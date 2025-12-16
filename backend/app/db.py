import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy import select, text
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for development if PostgreSQL is not available
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Try to use SQLite in-memory or file-based as fallback
    database_url = "sqlite+aiosqlite:///:memory:"
    print("[INFO] Using SQLite in-memory database for development")

DATABASE_URL = database_url

# Create engine with appropriate settings based on database type
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        future=True,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL connection
    engine = create_async_engine(
        DATABASE_URL, 
        future=True, 
        echo=False,
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,    # Recycle connections after 1 hour
        connect_args={
            "server_settings": {
                "application_name": "farmassist"
            }
        }
    )
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Dependency for FastAPI endpoints if needed
async def get_db():
    """
    Database dependency that provides async SQLAlchemy session.
    Handles cleanup properly without testing connections in the dependency itself.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        # Always close the session, even if an exception occurred
        try:
            await session.close()
        except Exception as e:
            print(f"Error closing database session: {e}")