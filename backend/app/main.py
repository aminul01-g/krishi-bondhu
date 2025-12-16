from fastapi import FastAPI, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os
from app.farm_agent.langgraph_app import app as langgraph_app
from app.api.utils import save_audio_local, save_image_local
from dotenv import load_dotenv
from app.api import routes as api_routes
from app.db import get_db

load_dotenv()

app = FastAPI(title="KrishiBondhu API")

# Helper to get/create user
from app.models.db_models import User, Conversation
from sqlalchemy import select

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
         print(f"[ERROR] Could not get/create user: {e}")
         return None

async def save_conversation_to_db(
    db: AsyncSession, 
    user_db_id: int, 
    transcript: str, 
    reply_text: str,
    metadata: dict = None,
    tts_path: str = None
):
    try:
        if not user_db_id:
            return
        
        # Ensure metadata is JSON serializable
        import json
        # Filter out unserializable objects if any (though clean_result should be fine)
        
        conv = Conversation(
            user_id=user_db_id,
            transcript=transcript,
            meta_data={"reply_text": reply_text, **(metadata or {})}, # Store reply in metadata as per schema
            tts_path=tts_path
        )
        db.add(conv)
        await db.commit()
        print(f"[DEBUG] Saved conversation for user_id {user_db_id}")
    except Exception as e:
        print(f"[ERROR] Failed to save conversation: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_routes.router, prefix="/api")

@app.post('/api/upload_audio')
async def upload_audio(
    file: UploadFile = File(...), 
    user_id: str = Form(...), 
    lat: float = Form(None), 
    lon: float = Form(None),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Save uploaded audio file (and optional image), invoke the LangGraph flow, and return the resulting state.
    """
    audio_path = await save_audio_local(file)
    image_path = None
    if image:
        image_path = await save_image_local(image)
    
    initial_state = {
        "audio_path": audio_path,
        "user_id": user_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "messages": []
    }
    try:
        # Use ainvoke for async nodes (respond_node is async)
        result = await langgraph_app.ainvoke(initial_state)
        # Ensure we always have a reply_text
        if not result.get("reply_text"):
             result["reply_text"] = "I processed your audio but couldn't generate a response. Please try again."

        # SAVE TO DB
        user_db_id = await get_current_user_db_id(user_id, db)
        await save_conversation_to_db(
            db, 
            user_db_id, 
            result.get("transcript", ""), 
            result.get("reply_text", ""), 
            metadata={
                "crop": result.get("crop"),
                "vision_result": result.get("vision_result"),
                "weather_forecast": result.get("weather_forecast"),
                "language": result.get("language"),
                "gps": result.get("gps")
            },
            tts_path=result.get("tts_path")
        )

        # Clean up non-serializable objects for JSON response
        clean_result = {
            "transcript": result.get("transcript", ""),
            "reply_text": result.get("reply_text", ""),
            "crop": result.get("crop"),
            "language": result.get("language"),
            "vision_result": result.get("vision_result"),
            "weather_forecast": result.get("weather_forecast"),
            "tts_path": result.get("tts_path"),
            "user_id": result.get("user_id", user_id),
            "gps": result.get("gps", {"lat": lat, "lon": lon})
        }
        return JSONResponse(clean_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a helpful error response instead of crashing
        return JSONResponse({
            "error": str(e),
            "reply_text": "I apologize, but I'm experiencing technical difficulties processing your audio. Please try again in a moment.",
            "user_id": user_id
        }, status_code=500)

@app.post('/api/upload_image')
async def upload_image(
    image: UploadFile = File(...),
    user_id: str = Form(...),
    lat: float = Form(None),
    lon: float = Form(None),
    question: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload image for analysis. Can include optional text question.
    """
    # Import language detection function
    from app.services.audio import detect_language_from_text
    
    image_path = await save_image_local(image)
    
    # CRITICAL: Detect language from question if provided
    detected_language = "en"
    if question:
        detected_language = detect_language_from_text(question)
        print(f"[DEBUG] /api/upload_image: Question language detected: {detected_language}")
    
    initial_state = {
        "audio_path": None,
        "user_id": user_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "transcript": question,  # Use question as transcript if provided
        "language": detected_language,  # SET LANGUAGE HERE!
        "messages": []
    }
    try:
        # Skip STT if no audio, go directly to intent/vision
        # We'll modify the flow to handle image-only queries
        result = await langgraph_app.ainvoke(initial_state)
        # Ensure we always have a reply_text
        # Ensure we always have a reply_text
        if not result.get("reply_text"):
             result["reply_text"] = "I analyzed your image but couldn't generate a detailed response. Please try again."

        # SAVE TO DB
        user_db_id = await get_current_user_db_id(user_id, db)
        await save_conversation_to_db(
            db, 
            user_db_id, 
            result.get("transcript", question), 
            result.get("reply_text", ""), 
            metadata={
                "crop": result.get("crop"),
                "vision_result": result.get("vision_result"),
                "weather_forecast": result.get("weather_forecast"),
                "language": result.get("language"),
                "gps": result.get("gps")
            },
            tts_path=result.get("tts_path")
        )
        
        # Clean up non-serializable objects for JSON response
        clean_result = {
            "transcript": result.get("transcript", question),
            "reply_text": result.get("reply_text", ""),
            "crop": result.get("crop"),
            "language": result.get("language"),
            "vision_result": result.get("vision_result"),
            "weather_forecast": result.get("weather_forecast"),
            "tts_path": result.get("tts_path"),
            "user_id": result.get("user_id", user_id),
            "gps": result.get("gps", {"lat": lat, "lon": lon})
        }
        return JSONResponse(clean_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a helpful error response instead of crashing
        return JSONResponse({
            "error": str(e),
            "reply_text": "I apologize, but I'm experiencing technical difficulties processing your image. Please try again in a moment.",
            "transcript": question,
            "user_id": user_id
        }, status_code=500)

@app.post('/api/chat')
async def chat(
    message: str = Form(...),
    user_id: str = Form(...),
    lat: float = Form(None),
    lon: float = Form(None),
    image: UploadFile = File(None),
    include_history: bool = Form(True),  # NEW: Option to include chat history
    db: AsyncSession = Depends(get_db)
):
    """
    Text-based chatbot endpoint. Can include optional image and chat history.
    """
    # Import language detection function
    from app.services.audio import detect_language_from_text
    from sqlalchemy import select, desc
    from app.models.db_models import Conversation
    
    image_path = None
    if image:
        image_path = await save_image_local(image)
    
    # CRITICAL: Detect language from message BEFORE passing to workflow
    detected_language = detect_language_from_text(message)
    print(f"[DEBUG] /api/chat: Message language detected: {detected_language}")
    
    # NEW: Load chat history for context (last 5 conversations)
    messages = [{"role": "user", "content": message}]
    if include_history and db:
        try:
            # Query previous conversations for this user
            # First get internal numeric ID
            user_db_id = await get_current_user_db_id(user_id, db)
            
            if user_db_id:
                result = await db.execute(
                    select(Conversation)
                    .where(Conversation.user_id == user_db_id)
                    .order_by(desc(Conversation.created_at))
                    .limit(5)  # Get last 5 conversations
                )
                previous_convs = result.scalars().all()
            
            # Reverse to get chronological order (oldest to newest)
            previous_convs = list(reversed(previous_convs))
            
            # Add to messages in conversational format
            for conv in previous_convs:
                if conv.transcript:
                    messages.insert(0, {"role": "user", "content": conv.transcript})
                if conv.meta_data and conv.meta_data.get("reply_text"):
                    messages.insert(1, {"role": "assistant", "content": conv.meta_data.get("reply_text", "")})
            
            print(f"[DEBUG] /api/chat: Loaded {len(previous_convs)} previous conversations for user {user_id}")
        except Exception as e:
            print(f"[DEBUG] /api/chat: Could not load history: {e}")
            # Continue without history if database fails
            pass
    
    initial_state = {
        "audio_path": None,
        "user_id": user_id,
        "gps": {"lat": lat, "lon": lon},
        "image_path": image_path,
        "transcript": message,  # Use message as transcript
        "language": detected_language,  # SET LANGUAGE HERE!
        "messages": messages  # Now includes history if available
    }
    try:
        # For text-only chat, skip STT and go to reasoning
        result = await langgraph_app.ainvoke(initial_state)
        # Ensure we always have a reply_text
        # Ensure we always have a reply_text
        if not result.get("reply_text"):
            result["reply_text"] = "I received your message but couldn't generate a response. Please try again."
        
        # SAVE TO DB
        user_db_id = await get_current_user_db_id(user_id, db)
        await save_conversation_to_db(
            db, 
            user_db_id, 
            result.get("transcript", ""), 
            result.get("reply_text", ""), 
            metadata={
                "crop": result.get("crop"),
                "vision_result": result.get("vision_result"),
                "weather_forecast": result.get("weather_forecast"),
                "language": result.get("language"),
                "gps": result.get("gps")
            },
            tts_path=result.get("tts_path")
        )

        # Clean up non-serializable objects for JSON response
        clean_result = {
            "transcript": result.get("transcript", ""),
            "reply_text": result.get("reply_text", ""),
            "crop": result.get("crop"),
            "language": result.get("language"),
            "vision_result": result.get("vision_result"),
            "weather_forecast": result.get("weather_forecast"),
            "tts_path": result.get("tts_path"),
            "user_id": result.get("user_id", user_id),
            "gps": result.get("gps", {"lat": lat, "lon": lon})
        }
        return JSONResponse(clean_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a helpful error response instead of crashing
        error_msg = str(e)
        return JSONResponse({
            "error": error_msg,
            "reply_text": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
            "transcript": message,
            "user_id": user_id
        }, status_code=500)


@app.get('/api/get_tts')
async def get_tts(path: str):
    """
    Return a generated tts mp3 by local path.
    The path is URL-encoded in the query parameter, so we need to decode it.
    Supports both old /tmp/ location and new UPLOAD_DIR location for backward compatibility.
    Silently handles old temp files that no longer exist.
    """
    from urllib.parse import unquote
    from app.api.utils import UPLOAD_DIR
    import re
    from fastapi import Response
    
    # URL decode the path parameter
    decoded_path = unquote(path)
    filename = os.path.basename(decoded_path)
    
    print(f"[DEBUG] get_tts requested: {decoded_path}")
    print(f"[DEBUG] get_tts UPLOAD_DIR: {UPLOAD_DIR}")
    
    # Check if this is an old temporary file pattern (from before the fix)
    # Pattern: tmp followed by alphanumeric characters and underscores, ending with .mp3
    # Python's tempfile can generate names like tmpXXXXXX or tmpXXXX_XX
    is_old_temp_file = (
        re.match(r'^tmp[a-z0-9_]+\.mp3$', filename, re.IGNORECASE) and 
        decoded_path.startswith('/tmp/') and 
        not decoded_path.startswith('/tmp/uploads/')
    )
    
    # Check if file exists at the requested path
    if os.path.exists(decoded_path):
        file_size = os.path.getsize(decoded_path)
        print(f"[DEBUG] get_tts: Serving file from requested path: {decoded_path} (size: {file_size} bytes)")
        return FileResponse(decoded_path, media_type='audio/mpeg', filename=filename)
    
    # If file not found, try to find it in UPLOAD_DIR (for backward compatibility)
    upload_dir_path = os.path.join(UPLOAD_DIR, filename)
    
    if os.path.exists(upload_dir_path):
        file_size = os.path.getsize(upload_dir_path)
        print(f"[DEBUG] get_tts: Serving file from UPLOAD_DIR: {upload_dir_path} (size: {file_size} bytes)")
        return FileResponse(upload_dir_path, media_type='audio/mpeg', filename=filename)
    
    # File not found - handle old temp files silently (they're expected to be missing)
    if is_old_temp_file:
        # Return 204 No Content instead of 404 to avoid uvicorn logging "404 Not Found"
        # This is a silent response that won't clutter the logs
        print(f"[DEBUG] get_tts: Old temp file, returning 204: {decoded_path}")
        return Response(status_code=204)
    
    # New file that should exist but doesn't - return 204 silently for old database records
    # This handles the case where database contains old TTS paths from previous test runs
    print(f"[WARN] get_tts: TTS file not found (likely old database record): {decoded_path}")
    
    # Return 204 No Content instead of 404 to avoid logging noise
    # The frontend will gracefully handle missing audio without breaking
    return Response(status_code=204)