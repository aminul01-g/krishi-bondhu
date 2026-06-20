from fastapi import FastAPI, File, UploadFile, Form, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, Response
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
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    media_url: str = None
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

        try:
            await ws_manager.broadcast({"type": "history_updated", "user_id": user_db_id})
        except Exception as broadcast_error:
            logger.warning("WebSocket broadcast failed", error=str(broadcast_error), user_id=user_db_id)

        return conv.id
    except Exception as e:
        logger.error("Failed to save conversation", error=str(e), user_id=user_db_id)
        return None

def _parse_allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost,http://localhost:3000,https://huggingface.co,https://krishibondhu.hf.space"
    )
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if "*" in origins:
        if os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true":
            logger.warning(
                "CORS_ALLOW_ORIGINS contains '*', but credentials are allowed. Removing wildcard for security."
            )
            origins = [origin for origin in origins if origin != "*"]
        else:
            return ["*"]
    if not origins:
        logger.warning(
            "No valid CORS origins configured; falling back to localhost defaults."
        )
        origins = ["http://localhost", "http://localhost:3000"]
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=True,
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

    try:
        async with engine.begin() as conn:
            if "postgresql" in DATABASE_URL.lower():
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("[INFO] PostGIS and pgvector extensions ensured.")

            await conn.run_sync(Base.metadata.create_all)
            print("[INFO] Database tables created or already exist.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

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

# --- APScheduler Setup ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def daily_notification_job():
    """
    Morning job to generate irrigation and pest alerts for all active users.
    """
    logger.info("Running daily irrigation and pest risk notification job...")
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch all users
            result = await db.execute(select(User))
            users = result.scalars().all()

            for user in users:
                # 2. Get last known location for the user from conversations
                conv_result = await db.execute(
                    select(Conversation)
                    .where(Conversation.user_id == user.id)
                    .order_by(desc(Conversation.created_at))
                    .limit(1)
                )
                last_conv = conv_result.scalars().first()

                gps = {"lat": 23.8103, "lon": 90.4125} # Default to Dhaka
                if last_conv and last_conv.meta_data and last_conv.meta_data.get("gps"):
                    gps = last_conv.meta_data.get("gps")

                # 3. We've moved to the Service Layer. We now use the AlertService here.
                from app.services.alert_service import AlertService
                alert_svc = AlertService()
                risk_data = await alert_svc.calculate_pest_risk(crop="rice", lat=gps["lat"], lon=gps["lon"])

                advice = f"Daily Pest Alert: {risk_data['risk_level']} risk. {risk_data['alerts'][0]}"

                new_log = IrrigationLog(
                    user_id=user.external_id,
                    soil_moisture_index=0.42,
                    advice=advice
                )
                db.add(new_log)

            await db.commit()
            logger.info(f"Successfully processed users: {len(users)}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

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
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

ws_manager = ConnectionManager()

@app.websocket("/api/ws/agent_status")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

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
            media_url=image_path
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
            media_url=image_path
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
            media_url=image_path
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

@app.get('/api/get_tts')
async def get_tts(path: str):
    from urllib.parse import unquote
    from app.api.utils import UPLOAD_DIR
    import re
    from fastapi import Response
    decoded_path = unquote(path)
    filename = os.path.basename(decoded_path)
    if os.path.exists(decoded_path):
        return FileResponse(decoded_path, media_type='audio/mpeg', filename=filename)
    upload_dir_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(upload_dir_path):
        return FileResponse(upload_dir_path, media_type='audio/mpeg', filename=filename)
    return Response(status_code=204)

@app.get("/{full_path:path}")
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
