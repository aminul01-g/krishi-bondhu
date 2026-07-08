from fastapi import FastAPI, File, UploadFile, Form, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
import asyncio
import traceback
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Load environment variables before importing LLM/agent modules.
load_dotenv()

from app.api.utils import save_audio_local, save_image_local
from app.services.audio import stt_node
from app.api import routes as api_routes
from app.api.endpoints import auth as auth_routes
from app.api.endpoints import market as market_routes
from app.api.endpoints import diary as diary_routes
from app.api.endpoints import alerts as alerts_routes
from app.api.endpoints import soil as soil_routes
from app.api.endpoints import water as water_routes
from app.api.endpoints import finance as finance_routes
from app.api.endpoints import community as community_routes
from app.api.endpoints import marketplace as marketplace_routes
from app.api.endpoints import emergency as emergency_routes
from app.api.endpoints import recommendations as recommendations_routes
from app.api.endpoints import tasks as tasks_routes
from app.api.endpoints import planner as planner_routes
from app.api.endpoints import traceability as traceability_routes
from app.api.endpoints import sustainability as sustainability_routes
from app.api.endpoints import farmer_profile as farmer_profile_routes
from app.api.endpoints import dashboard as dashboard_routes
from app.services.task_worker import task_worker_loop
from app.services.memory import MemoryService
from app.api.endpoints import memory as memory_routes
from app.db import get_db, engine, DATABASE_URL, AsyncSessionLocal
from app.models.db_models import Base, User, Conversation, IrrigationLog
from app.core.dependencies import get_current_user
import app.models  # Register all ORM models before startup actions

from app.core.logging import get_logger
from app.core.exceptions import KrishiBondhuException, KrishiBondhuClientException, KrishiBondhuServerException
import structlog

logger = get_logger("main")

app = FastAPI(title="KrishiBondhu API")

# --- Rate Limiting ---
# The shared limiter (app.core.rate_limit) is imported so routers can attach
# stricter per-route limits using the same instance. A generous global default
# catches abusive bursts (credential brute-force, unmetered LLM/DB hammering) on
# EVERY route; hot/sensitive endpoints keep stricter @limiter.limit overrides.
from app.core.rate_limit import limiter, DEFAULT_LIMITS
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# SlowAPIMiddleware is what actually enforces the global default_limits across
# all routes (per-route decorators work without it, but defaults do not).
if DEFAULT_LIMITS:
    app.add_middleware(SlowAPIMiddleware)

# --- Global Error Handling ---

@app.exception_handler(KrishiBondhuException)
async def krishi_bondhu_exception_handler(request: Request, exc: KrishiBondhuException):
    status_code = 400 if isinstance(exc, KrishiBondhuClientException) else 500
    if isinstance(exc, KrishiBondhuServerException):
        logger.exception("Server error occurred", code=exc.code, detail=exc.detail)
    else:
        logger.info("Client error occurred", code=exc.code, detail=exc.detail)

    return JSONResponse(
        status_code=status_code,
        content={"error": exc.message, "detail": exc.detail, "code": exc.code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception caught by global handler", exc=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later.", "code": "INTERNAL_SERVER_ERROR"}
    )

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("Validation error occurred", detail=exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors(), "code": "VALIDATION_ERROR"}
    )

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
        return response
    finally:
        structlog.contextvars.clear_contextvars()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        csp = (
            "default-src 'self' https://huggingface.co;"
            "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://huggingface.co https://js.stripe.com https://m.stripe.network;"
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
            "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com;"
            "font-src 'self' https://fonts.gstatic.com data:;"
            "connect-src 'self' https://huggingface.co wss://huggingface.co https://*.hf.space wss://*.hf.space https://api.stripe.com https://m.stripe.network;"
            "img-src 'self' data: blob: https://huggingface.co https://*.stripe.com;"
            "media-src 'self' data: blob: https://huggingface.co;"
            "frame-src 'self' https://js.stripe.com https://hooks.stripe.com https://m.stripe.network;"
            "frame-ancestors 'self' https://huggingface.co;"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Modern Permissions-Policy
        response.headers["Permissions-Policy"] = "camera=*, microphone=*, geolocation=*, payment=*, usb=(), accelerometer=*, gyroscope=*"
        
        # Ensure session cookies within iframe are partitioned properly
        # This resolves the Hugging Face Storage Partitioning warning.
        if "set-cookie" in response.headers:
            cookies = response.headers.get_all("set-cookie")
            response.headers.raw.pop(b"set-cookie")
            for cookie in cookies:
                if "SameSite=None" not in cookie:
                    cookie += "; SameSite=None; Secure"
                if "Partitioned" not in cookie:
                    cookie += "; Partitioned"
                response.headers.append("set-cookie", cookie)

        return response

app.add_middleware(SecurityHeadersMiddleware)

# Helper to get/create user
from sqlalchemy import select, desc

async def get_current_user_db_id(external_id: str, db: AsyncSession) -> int:
    try:
        result = await db.execute(select(User).where(User.external_id == external_id))
        user = result.scalars().first()
        if not user:
            user = User(external_id=external_id)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user.id
    except Exception as e:
         logger.error("Could not get/create user", error=str(e), external_id=external_id)
         return None

async def save_conversation_to_db(
    db: AsyncSession,
    user_db_id: int,
    transcript: str,
    reply_text: str,
    metadata: dict = None,
    tts_path: str = None,
    media_url: str = None,
    external_id: str = None,
):
    try:
        if not user_db_id:
            return None

        conv = Conversation(
            user_id=user_db_id,
            transcript=transcript,
            meta_data={"reply_text": reply_text, **(metadata or {})},
            tts_path=tts_path,
            media_url=media_url
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        logger.debug(f"Saved conversation id={conv.id} for user_id={user_db_id}")

        # Notify ONLY the owning user's sockets. Previously this fanned out to
        # every connected client (an activity/user-id side-channel leak).
        if external_id:
            try:
                await ws_manager.send_to_user(
                    external_id, {"type": "history_updated"}
                )
            except Exception as broadcast_error:
                logger.warning("WebSocket notify failed", error=str(broadcast_error), user_id=user_db_id)

        return conv.id
    except Exception as e:
        logger.error("Failed to save conversation", error=str(e), user_id=user_db_id)
        return None

from app.core.config import settings

def _parse_allowed_origins() -> list[str]:
    """Resolve CORS origins from the central settings object.

    The wildcard-vs-credentials safety handling now lives in
    ``settings.cors_origins_list``; we keep this thin wrapper so the log
    warnings (useful in prod misconfig) stay at the composition root.
    """
    raw_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    if "*" in raw_origins and settings.cors_allow_credentials:
        logger.warning(
            "CORS_ALLOW_ORIGINS contains '*', but credentials are allowed. Removing wildcard for security."
        )
    origins = settings.cors_origins_list
    if not raw_origins:
        logger.warning(
            "No valid CORS origins configured; falling back to localhost defaults."
        )
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def create_database_tables():
    from sqlalchemy import text

    # --- One-time HuggingFace Hub login ---
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if hf_token:
        try:
            from huggingface_hub import login
            login(token=hf_token, add_to_git_credential=False)
            logger.info("HuggingFace Hub login completed (one-time).")
        except Exception as e:
            logger.warning(f"HuggingFace Hub login failed: {e}")

    # Schema ownership (M6):
    #   * PostgreSQL (production): Alembic is the single source of truth. Migrations
    #     run via `alembic upgrade head` (Docker CMD). We do NOT run create_all,
    #     which would create untracked tables and mask pending migrations / schema
    #     drift. Set AUTO_CREATE_TABLES=true to force the old behavior if needed.
    #   * SQLite (local dev / HF Space fallback): create_all bootstraps the full
    #     model schema so a fresh checkout runs without a migration step (the
    #     Postgres migrations can't fully replay on SQLite due to PostGIS/pgvector
    #     column types).
    is_postgres = "postgresql" in DATABASE_URL.lower()
    _auto = os.getenv("AUTO_CREATE_TABLES", "auto").strip().lower()
    should_create_all = _auto in ("1", "true", "yes") or (_auto == "auto" and not is_postgres)

    try:
        async with engine.begin() as conn:
            if is_postgres:
                # Idempotent; also ensured by migration 0007, but created here as a
                # safety net for migrations that assume the extensions exist.
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                logger.info("PostGIS and pgvector extensions ensured.")

            if should_create_all:
                await conn.run_sync(Base.metadata.create_all)
                logger.info(
                    "Database schema ensured via create_all (non-Alembic path).",
                    dialect="sqlite" if not is_postgres else "postgresql",
                )
            else:
                logger.info(
                    "Skipping create_all; Alembic owns the schema. "
                    "Run `alembic upgrade head` to apply migrations.",
                )
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))

app.include_router(api_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(market_routes.router, prefix="/api/market", tags=["market"])
app.include_router(diary_routes.router, prefix="/api/diary", tags=["diary"])
app.include_router(alerts_routes.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(soil_routes.router, prefix="/api/soil", tags=["soil"])
app.include_router(water_routes.router, prefix="/api/water", tags=["water"])
app.include_router(finance_routes.router, prefix="/api/finance", tags=["finance"])
app.include_router(memory_routes.router, prefix="/api/memory", tags=["memory"])
app.include_router(community_routes.router, prefix="/api/community", tags=["community"])
app.include_router(marketplace_routes.router, prefix="/api/marketplace", tags=["marketplace"])
app.include_router(emergency_routes.router, prefix="/api/emergency", tags=["emergency"])
app.include_router(recommendations_routes.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(tasks_routes.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(planner_routes.router, prefix="/api/planner", tags=["planner"])
app.include_router(traceability_routes.router, prefix="/api/traceability", tags=["traceability"])
app.include_router(sustainability_routes.router, prefix="/api/sustainability", tags=["sustainability"])
app.include_router(farmer_profile_routes.router, prefix="/api/profile", tags=["profile"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["dashboard"])

# --- APScheduler Setup ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

_DEFAULT_GPS = {"lat": 23.8103, "lon": 90.4125}  # Dhaka
_ALERT_JOB_CONCURRENCY = int(os.getenv("ALERT_JOB_CONCURRENCY", "8"))


async def daily_notification_job():
    """
    Morning job to generate irrigation and pest alerts for all active users.

    Performance & reliability (M5):
    - One query resolves each user's last known GPS instead of a per-user
      Conversation lookup (was N+1).
    - Pest-risk calls (network I/O to the weather service) run with bounded
      concurrency rather than serially.
    - A failure for one user is logged and skipped; it no longer aborts the
      whole batch.
    """
    from app.services.alert_service import AlertService

    logger.info("Running daily irrigation and pest risk notification job...")
    async with AsyncSessionLocal() as db:
        try:
            users = (await db.execute(select(User))).scalars().all()
            if not users:
                logger.info("Daily alert job: no users to process.")
                return

            # --- Resolve latest GPS per user in a single pass (no N+1) --------
            # Pull the most-recent conversation row per user via a window
            # function, portable across PostgreSQL and SQLite (both support it).
            from sqlalchemy import func as sa_func

            rn = (
                sa_func.row_number()
                .over(
                    partition_by=Conversation.user_id,
                    order_by=desc(Conversation.created_at),
                )
                .label("rn")
            )
            subq = select(Conversation.user_id, Conversation.meta_data, rn).subquery()
            latest_rows = (
                await db.execute(select(subq).where(subq.c.rn == 1))
            ).all()

            gps_by_user_id: dict = {}
            for row in latest_rows:
                meta = row.meta_data or {}
                if isinstance(meta, dict) and meta.get("gps"):
                    gps_by_user_id[row.user_id] = meta["gps"]

            # --- Compute pest risk with bounded concurrency -------------------
            alert_svc = AlertService()
            semaphore = asyncio.Semaphore(max(1, _ALERT_JOB_CONCURRENCY))

            async def _risk_for(user) -> "tuple | None":
                gps = gps_by_user_id.get(user.id, _DEFAULT_GPS)
                async with semaphore:
                    try:
                        risk = await alert_svc.calculate_pest_risk(
                            crop="rice", lat=gps["lat"], lon=gps["lon"]
                        )
                        advice = f"Daily Pest Alert: {risk['risk_level']} risk. {risk['alerts'][0]}"
                        return (user.external_id, advice)
                    except Exception as user_err:
                        # Per-user isolation: one failure must not sink the batch.
                        logger.warning(
                            "Daily alert failed for user; skipping",
                            user_id=user.external_id,
                            error=str(user_err),
                        )
                        return None

            results = await asyncio.gather(*[_risk_for(u) for u in users])

            processed = 0
            for item in results:
                if item is None:
                    continue
                external_id, advice = item
                db.add(
                    IrrigationLog(
                        user_id=external_id,
                        soil_moisture_index=0.42,
                        advice=advice,
                    )
                )
                processed += 1

            await db.commit()
            logger.info(
                "Daily alert job complete",
                users_total=len(users),
                logs_written=processed,
            )
        except Exception as e:
            await db.rollback()
            logger.exception("Scheduler error in daily_notification_job", error=str(e))

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(daily_notification_job, 'cron', hour=6, minute=0)
    scheduler.start()
    logger.info("Scheduler started")

    import asyncio
    asyncio.create_task(task_worker_loop())
    logger.info("Async task worker started")

@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")

# --- WebSocket Setup for Agent Status ---
from typing import List, Dict

# Cap total concurrent sockets to bound resource use from anonymous/abusive clients.
_WS_MAX_CONNECTIONS = int(os.getenv("WS_MAX_CONNECTIONS", "500"))


class ConnectionManager:
    """Tracks live sockets keyed by the authenticated user's external_id so that
    broadcasts can be scoped to their owner instead of fanned out to everyone.
    """

    def __init__(self):
        # external_id -> list of that user's sockets (multi-device/tab support)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    @property
    def total(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        conns = self.active_connections.get(user_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        """Deliver a message only to the sockets owned by ``user_id``."""
        conns = list(self.active_connections.get(user_id, []))
        for connection in conns:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("WebSocket send failed; dropping connection", error=str(exc))
                self.disconnect(connection, user_id)


ws_manager = ConnectionManager()


async def _authenticate_websocket(websocket: WebSocket) -> "User | None":
    """Validate the JWT supplied on the WS handshake.

    The token may arrive either as a ``?token=`` query parameter or via the
    ``Authorization: Bearer <token>`` header. Returns the matching User, or
    None if authentication fails (caller closes the socket).
    """
    from app.core.security import decode_access_token

    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalars().first()


@app.websocket("/api/ws/agent_status")
async def websocket_endpoint(websocket: WebSocket):
    # Enforce a global connection cap before doing any auth work.
    if ws_manager.total >= _WS_MAX_CONNECTIONS:
        await websocket.close(code=1013)  # 1013 = Try Again Later
        return

    user = await _authenticate_websocket(websocket)
    if user is None:
        # 1008 = Policy Violation (auth failure). Reject before accepting frames.
        await websocket.close(code=1008)
        return

    user_id = user.external_id
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)

@app.post('/api/upload_audio')
@limiter.limit("10/minute")
async def upload_audio(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    lat: float = Form(None),
    lon: float = Form(None),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    audio_path = await save_audio_local(file)
    image_path = None
    if image:
        image_path = await save_image_local(image)

    initial_state = {
        "audio_path": audio_path,
        "user_id": current_user.external_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "messages": []
    }

    stt_result = stt_node(initial_state)
    transcript = stt_result.get("transcript", "").strip()
    language = stt_result.get("language", "en")
    stt_source = stt_result.get("stt_source")

    if stt_result.get("unclear"):
        return JSONResponse({
            "error": "Unable to understand voice clearly",
            "reply_text": "I did not understand your voice clearly. Please speak more clearly or repeat your question.",
            "transcript": transcript,
            "language": language,
            "stt_source": stt_source,
            "stt_source_reason": stt_result.get("stt_source_reason"),
            "unclear_audio": True
        }, status_code=200)

    # Allow frontend to override detected language via header
    header_lang = request.headers.get('x-kb-lang')
    initial_state["transcript"] = transcript
    initial_state["language"] = header_lang or language

    try:
        # Use the new Crew-based logic
        from app.crews.krishi_crew import KrishiCrew
        from crewai import Task
        from app.agents.bengali_interpreter import bengali_interpreter

        clean_msg = transcript.lower().strip()
        greetings = ["hello", "hi", "hey", "হ্যালো", "সালাম", "আসসালামু আলাইকুম", "hi there", "good morning"]
        
        if clean_msg in greetings:
            reply_text = "হ্যালো! আমি আপনার কৃষিবন্ধু। আমি কীভাবে সাহায্য করতে পারি? (Hello! I'm your KrishiBondhu. How can I help you today?)"
        else:
            route_task = Task(
                description=(
                    f"Process the user's message: {transcript}. "
                    "Interpret the intent and delegate to the appropriate expert agent to get the answer. "
                    "You must provide the final expert advice directly to the user."
                ),
                expected_output="A detailed, helpful answer in plain Bengali/English text. DO NOT output JSON.",
                agent=bengali_interpreter
            )

            crew_obj = KrishiCrew()
            crew = crew_obj.create_crew(tasks=[route_task])

            result = await asyncio.to_thread(crew.kickoff, inputs=initial_state)
            raw_reply = str(result)
            
            import json
            try:
                data = json.loads(raw_reply)
                if isinstance(data, dict):
                    parts = []
                    for k, v in data.items():
                        parts.append(f"{str(k).replace('_', ' ').title()}: {v}")
                    reply_text = "\n".join(parts)
                else:
                    reply_text = raw_reply
            except Exception:
                reply_text = raw_reply

        user_db_id = current_user.id
        saved_conv_id = await save_conversation_to_db(
            db,
            user_db_id,
            transcript,
            reply_text,
            metadata={"gps": initial_state["gps"]},
            tts_path=None,
            media_url=image_path,
            external_id=current_user.external_id,
        )

        await MemoryService.extract_and_save_facts(
            db,
            current_user.external_id,
            transcript,
            conv_id=saved_conv_id
        )

        # --- TTS: generate audio for Bengali replies ---
        from app.services.tts import generate_tts
        tts_path = None
        try:
            lang = initial_state.get("language", "bn")
            if lang in ("bn", "bengali", "bn-BD"):
                tts_path = await asyncio.to_thread(generate_tts, reply_text[:600], language="bn-BD")
        except Exception as tts_err:
            logger.warning("TTS generation failed", error=str(tts_err))

        return JSONResponse({
            "transcript": transcript,
            "reply_text": reply_text,
            "tts_path": tts_path,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        logger.error("Endpoint failed", error=str(e), traceback=traceback.format_exc())
        return JSONResponse({"error": "Something went wrong. Please try again.", "code": "AGENT_ERROR"}, status_code=500)

@app.post('/api/upload_image')
@limiter.limit("10/minute")
async def upload_image(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    lat: float = Form(None),
    lon: float = Form(None),
    question: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    from app.services.audio import detect_language_from_text
    image_path = await save_image_local(image)
    detected_language = detect_language_from_text(question) if question else "en"

    header_lang = request.headers.get('x-kb-lang')

    initial_state = {
        "user_id": current_user.external_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "transcript": question,
        "language": header_lang or detected_language,
    }
    try:
        from app.crews.krishi_crew import KrishiCrew
        from crewai import Task
        from app.agents.disease_analyst import disease_analyst

        vision_task = Task(
            description=f"Analyze the soil/crop image at {image_path} and answer: {question}",
            expected_output="A technical diagnostic report with treatment recommendations.",
            agent=disease_analyst
        )

        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew(tasks=[vision_task])

        result = await asyncio.to_thread(crew.kickoff, inputs=initial_state)
        reply_text = str(result)

        user_db_id = current_user.id
        saved_conv_id = await save_conversation_to_db(
            db,
            user_db_id,
            question,
            reply_text,
            metadata={"gps": initial_state["gps"]},
            media_url=image_path,
            external_id=current_user.external_id,
        )

        await MemoryService.extract_and_save_facts(
            db,
            current_user.external_id,
            question,
            conv_id=saved_conv_id
        )

        # --- TTS: generate audio for Bengali replies ---
        from app.services.tts import generate_tts
        tts_path = None
        try:
            lang = initial_state.get("language", "bn")
            if lang in ("bn", "bengali", "bn-BD"):
                tts_path = await asyncio.to_thread(generate_tts, reply_text[:600], language="bn-BD")
        except Exception as tts_err:
            logger.warning("TTS generation failed", error=str(tts_err))

        return JSONResponse({
            "transcript": question,
            "reply_text": reply_text,
            "tts_path": tts_path,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        logger.error("Endpoint failed", error=str(e), traceback=traceback.format_exc())
        return JSONResponse({"error": "Something went wrong. Please try again.", "code": "AGENT_ERROR"}, status_code=500)

@app.post('/api/chat')
@limiter.limit("20/minute")
async def chat(
    request: Request,
    message: str = Form(...),
    current_user: User = Depends(get_current_user),
    lat: float = Form(None),
    lon: float = Form(None),
    image: UploadFile = File(None),
    include_history: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    from app.services.audio import detect_language_from_text
    from sqlalchemy import select, desc
    from app.models.db_models import Conversation

    image_path = None
    if image:
        image_path = await save_image_local(image)

    # Prefer language set by frontend (UI toggle), fall back to auto-detection
    header_lang = request.headers.get('x-kb-lang')
    detected_language = header_lang or detect_language_from_text(message)

    messages = [{"role": "user", "content": message}]
    if include_history and db:
        user_db_id = current_user.id
        if user_db_id:
            result = await db.execute(
                select(Conversation)
                .where(Conversation.user_id == user_db_id)
                .order_by(desc(Conversation.created_at))
                .limit(5)
            )
            previous_convs = list(reversed(result.scalars().all()))
            for conv in previous_convs:
                if conv.transcript: messages.insert(0, {"role": "user", "content": conv.transcript})
                if conv.meta_data and conv.meta_data.get("reply_text"):
                    messages.insert(1, {"role": "assistant", "content": conv.meta_data.get("reply_text", "")})

    initial_state = {
        "user_id": current_user.external_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "transcript": message,
        "language": detected_language,
        "messages": messages
    }
    try:
        from app.crews.krishi_crew import KrishiCrew
        from crewai import Task
        from app.agents.bengali_interpreter import bengali_interpreter

        clean_msg = message.lower().strip()
        greetings = ["hello", "hi", "hey", "হ্যালো", "সালাম", "আসসালামু আলাইকুম", "hi there", "good morning"]
        
        if clean_msg in greetings:
            reply_text = "হ্যালো! আমি আপনার কৃষিবন্ধু। আমি কীভাবে সাহায্য করতে পারি? (Hello! I'm your KrishiBondhu. How can I help you today?)"
        else:
            route_task = Task(
                description=(
                    f"Process the user's message: {message}. "
                    "Interpret the intent and delegate to the appropriate expert agent to get the answer. "
                    "You must provide the final expert advice directly to the user."
                ),
                expected_output="A detailed, helpful answer in plain Bengali/English text. DO NOT output JSON.",
                agent=bengali_interpreter
            )

            crew_obj = KrishiCrew()
            crew = crew_obj.create_crew(tasks=[route_task])

            result = await asyncio.to_thread(crew.kickoff, inputs=initial_state)
            reply_text = str(result)

        user_db_id = current_user.id
        saved_conv_id = await save_conversation_to_db(
            db,
            user_db_id,
            message,
            reply_text,
            metadata={"gps": initial_state["gps"]},
            media_url=image_path,
            external_id=current_user.external_id,
        )

        await MemoryService.extract_and_save_facts(
            db,
            current_user.external_id,
            message,
            conv_id=saved_conv_id
        )

        # --- TTS: generate audio for Bengali replies ---
        from app.services.tts import generate_tts
        tts_path = None
        try:
            lang = initial_state.get("language", "bn")
            if lang in ("bn", "bengali", "bn-BD"):
                tts_path = await asyncio.to_thread(generate_tts, reply_text[:600], language="bn-BD")
        except Exception as tts_err:
            logger.warning("TTS generation failed", error=str(tts_err))

        return JSONResponse({
            "transcript": message,
            "reply_text": reply_text,
            "tts_path": tts_path,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        logger.error("Endpoint failed", error=str(e), traceback=traceback.format_exc())
        return JSONResponse({"error": "Something went wrong. Please try again.", "code": "AGENT_ERROR"}, status_code=500)

@app.post('/api/chat/stream')
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    message: str = Form(...),
    current_user: User = Depends(get_current_user),
    lat: float = Form(None),
    lon: float = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """SSE streaming endpoint — yields word-by-word chunks as text/event-stream."""
    import json as _json
    from app.services.audio import detect_language_from_text
    from sqlalchemy import select, desc
    from app.models.db_models import Conversation as _Conversation

    header_lang = request.headers.get('x-kb-lang')
    detected_language = header_lang or detect_language_from_text(message)

    # Build conversation history for context
    messages_ctx = [{"role": "user", "content": message}]
    user_db_id = current_user.id
    if user_db_id:
        try:
            hist = await db.execute(
                select(_Conversation)
                .where(_Conversation.user_id == user_db_id)
                .order_by(desc(_Conversation.created_at))
                .limit(5)
            )
            previous_convs = list(reversed(hist.scalars().all()))
            for conv in previous_convs:
                if conv.transcript:
                    messages_ctx.insert(0, {"role": "user", "content": conv.transcript})
                if conv.meta_data and conv.meta_data.get("reply_text"):
                    messages_ctx.insert(1, {"role": "assistant", "content": conv.meta_data.get("reply_text", "")})
        except Exception as hist_err:
            logger.warning("Failed to load history for SSE chat", error=str(hist_err))

    initial_state = {
        "user_id": current_user.external_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": None,
        "transcript": message,
        "language": detected_language,
        "messages": messages_ctx
    }

    async def generate():
        try:
            # Signal to the client that we are thinking
            yield f"data: {_json.dumps({'type': 'thinking'})}\n\n"

            from app.crews.krishi_crew import KrishiCrew
            from crewai import Task
            from app.agents.bengali_interpreter import bengali_interpreter

            clean_msg = message.lower().strip()
            greetings = ["hello", "hi", "hey", "হ্যালো", "সালাম", "আসসালামু আলাইকুম", "hi there", "good morning"]

            if clean_msg in greetings:
                reply_text = "হ্যালো! আমি আপনার কৃষিবন্ধু। আমি কীভাবে সাহায্য করতে পারি? (Hello! I'm your KrishiBondhu. How can I help you today?)"
            else:
                route_task = Task(
                    description=(
                        f"Process the user's message: {message}. "
                        "Interpret the intent and delegate to the appropriate expert agent to get the answer. "
                        "You must provide the final expert advice directly to the user."
                    ),
                    expected_output="A detailed, helpful answer in plain Bengali/English text. DO NOT output JSON.",
                    agent=bengali_interpreter
                )
                crew_obj = KrishiCrew()
                crew = crew_obj.create_crew(tasks=[route_task])
                result = await asyncio.to_thread(crew.kickoff, inputs=initial_state)
                reply_text = str(result)

            # Stream reply word-by-word (3 words per chunk)
            words = reply_text.split(' ')
            chunk = ''
            for i, word in enumerate(words):
                chunk += word + ' '
                if i % 3 == 0:
                    yield f"data: {_json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                    chunk = ''
                    await asyncio.sleep(0.05)
            if chunk:
                yield f"data: {_json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

            # Persist to DB after full response
            saved_conv_id = await save_conversation_to_db(
                db,
                user_db_id,
                message,
                reply_text,
                metadata={"gps": initial_state["gps"]},
                external_id=current_user.external_id,
            )

            try:
                await MemoryService.extract_and_save_facts(
                    db,
                    current_user.external_id,
                    message,
                    conv_id=saved_conv_id
                )
            except Exception as mem_err:
                logger.warning("Memory extraction failed in SSE stream", error=str(mem_err))

            yield f"data: {_json.dumps({'type': 'done', 'full_text': reply_text})}\n\n"

        except Exception as e:
            logger.error("SSE stream error", error=str(e), traceback=traceback.format_exc())
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@app.get('/api/get_tts')
async def get_tts(path: str):
    from urllib.parse import unquote
    from app.api.utils import UPLOAD_DIR
    from fastapi import Response

    # SECURITY: never trust the caller-supplied directory component. A previous
    # implementation returned any absolute path that existed on disk, which was
    # an arbitrary-file-read vulnerability (e.g. ?path=/etc/passwd). We now use
    # only the basename and serve strictly from within UPLOAD_DIR, verifying the
    # resolved real path stays inside the allowed directory (defends against
    # symlink / ".." tricks in the filename itself).
    filename = os.path.basename(unquote(path))
    if not filename:
        return Response(status_code=204)

    upload_root = os.path.realpath(UPLOAD_DIR)
    candidate = os.path.realpath(os.path.join(upload_root, filename))

    # Containment check: candidate must live under upload_root.
    if os.path.commonpath([upload_root, candidate]) != upload_root:
        logger.warning("Rejected out-of-bounds TTS path request", requested=path)
        return Response(status_code=204)

    if os.path.isfile(candidate):
        return FileResponse(candidate, media_type='audio/mpeg', filename=filename)
    return Response(status_code=204)

@app.get("/{full_path:path}")
@limiter.exempt  # Static/SPA asset serving: one page load fetches many chunks;
                 # the per-IP default limit would break loads behind shared NAT.
async def serve_spa(full_path: str):
    if full_path.startswith("api"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    
    # Serve static assets if they exist (CSS, JS, manifest, SW, etc.)
    file_path = os.path.join("static", full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
        
    # Fallback to index.html for React Router
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
