import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy import select, text, event
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Resolve database URL
# ---------------------------------------------------------------------------
database_url = os.getenv("DATABASE_URL")
if not database_url:
    sqlite_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'backend.db')
    )
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    database_url = f"sqlite+aiosqlite:///{sqlite_path}"
    print(f"[INFO] Using persistent SQLite fallback database at {sqlite_path}")

DATABASE_URL = database_url

# ---------------------------------------------------------------------------
# Engine creation
# ---------------------------------------------------------------------------
if "sqlite" in DATABASE_URL:
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        DATABASE_URL,
        future=True,
        echo=False,
        # StaticPool reuses one connection – ideal for SQLite which does not
        # support concurrent writers.  NullPool also works but StaticPool
        # avoids repeated file-open overhead.
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # ------------------------------------------------------------------
    # Optional SpatiaLite loading — runs on the raw *synchronous* DBAPI
    # connection every time a new connection is checked out of the pool.
    # ------------------------------------------------------------------
    _spatialite_warned = False

    @event.listens_for(engine.sync_engine, "connect")
    def _load_spatialite(dbapi_conn, connection_record):
        """Attempt to load mod_spatialite on the raw DBAPI connection.

        This callback receives the *synchronous* pysqlite / aiosqlite
        DBAPI connection, so calling ``enable_load_extension`` /
        ``load_extension`` directly is safe and correct.
        """
        global _spatialite_warned
        try:
            dbapi_conn.enable_load_extension(True)
            dbapi_conn.load_extension("mod_spatialite")
        except Exception:
            if not _spatialite_warned:
                print(
                    "[INFO] SpatiaLite not available – geospatial features "
                    "disabled.  Install libspatialite-dev if needed."
                )
                _spatialite_warned = True

else:
    # PostgreSQL connection
    engine = create_async_engine(
        DATABASE_URL,
        future=True,
        echo=False,
        pool_pre_ping=True,     # Verify connections before using them
        pool_recycle=3600,       # Recycle connections after 1 hour
        connect_args={
            "server_settings": {
                "application_name": "farmassist"
            }
        },
    )

AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
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
