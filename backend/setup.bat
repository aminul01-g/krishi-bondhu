@echo off
REM Setup script for KrishiBondhu backend on Windows

echo.
echo ====================================
echo KrishiBondhu Backend Setup
echo ====================================
echo.

REM Install dependencies
echo [1/4] Installing Python dependencies...
call venv\Scripts\python.exe -m pip install -r requirements-minimal.txt
if errorlevel 1 (
    echo Error installing dependencies
    exit /b 1
)

echo.
echo [2/4] Starting PostgreSQL Docker container...
docker compose up -d postgres
if errorlevel 1 (
    echo Error starting Docker. Make sure Docker Desktop is running.
    exit /b 1
)

echo.
echo [3/4] Waiting for PostgreSQL to initialize...
timeout /t 10 /nobreak

echo.
echo [4/4] Running database migrations...
call venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo Error running migrations
    exit /b 1
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Create a .env file with your configuration
echo 2. Run the backend with: venv\Scripts\python.exe -m uvicorn app.main:app --reload
echo.
