"""IntelligenceOrchestrator — the brain of Phase 0.

Flow for every query:
  1. Assemble farmer context (profile + GPS + diary + memory + season).
  2. Retrieve relevant knowledge via RAG (cited as [n]).
  3. Classify intent -> call real domain-service *tools* for live evidence.
  4. Synthesize a grounded, cited answer with the LLM.
  5. Return a structured :class:`IntelligenceResult` (answer + sources +
     tool_traces + confidence + simulated-data flag).

This replaces the old "raw message -> single LLM call" path with one that is
context-aware, tool-augmented, and honest about data provenance.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.intelligence.farmer_context import FarmerContextAssembler
from app.intelligence.intent import classify_intent
from app.intelligence.retrieval import get_retrieval_layer
from app.intelligence.schemas import FarmerContext, IntelligenceResult, Source, ToolTrace
from app.intelligence.tools import run_tool

logger = logging.getLogger("IntelligenceOrchestrator")


class IntelligenceOrchestrator:
    def __init__(self):
        self.retrieval = get_retrieval_layer()

    async def respond(
        self,
        db,
        *,
        message: str,
        user_id_int: int,
        external_id: str,
        gps: Optional[Dict[str, float]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        language: str = "bn",
    ) -> IntelligenceResult:
        # 1. Context
        ctx: FarmerContext = await FarmerContextAssembler.assemble(
            db, user_id_int, external_id, gps
        )

        # 2. Retrieval (RAG)
        sources: List[Source] = self.retrieval.retrieve(message, k=4)

        # 3. Intent -> tools
        intent = classify_intent(message)
        tool_names = [t for t in intent["tools"] if t not in ("retrieval", "memory")]
        traces: List[ToolTrace] = []
        evidence: List[str] = []
        simulated = False
        for name in tool_names:
            trace = await run_tool(name, db, ctx, message, gps, external_id)
            traces.append(trace)
            if trace.provenance and trace.provenance.get("simulated"):
                simulated = True
            if trace.called and trace.result_summary:
                prov = ""
                if trace.provenance:
                    src = trace.provenance.get("source")
                    if src:
                        prov = f" [source: {src}]"
                evidence.append(f"- {name}: {trace.result_summary}{prov}")
            elif trace.error:
                evidence.append(f"- {name}: unavailable ({trace.error})")

        # 4. Synthesize
        prompt = self._build_prompt(message, ctx, sources, evidence, history, language)
        answer = self._synthesize(prompt, language)

        # 5. Confidence + provenance
        confidence = self._confidence(ctx, traces, simulated)
        result = IntelligenceResult(
            answer=answer,
            sources=sources,
            tool_traces=traces,
            context_used=ctx.to_dict(),
            confidence=round(confidence, 2),
            simulated_data_used=simulated,
            language=language,
        )
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(message, ctx, sources, evidence, history, language) -> str:
        lang_name = "Bengali (Bangla)" if language in ("bn", "bengali", "bn-BD") else "English"
        lines = [f"USER QUESTION: {message}", "", f"LANGUAGE TO REPLY IN: {lang_name}", ""]

        if ctx.formatted:
            lines += ["FARMER CONTEXT:", ctx.formatted, ""]

        if sources:
            lines.append("RETRIEVED KNOWLEDGE (cite with [n]):")
            for i, s in enumerate(sources, 1):
                lines.append(f"[{i}] {s.title}: {s.snippet}")
            lines.append("")

        if evidence:
            lines.append("LIVE DATA FROM FARM TOOLS:")
            lines.extend(evidence)
            lines.append("")

        if history:
            recent = history[-4:]
            lines.append("CONVERSATION HISTORY:")
            for m in recent:
                role = m.get("role", "user")
                lines.append(f"- {role}: {m.get('content', '')}")
            lines.append("")

        lines += [
            "INSTRUCTIONS:",
            "- Give a practical, localized answer grounded in the farmer context and data above.",
            "- Cite retrieved knowledge with [n] where you use it.",
            "- If live data is limited or simulated, state that briefly and advise verifying with the local DAE office.",
            "- Be concise, actionable, and friendly. Reply in the requested language.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _synthesize(prompt: str, language: str) -> str:
        try:
            from app.core.prompts import REASONING_CHAT_INSTRUCTION
            from app.services.llm import call_llm

            sys_inst = REASONING_CHAT_INSTRUCTION + (
                "\n\nRespond in Bengali (Bangla) unless the user writes in English."
                if language in ("bn", "bengali", "bn-BD")
                else "\n\nRespond in English."
            )
            return call_llm(prompt, sys_inst).strip()
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Synthesis LLM failed", error=str(e))
            return (
                "I'm operating in basic mode right now and couldn't generate a full answer. "
                "Please try again, or contact your local agricultural extension office (DAE)."
            )

    @staticmethod
    def _confidence(ctx, traces, simulated) -> float:
        score = 0.6
        if ctx.formatted:
            score += 0.1
        success = sum(1 for t in traces if t.called)
        score += min(0.15, 0.05 * success)
        if simulated:
            score = min(score, 0.7)
        return max(0.4, min(0.95, score))
