import os
import aiofiles
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/tmp/uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_audio_local(upload_file):
    """
    Save UploadFile to local UPLOAD_DIR and return the path.
    """
    suffix = os.path.splitext(upload_file.filename)[1] or '.webm'
    dest = os.path.join(UPLOAD_DIR, f"{uuid4().hex}{suffix}")
    async with aiofiles.open(dest, 'wb') as out:
        content = await upload_file.read()
        await out.write(content)
    return dest

async def save_image_local(upload_file):
    """
    Save uploaded image file to local UPLOAD_DIR and return the path.
    """
    suffix = os.path.splitext(upload_file.filename)[1] or '.jpg'
    # Ensure valid image extension
    if suffix not in ['.jpg', '.jpeg', '.png', '.webp']:
        suffix = '.jpg'
    dest = os.path.join(UPLOAD_DIR, f"{uuid4().hex}{suffix}")
    async with aiofiles.open(dest, 'wb') as out:
        content = await upload_file.read()
        await out.write(content)
    return dest
