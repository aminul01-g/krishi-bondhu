import asyncio
import os
from app.main import app

# For Vercel deployment
# Use a simple event loop for Vercel's serverless environment
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Export the FastAPI app for Vercel
__all__ = ["app"]
