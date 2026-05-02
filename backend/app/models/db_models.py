import uuid
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

class SoilTestLog(Base):
    __tablename__ = "soil_test_logs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    crop = Column(String)
    image_url = Column(String, nullable=True)
    diy_inputs = Column(JSON, nullable=True) # E.g., {"ribbon_length_cm": 2.5, "color": "dark brown"}
    derived_texture = Column(String, nullable=True)
    derived_ph = Column(Float, nullable=True)
    recommendations = Column(JSON, nullable=True)

class IrrigationLog(Base):
    __tablename__ = "irrigation_logs"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    soil_moisture_index = Column(Float, nullable=True)
    advice = Column(Text, nullable=True)
    action_taken = Column(Integer, default=0) # 0: No, 1: Yes

class FinanceScheme(Base):
    __tablename__ = "finance_schemes"
    id = Column(Integer, primary_key=True, index=True)
    name_bn = Column(String, nullable=False)
    name_en = Column(String, nullable=True)
    category = Column(String, nullable=True) # 'Subsidy', 'Loan', 'Insurance'
    eligibility_criteria = Column(JSON, nullable=True)
    description_bn = Column(Text, nullable=True)
    how_to_apply_bn = Column(Text, nullable=True)
    apply_link = Column(String, nullable=True)

class InsuranceQuote(Base):
    __tablename__ = "insurance_quotes"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    crop = Column(String, nullable=False)
    land_size = Column(Float, nullable=True)
    premium_estimate = Column(Float, nullable=True)
    payout_triggers = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
