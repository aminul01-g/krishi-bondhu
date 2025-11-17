import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config
from alembic import context
import os
import sys
# Add the backend directory to the path so we can import app modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config
fileConfig(config.config_file_name)

# Interpret the config file for Python logging.
from app.models.db_models import Base
from app.db import DATABASE_URL

def get_url():
    # Get DATABASE_URL from environment or use default
    url = os.getenv("DATABASE_URL", DATABASE_URL)
    # Convert asyncpg URL to psycopg2 for Alembic (Alembic uses sync driver)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

def run_migrations_offline():
    url = get_url()
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = get_url()
    # Update config with the converted URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
