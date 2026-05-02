"""
Input Marketplace Database Models
Phase 3 Implementation - Feature: Input Marketplace & Quality Verification
"""

from sqlalchemy import Column, String, Text, Integer, Float, Date, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.models.db_models import Base
from geoalchemy2 import Geometry


class Dealer(Base):
    """Agro-input dealer directory entry"""
    __tablename__ = "dealers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100))
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    location_geom = Column(Geometry(geometry_type='POINT', srid=4326))

    is_verified = Column(Boolean, default=False, index=True)
    verification_status = Column(String(50), default='pending', index=True)
    verified_at = Column(DateTime)
    verified_by = Column(String(128))

    regions_served = Column(JSON)  # JSON array of division names
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory = relationship("DealerInventory", back_populates="dealer", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_dealers_location', 'location_lat', 'location_lon'),
        Index('idx_dealers_verification', 'is_verified', 'verification_status'),
    )

    def __repr__(self):
        return f"<Dealer {self.name} @ {self.location_lat},{self.location_lon}>"


class DealerInventory(Base):
    """Inventory records for dealers"""
    __tablename__ = "dealer_inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dealer_id = Column(UUID(as_uuid=True), ForeignKey("dealers.id"), nullable=False, index=True)

    product_name = Column(String(200), nullable=False)
    input_type = Column(String(50), nullable=False)  # seed, fertilizer, pesticide
    crop_type = Column(String(50))  # rice, tomato, potato, etc.
    batch_number = Column(String(100))
    manufacturer = Column(String(200))

    quantity_in_stock = Column(Integer, nullable=False)
    price_bdt = Column(Float, nullable=False)
    expiry_date = Column(Date, nullable=False)

    added_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dealer = relationship("Dealer", back_populates="inventory")

    __table_args__ = (
        Index('idx_dealer_inventory_type_crop', 'input_type', 'crop_type'),
        Index('idx_dealer_inventory_expiry', 'expiry_date'),
    )

    def __repr__(self):
        return f"<DealerInventory {self.product_name} [{self.input_type}]>"


class VerifiedProduct(Base):
    """Registry of verified agro-input products"""
    __tablename__ = "verified_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    barcode = Column(String(50), nullable=False, unique=True, index=True)
    qr_code = Column(String(500))

    product_name = Column(String(200), nullable=False)
    manufacturer = Column(String(200), nullable=False)
    batch_number = Column(String(100), nullable=False, index=True)

    active_ingredient = Column(Text)
    npk_ratio = Column(String(20))
    dose_per_application = Column(String(100))

    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = Column(Date, nullable=False)
    government_registry = Column(String(50))

    is_verified = Column(Boolean, default=True, index=True)
    verification_source = Column(String(50), default='local_db')

    __table_args__ = (
        Index('idx_verified_products_expiry', 'expiry_date'),
    )

    def __repr__(self):
        return f"<VerifiedProduct {self.product_name} [{self.batch_number}]>"


class ProductScan(Base):
    """History of barcode/QR scans for farmers"""
    __tablename__ = "product_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id_hashed = Column(String(128), nullable=False, index=True)
    barcode = Column(String(50))
    qr_text = Column(String(500))
    verified_product_id = Column(UUID(as_uuid=True), ForeignKey("verified_products.id"), index=True)

    verification_result = Column(String(50), nullable=False)  # VERIFIED, UNREGISTERED, SUSPICIOUS, EXPIRED
    confidence_score = Column(Float)

    scanned_at = Column(DateTime, default=datetime.utcnow, index=True)
    location_lat = Column(Float)
    location_lon = Column(Float)

    verified_product = relationship("VerifiedProduct")

    __table_args__ = (
        Index('idx_product_scans_verified', 'verified_product_id', 'verification_result'),
    )

    def __repr__(self):
        return f"<ProductScan {self.barcode} - {self.verification_result}>"
