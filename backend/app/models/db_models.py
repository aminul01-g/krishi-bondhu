from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)  # farmer id from frontend
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    tts_path = Column(String, nullable=True)
    media_url = Column(String, nullable=True)  # Added in migration 0002
    confidence = Column(Float, nullable=True)  # Added in migration 0002
    meta_data = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
