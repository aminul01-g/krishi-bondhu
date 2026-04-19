# --- Stage 1: Build Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Runtime ---
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements-heavy.txt ./
RUN pip install --no-cache-dir -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend from Stage 1 to a directory named 'static'
# backend/app/main.py is configured to serve this directory
COPY --from=frontend-builder /app/frontend/dist ./static

# Expose the port HF Spaces expects
EXPOSE 7860

# Run migrations and start server
# Using ${PORT:-7860} to be safe
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
