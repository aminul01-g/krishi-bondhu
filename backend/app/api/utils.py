import os
import aiofiles
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import HTTPException
from PIL import Image
import io

load_dotenv()
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/tmp/uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_audio_local(upload_file):
    """
    Save UploadFile to local UPLOAD_DIR and return the path.
    Validates file size (max 25MB).
    """
    content = await upload_file.read()
    
    # Validate file size (25MB max)
    if len(content) > 25_000_000:
        raise HTTPException(413, "Audio too large. Maximum 25MB.")
    
    suffix = os.path.splitext(upload_file.filename)[1] or '.webm'
    dest = os.path.join(UPLOAD_DIR, f"{uuid4().hex}{suffix}")
    async with aiofiles.open(dest, 'wb') as out:
        await out.write(content)
    return dest

async def save_image_local(upload_file):
    """
    Save uploaded image file to local UPLOAD_DIR and return the path.
    Validates file size (max 10MB) and resizes image.
    """
    content = await upload_file.read()
    
    # Validate file size (10MB max)
    if len(content) > 10_000_000:
        raise HTTPException(413, "Image too large. Maximum 10MB.")
    
    # Resize image
    img = Image.open(io.BytesIO(content))
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format=img.format or 'JPEG', quality=85)
    content = buf.getvalue()
    
    suffix = os.path.splitext(upload_file.filename)[1] or '.jpg'
    # Ensure valid image extension
    if suffix not in ['.jpg', '.jpeg', '.png', '.webp']:
        suffix = '.jpg'
    dest = os.path.join(UPLOAD_DIR, f"{uuid4().hex}{suffix}")
    async with aiofiles.open(dest, 'wb') as out:
        await out.write(content)
    return dest