FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install heavy dependencies (CPU only)
COPY requirements-heavy.txt .
RUN pip install --no-cache-dir -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
COPY requirements-lock.txt .
# Allow slightly looser constraints if strict versions conflict with CPU wheels
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
