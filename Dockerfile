FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/requirements-heavy.txt ./
RUN pip install --no-cache-dir -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy backend application code
COPY backend/ ./

EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
