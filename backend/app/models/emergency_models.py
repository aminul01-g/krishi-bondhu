"""
Emergency & Insurance Database Models
Phase 3 Implementation - Feature: Emergency & Crop Insurance Quick Claim
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.models.db_models import Base
from geoalchemy2 import Geometry


class InsuranceProvider(Base):
    """Insurance provider configuration for claims """
    __tablename__ = "insurance_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    email = Column(String(100))
    phone_number = Column(String(20))

    api_endpoint = Column(String(500))
    api_key = Column(String(500))

    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claims = relationship("DamageReport", back_populates="insurance_provider")

    def __repr__(self):
        return f"<InsuranceProvider {self.name}>"


class DamageReport(Base):
    """Structured damage report for insurance claims"""
    __tablename__ = "damage_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(String(128), nullable=False, index=True)
    crop_type = Column(String(50), nullable=False, index=True)
    growth_stage = Column(String(50))

    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    location_geom = Column(Geometry(geometry_type='POINT', srid=4326))

    damage_cause = Column(String(100), nullable=False)
    damage_estimate_percent = Column(Float, nullable=False)
    yield_loss_estimate_percent = Column(Float, nullable=False)

    number_of_photos = Column(Integer, default=0)
    voice_statement_transcribed = Column(Text)
    voice_statement_transcribed_en = Column(Text)

    status = Column(String(50), default='submitted', index=True)  # submitted, under_review, approved, rejected, claimed

    insurance_provider_id = Column(UUID(as_uuid=True), ForeignKey("insurance_providers.id"), index=True)
    insurance_claim_id = Column(String(128))

    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    claimed_at = Column(DateTime)

    pdf_url = Column(String(500))

    insurance_provider = relationship("InsuranceProvider", back_populates="claims")
    images = relationship("ReportImage", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_damage_reports_status', 'status'),
        Index('idx_damage_reports_location', 'location_lat', 'location_lon'),
    )

    def __repr__(self):
        return f"<DamageReport {self.id} - {self.crop_type} - {self.status}>"


class ReportImage(Base):
    """Photos associated with a damage report"""
    __tablename__ = "report_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("damage_reports.id"), nullable=False, index=True)

    image_data = Column(Text)  # Base64 text or URL
    image_url = Column(String(500))
    image_order = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("DamageReport", back_populates="images")

    def __repr__(self):
        return f"<ReportImage {self.id} for {self.report_id}>"


class HelplineCallLog(Base):
    """Log of helpline contact attempts"""
    __tablename__ = "helpline_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(String(128), nullable=False, index=True)
    location_lat = Column(Float)
    location_lon = Column(Float)
    crop_type = Column(String(50))
    damage_estimate = Column(Float)

    call_time = Column(DateTime, default=datetime.utcnow, index=True)
    call_duration_seconds = Column(Integer)
    status = Column(String(50), default='initiated')  # initiated, connected, completed, missed
    operator_notes = Column(Text)
    follow_up_scheduled = Column(DateTime)

    def __repr__(self):
        return f"<HelplineCallLog {self.id} - {self.farmer_id}>"
