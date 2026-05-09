from fastapi import FastAPI, File, UploadFile, Form, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
import asyncio
from dotenv import load_dotenv

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
            "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://huggingface.co https://js.stripe.com "
            "'sha256-7PZaH7TzFg4JdT5xJguN7Och6VcMcP1LW4N3fQ936Fs=' "
            "'sha256-MqH8JJslY2fF2bGYY1rZlpCNrRCnWKRzrrDefixUJTI=' "
            "'sha256-ZswfTY7H35rbV8WC7NXBoiC7WNu86vSzCDChNWwZZDM=';"
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
            "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com;"
            "font-src 'self' https://fonts.gstatic.com data:;"
            "connect-src 'self' https://huggingface.co wss://huggingface.co https://*.hf.space wss://*.hf.space https://api.stripe.com;"
            "img-src 'self' data: blob: https://huggingface.co https://*.stripe.com;"
            "media-src 'self' data: blob: https://huggingface.co;"
            "frame-src 'self' https://js.stripe.com https://hooks.stripe.com;"
            "frame-ancestors 'self' https://huggingface.co;"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Modern Permissions-Policy (replaces deprecated Feature-Policy)
        response.headers["Permissions-Policy"] = "camera=*, microphone=*, geolocation=*, payment=*, usb=()"
        
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
            return

        conv = Conversation(
            user_id=user_db_id,
            transcript=transcript,
            meta_data={"reply_text": reply_text, **(metadata or {})},
            tts_path=tts_path,
            media_url=media_url
        )
        db.add(conv)
        await db.commit()
        print(f"[DEBUG] Saved conversation for user_id {user_db_id}")

        await ws_manager.broadcast({"type": "history_updated", "user_id": user_db_id})
    except Exception as e:
        logger.error("Failed to save conversation", error=str(e), user_id=user_db_id)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "https://huggingface.co",
        "https://krishibondhu.hf.space",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def create_database_tables():
    from sqlalchemy import text
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
async def upload_audio(
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

    initial_state["transcript"] = transcript
    initial_state["language"] = language

    try:
        # Use the new Crew-based logic
        from app.crews.krishi_crew import KrishiCrew
        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew()

        from crewai import Task
        from app.agents.bengali_interpreter import bengali_interpreter

        route_task = Task(
            description=f"Interpret the user's intent: {transcript}. Route to the best expert agent.",
            expected_output="A JSON object specifying the intent and a preliminary response.",
            agent=bengali_interpreter
        )

        result = await asyncio.to_thread(crew.kickoff, inputs=initial_state, tasks=[route_task])
        reply_text = str(result)

        user_db_id = current_user.id
        await save_conversation_to_db(
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
            conv_id=user_db_id
        )

        return JSONResponse({
            "transcript": transcript,
            "reply_text": reply_text,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post('/api/upload_image')
async def upload_image(
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

    initial_state = {
        "user_id": current_user.external_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "transcript": question,
        "language": detected_language,
    }
    try:
        from app.crews.krishi_crew import KrishiCrew
        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew()

        from crewai import Task
        from app.agents.disease_analyst import disease_analyst

        vision_task = Task(
            description=f"Analyze the soil/crop image at {image_path} and answer: {question}",
            expected_output="A technical diagnostic report with treatment recommendations.",
            agent=disease_analyst
        )

        result = await asyncio.to_thread(crew.kickoff, inputs=initial_state, tasks=[vision_task])
        reply_text = str(result)

        user_db_id = current_user.id
        await save_conversation_to_db(
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
            conv_id=user_db_id
        )

        return JSONResponse({
            "transcript": question,
            "reply_text": reply_text,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post('/api/chat')
async def chat(
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

    detected_language = detect_language_from_text(message)

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
        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew()

        from crewai import Task
        from app.agents.bengali_interpreter import bengali_interpreter

        route_task = Task(
            description=f"Interpret the user's intent from this message: {message}. Route to the most la- la la la appropriate expert agent.",
            expected_output="A JSON object with the intent and a a-dedicated response.",
            agent=bengali_interpreter
        )

        result = await asyncio.to_thread(crew.kickoff, inputs=initial_state, tasks=[route_task])
        reply_text = str(result)

        user_db_id = current_user.id
        await save_conversation_to_db(
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
            conv_id=user_db_id
        )

        return JSONResponse({
            "transcript": message,
            "reply_text": reply_text,
            "user_id": current_user.external_id,
            "gps": initial_state["gps"]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

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
