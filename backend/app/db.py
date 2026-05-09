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
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend.db'))
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    database_url = f"sqlite+aiosqlite:///{sqlite_path}"
    print(f"[INFO] Using persistent SQLite fallback database at {sqlite_path}")

DATABASE_URL = database_url

# Create engine with appropriate settings based on database type
if "sqlite" in DATABASE_URL:
    from sqlalchemy.pool import NullPool
    
    # We need to enable spatialite for SQLite
    async def create_sqlite_connection():
        import aiosqlite
        conn = await aiosqlite.connect(sqlite_path)
        await conn.enable_load_extension(True)
        try:
            await conn.load_extension("mod_spatialite")
        except Exception as e:
            print(f"[WARNING] Could not load mod_spatialite directly: {e}. Trying alternative names.")
            try:
                await conn.load_extension("mod_spatialite.so")
            except Exception as e2:
                print(f"[WARNING] Failed to load mod_spatialite.so: {e2}")
        return conn

    engine = create_async_engine(
        "sqlite+aiosqlite://", # We use empty URL and pass a creator
        creator=create_sqlite_connection,
        future=True,
        echo=False,
        poolclass=NullPool
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


async def get_db_session():
    async for session in get_db():
        yield session
