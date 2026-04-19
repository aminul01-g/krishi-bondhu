# --- Stage 1: Build Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
ENV NODE_ENV=production
# Increase memory limit for Node.js build process
ENV NODE_OPTIONS="--max-old-space-size=4096"
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
# Prevent pip timeouts on large ML packages
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
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

# Consolidate PIP installation
RUN pip install --no-cache-dir -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-lock.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from Stage 1 to 'static' directory
COPY --from=frontend-builder /app/frontend/dist ./static

# Expose port
EXPOSE 7860

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
