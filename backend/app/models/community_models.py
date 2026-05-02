"""
Community Q&A Database Models
Phase 3 Implementation - Feature: Community Q&A & Local Expert Connect
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, ForeignKey, Index, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from app.models.db_models import Base
from geoalchemy2 import Geometry


class CommunityQuestion(Base):
    """Store farmer questions about crops and farming practices"""
    __tablename__ = "community_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Anonymized farmer info
    farmer_id_hashed = Column(String(128), nullable=False, index=True)
    
    # Question content
    question_text = Column(Text, nullable=False)
    question_text_en = Column(Text)  # English translation
    
    # Context
    crop_type = Column(String(50), nullable=False, index=True)  # rice, tomato, potato, etc.
    growth_stage = Column(String(50), index=True)  # seedling, vegetative, flowering, maturity
    
    # Media
    photo_url = Column(String(500))
    
    # Location
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    location_geom = Column(Geometry(geometry_type='POINT', srid=4326))
    
    # Vector embedding for semantic search
    embedding = Column(Vector(384))  # sentence-transformers output dimension
    
    # Status tracking
    status = Column(String(20), default='pending', index=True)  # pending, answered, escalated, removed
    moderation_flag = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    admin_review_needed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    answers = relationship("CommunityAnswer", back_populates="question", cascade="all, delete-orphan")
    escalation = relationship("EscalationQueue", back_populates="question", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_community_questions_crop_stage', 'crop_type', 'growth_stage'),
        Index('idx_community_questions_embedding', 'embedding', postgresql_using='ivfflat'),
        Index('idx_community_questions_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<CommunityQuestion {self.id} - {self.crop_type}>"


class CommunityAnswer(Base):
    """Answers to community questions from experts or experienced farmers"""
    __tablename__ = "community_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to question
    question_id = Column(UUID(as_uuid=True), ForeignKey("community_questions.id"), nullable=False, index=True)
    
    # Answerer info
    answerer_id = Column(String(128), nullable=False, index=True)  # Expert or farmer ID
    answerer_name = Column(String(100), nullable=False)
    answerer_credentials = Column(String(255))  # "Extension Officer, Dhaka" or "Senior Farmer"
    
    # Answer content
    answer_text = Column(Text, nullable=False)
    answer_text_en = Column(Text)  # English translation
    
    # Quality flags
    is_expert_answer = Column(Boolean, default=False)  # True if from agricultural expert
    is_verified = Column(Boolean, default=False)  # Admin verification
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    verified_at = Column(DateTime)
    
    # Relationships
    question = relationship("CommunityQuestion", back_populates="answers")
    upvotes = relationship("AnswerUpvote", back_populates="answer", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_community_answers_question_answerer', 'question_id', 'answerer_id'),
    )
    
    def __repr__(self):
        return f"<CommunityAnswer {self.id} by {self.answerer_name}>"


class AnswerUpvote(Base):
    """Upvote and rating system for answers"""
    __tablename__ = "answer_upvotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to answer
    answer_id = Column(UUID(as_uuid=True), ForeignKey("community_answers.id"), nullable=False, index=True)
    
    # Voter info
    farmer_id_hashed = Column(String(128), nullable=False)
    
    # Rating (1-5 stars, optional)
    rating = Column(Integer)  # 1-5, optional
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    answer = relationship("CommunityAnswer", back_populates="upvotes")
    
    __table_args__ = (
        # Ensure one vote per farmer per answer
        Index('idx_answer_upvotes_unique', 'answer_id', 'farmer_id_hashed', unique=True),
    )
    
    def __repr__(self):
        return f"<AnswerUpvote {self.id} - rating {self.rating}>"


class EscalationQueue(Base):
    """Queue for escalating unanswered questions to experts"""
    __tablename__ = "escalation_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to question
    question_id = Column(UUID(as_uuid=True), ForeignKey("community_questions.id"), nullable=False, unique=True)
    
    # Assigned expert
    expert_id = Column(String(128), ForeignKey("agricultural_experts.id"), index=True)
    
    # Status tracking
    status = Column(String(20), default='pending', index=True)  # pending, assigned, resolved, timeout
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    auto_escalate_at = Column(DateTime, index=True)  # If not answered by this time, escalate further
    assigned_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Relationships
    question = relationship("CommunityQuestion", back_populates="escalation")
    expert = relationship("AgriculturalExpert", back_populates="escalations")
    
    def __repr__(self):
        return f"<EscalationQueue {self.id} - {self.status}>"


class AgriculturalExpert(Base):
    """Directory of agricultural extension officers and experts"""
    __tablename__ = "agricultural_experts"

    id = Column(String(128), primary_key=True)  # Expert user ID
    region_geom = Column(Geometry(geometry_type='POINT', srid=4326))  # PostGIS point for spatial queries
    
    # Contact info
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100))
    
    # Location and service area
    region = Column(String(100), nullable=False, index=True)
    # PostGIS point geometry (handled separately in migrations)
    # region_geom stored in migration
    
    # Credentials and expertise
    credentials = Column(String(255))  # "Extension Officer", "Soil Scientist", etc.
    areas_of_expertise = Column(JSON)  # JSON array: ["rice", "wheat", "vegetables"]
    
    # Performance metrics
    response_time_avg_hours = Column(Float)  # Average response time
    total_answers = Column(Integer, default=0)
    rating_avg = Column(Float, default=4.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime)
    
    # Relationships
    escalations = relationship("EscalationQueue", back_populates="expert")
    
    def __repr__(self):
        return f"<AgriculturalExpert {self.name} - {self.region}>"
