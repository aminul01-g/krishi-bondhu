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
    image: UploadFile = File(None)
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
