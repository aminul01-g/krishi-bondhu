# --- Stage 1: Build Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
# Set production environment
ENV NODE_ENV=production
COPY frontend/package*.json ./
RUN npm install --include=dev
COPY frontend/ ./
# CI=false prevents Vite from failing on warnings
RUN CI=false npm run build

# --- Stage 2: Runtime ---
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Install system dependencies
# Including ffmpeg and libsm6/libxext6 for OpenCV/Audio
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    ffmpeg \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements-heavy.txt backend/requirements-lock.txt ./

# Consolidate PIP installation to reduce layers and handle conflicts
# Using CPU-specific wheels for PyTorch to save space
RUN pip install --no-cache-dir -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-lock.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from Stage 1 to 'static' directory
COPY --from=frontend-builder /app/frontend/dist ./static

# Expose port (default for HF Spaces is 7860)
EXPOSE 7860

# Run migrations and start server
# Using uvicorn directly
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
