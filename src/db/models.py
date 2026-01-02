"""SQLAlchemy models for lead intelligence pipeline."""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class RawEvent(Base):
    """Tracks ingested raw files and their processing status."""
    __tablename__ = "raw_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(255), nullable=False)  # e.g., "manual", "scraper", "api"
    file_path = Column(String(1024), nullable=False)  # or s3_uri in production
    content_hash = Column(String(64), nullable=False, unique=True)  # SHA256 for deduplication
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="NEW")  # NEW, PROCESSED, FAILED
    error = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_raw_events_status', 'status'),
        Index('idx_raw_events_content_hash', 'content_hash'),
    )


class Entity(Base):
    """Deduped entities (companies, orgs, projects, etc.)."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name = Column(String(512), nullable=False)  # e.g., "ACME CLOUD"
    normalized_name = Column(String(512), nullable=False)  # e.g., "ACMECLOUD" (no punct/spaces)
    domain = Column(String(255), nullable=True, unique=True)  # Best global identifier
    website_url = Column(String(1024), nullable=True)
    linkedin_url = Column(String(1024), nullable=True)
    hq_location = Column(String(512), nullable=True)
    last_enriched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="entity", cascade="all, delete-orphan")
    lead = relationship("LeadCurrent", back_populates="entity", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_entities_canonical_name', 'canonical_name'),
        Index('idx_entities_normalized_name', 'normalized_name'),
        Index('idx_entities_domain', 'domain'),
    )


class Event(Base):
    """Normalized events extracted from sources."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(255), nullable=False)  # e.g., "web_scrape", "news_api"
    event_type = Column(String(100), nullable=False)  # funding_round, partnership, etc.
    event_time = Column(DateTime, nullable=True)  # When the event occurred (if known)
    ingest_time = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Structured data
    strict = Column(JSONB, nullable=False, default=dict)  # Strict schema fields
    dynamic_signals = Column(JSONB, nullable=False, default=list)  # Catch-all signals

    extraction_confidence = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    raw_ref = Column(String(1024), nullable=False)  # Reference to raw file

    # Relationships
    entity = relationship("Entity", back_populates="events")

    __table_args__ = (
        Index('idx_events_entity_id', 'entity_id'),
        Index('idx_events_event_type', 'event_type'),
        Index('idx_events_event_time', 'event_time'),
    )


class LeadCurrent(Base):
    """Materialized current state of leads for UI/API queries."""
    __tablename__ = "leads_current"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, unique=True)
    score = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    status = Column(String(50), nullable=False, default="NEW")  # NEW, ACTIVE, STALE, DISMISSED
    reasons = Column(JSONB, nullable=False, default=dict)  # Evidence + reasoning
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="lead")

    __table_args__ = (
        Index('idx_leads_current_score', 'score'),
        Index('idx_leads_current_status', 'status'),
    )


class LeadStateHistory(Base):
    """Append-only history of lead state changes for explainability."""
    __tablename__ = "lead_state_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)
    reasons = Column(JSONB, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_lead_history_entity_id', 'entity_id'),
        Index('idx_lead_history_changed_at', 'changed_at'),
    )
