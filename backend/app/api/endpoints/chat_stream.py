"""Streaming chat endpoint powered by the Phase 0 IntelligenceOrchestrator.

This router replaces the legacy inline ``/api/chat/stream`` (which used the
``KrishiCrew`` and emitted only ``thinking`` / ``chunk`` / ``done`` / ``error``)
with one that runs the tool-augmented :class:`IntelligenceOrchestrator` and
emits rich, honest Server-Sent Events:

SSE EVENT SCHEMA (one JSON object per ``data:`` line, ``\\n\\n``-delimited)
-------------------------------------------------------------------------
  thinking   { "type": "thinking" }
      Emitted once when the stream opens, before any work is done.

  tool       { "type": "tool",
               "name":        str,            # e.g. "weather", "market"
               "called":      bool,           # did the tool actually run
               "summary":     str | null,     # short result summary
               "query":       str | null,     # the query/args passed
               "provenance":  dict | null,    # {source, simulated, ...}
               "error":       str | null }    # error reason if not called
      One per tool trace returned by the orchestrator. Lets the UI show
      exactly which live farm tools were used and whether the data was
      simulated.

  citation   { "type": "citation",
               "id":     str,                # source id
               "title":  str,                # document title
               "url":    str | null,         # source url
               "snippet": str,               # retrieved excerpt
               "score":  float }             # retrieval score
      One per retrieved knowledge source cited by the orchestrator.

  chunk      { "type": "chunk",
               "text":  str }                # INCREMENTAL delta only
      Small incremental text deltas. The client APPENDS these (never
      cumulative) to grow the reply.

  done       { "type": "done",
               "full_text":            str,
               "confidence":           float,
               "simulated_data_used":  bool }
      Emitted once at the end with the complete answer and provenance meta.

  error      { "type": "error",
               "message": str }
      Emitted once on any failure; the stream then closes cleanly.

All events are sent as ``data: {json}\\n\\n`` lines via a ``StreamingResponse``
with ``media_type="text/event-stream"`` (no extra dependency required).
"""
from __future__ import annotations

import asyncio
import json
import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, Form, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.db import get_db
from app.models.db_models import Conversation, User
from app.intelligence import IntelligenceOrchestrator

logger = logging.getLogger("chat_stream")

router = APIRouter()

_GREETINGS = [
    "hello", "hi", "hey", "হ্যালো", "সালাম", "আসসালামু আলাইকুম",
    "hi there", "good morning",
]

_GREETING_REPLY = (
    "হ্যালো! আমি আপনার কৃষিবন্ধু। আমি কীভাবে সাহায্য করতে পারি? "
    "(Hello! I'm your KrishiBondhu. How can I help you today?)"
)


def _sse(payload: dict) -> str:
    """Serialize one event as an SSE ``data:`` line."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _split_into_chunks(text: str, size: int = 3):
    """Split text into small incremental word-group deltas."""
    words = text.split(" ")
    chunks = []
    for i in range(0, len(words), size):
        group = words[i : i + size]
        delta = " ".join(group)
        if i + size < len(words):
            delta += " "
        chunks.append(delta)
    if not chunks:
        chunks = [text]
    return chunks


async def _save_conversation(db, user_db_id, transcript, reply_text, metadata, external_id):
    """Local mirror of main.save_conversation_to_db (no ws notify)."""
    try:
        if not user_db_id:
            return None
        conv = Conversation(
            user_id=user_db_id,
            transcript=transcript,
            meta_data={"reply_text": reply_text, **(metadata or {})},
            media_url=None,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv.id
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Failed to save conversation", error=str(e))
        return None


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    message: str = Form(...),
    current_user: User = Depends(get_current_user),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db=Depends(get_db),
):
    """SSE streaming chat — tool-augmented, emits citation + tool events."""
    from app.services.audio import detect_language_from_text
    from app.services.memory import MemoryService

    gps = {"lat": lat, "lon": lon} if lat is not None else None

    # Prefer language set by frontend (UI toggle), fall back to auto-detection.
    header_lang = request.headers.get("x-kb-lang")
    detected_language = header_lang or detect_language_from_text(message)

    # Build conversation history for context (mirrors main.py /api/chat).
    messages_ctx = [{"role": "user", "content": message}]
    user_db_id = current_user.id
    if user_db_id:
        try:
            hist = await db.execute(
                select(Conversation)
                .where(Conversation.user_id == user_db_id)
                .order_by(desc(Conversation.created_at))
                .limit(5)
            )
            previous_convs = list(reversed(hist.scalars().all()))
            for conv in previous_convs:
                if conv.transcript:
                    messages_ctx.insert(0, {"role": "user", "content": conv.transcript})
                if conv.meta_data and conv.meta_data.get("reply_text"):
                    messages_ctx.insert(
                        1,
                        {"role": "assistant", "content": conv.meta_data.get("reply_text", "")},
                    )
        except Exception as hist_err:
            logger.warning("Failed to load history for SSE chat", error=str(hist_err))

    image_path = None
    if image:
        try:
            from app.api.utils import save_image_local

            image_path = await save_image_local(image)
        except Exception as img_err:
            logger.warning("Image save failed in SSE chat", error=str(img_err))

    async def event_generator():
        result = None
        reply_text = ""
        try:
            # Signal to the client that we are thinking.
            yield _sse({"type": "thinking"})

            clean_msg = (message or "").lower().strip()
            if clean_msg in _GREETINGS:
                reply_text = _GREETING_REPLY
                confidence = 1.0
                simulated_data_used = False
            else:
                # Phase 0 intelligence layer: context-aware, tool-augmented, cited.
                orch = IntelligenceOrchestrator()
                result = await orch.respond(
                    db,
                    message=message,
                    user_id_int=current_user.id,
                    external_id=current_user.external_id,
                    gps=gps,
                    history=messages_ctx,
                    language=detected_language,
                )
                reply_text = result.answer
                confidence = result.confidence
                simulated_data_used = result.simulated_data_used

            # Emit one `tool` event per tool trace (in execution order).
            if result:
                for trace in result.tool_traces:
                    yield _sse(
                        {
                            "type": "tool",
                            "name": trace.tool,
                            "called": trace.called,
                            "summary": trace.result_summary,
                            "query": trace.query,
                            "provenance": trace.provenance,
                            "error": trace.error,
                        }
                    )

                # Emit one `citation` event per retrieved source.
                for src in result.sources:
                    yield _sse(
                        {
                            "type": "citation",
                            "id": src.id,
                            "title": src.title,
                            "url": src.url,
                            "snippet": src.snippet,
                            "score": src.score,
                        }
                    )

            # Stream the reply as small incremental deltas (append on client).
            for delta in _split_into_chunks(reply_text or ""):
                yield _sse({"type": "chunk", "text": delta})
                await asyncio.sleep(0.03)

            # Signal completion with the full text + provenance meta.
            yield _sse(
                {
                    "type": "done",
                    "full_text": reply_text,
                    "confidence": round(confidence, 2) if result else 1.0,
                    "simulated_data_used": simulated_data_used,
                }
            )

            # Persist to DB after the full response (mirrors main.py /api/chat).
            try:
                conv_metadata = {"gps": gps}
                if result:
                    conv_metadata.update(
                        {
                            "sources": [
                                {
                                    "id": s.id,
                                    "title": s.title,
                                    "url": s.url,
                                    "snippet": s.snippet,
                                    "score": s.score,
                                }
                                for s in result.sources
                            ],
                            "tool_traces": [
                                {
                                    "tool": t.tool,
                                    "called": t.called,
                                    "summary": t.result_summary,
                                    "provenance": t.provenance,
                                    "error": t.error,
                                }
                                for t in result.tool_traces
                            ],
                            "confidence": result.confidence,
                            "simulated_data_used": result.simulated_data_used,
                        }
                    )
                saved_conv_id = await _save_conversation(
                    db,
                    user_db_id,
                    message,
                    reply_text,
                    metadata=conv_metadata,
                    external_id=current_user.external_id,
                )
                if saved_conv_id is not None:
                    await MemoryService.extract_and_save_facts(
                        db,
                        current_user.external_id,
                        message,
                        conv_id=saved_conv_id,
                    )
            except Exception as persist_err:
                logger.warning(
                    "Persistence failed in SSE stream", error=str(persist_err)
                )

        except Exception as e:
            logger.error(
                "SSE stream error", error=str(e), traceback=traceback.format_exc()
            )
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
