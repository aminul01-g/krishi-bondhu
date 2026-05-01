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

class FarmDiary(Base):
    __tablename__ = "farm_diary"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) # Store external_id for easy query
    date = Column(DateTime(timezone=True), server_default=func.now())
    entry_type = Column(String, nullable=False)  # 'expense', 'income', 'yield'
    category = Column(String, nullable=True)  # e.g., 'fertilizer', 'labor', 'sales'
    amount = Column(Float, nullable=False)
    unit = Column(String, nullable=True)  # 'BDT', 'kg', 'mon'
    notes = Column(Text, nullable=True)
    crop = Column(String, nullable=True)
    plot = Column(String, nullable=True)

class CuratedTip(Base):
    __tablename__ = "curated_tips"
    id = Column(Integer, primary_key=True, index=True)
    crop = Column(String, index=True, nullable=False)
    growth_stage_days_start = Column(Integer, nullable=False)
    growth_stage_days_end = Column(Integer, nullable=False)
    category = Column(String, nullable=True)  # 'pest', 'fertilizer', 'general'
    tip_text_bn = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)