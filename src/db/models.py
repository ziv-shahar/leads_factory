"""SQLAlchemy models for lead intelligence pipeline."""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, UniqueConstraint, Index, text
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
    """Universal entity model - works for companies, governments, contractors, nonprofits, etc."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields (work for ANY entity)
    canonical_name = Column(String(512), nullable=False)  # e.g., "ACME CLOUD"
    normalized_name = Column(String(512), nullable=False)  # e.g., "ACMECLOUD" (no punct/spaces)
    domain = Column(String(255), nullable=True, unique=True)  # Works for .com, .gov, .org, etc.

    # Classification (informational label, not a logic driver)
    entity_type = Column(String(50), nullable=True)  # "company", "government_agency", "municipality", "contractor", "nonprofit"

    # Flexible storage for ANY entity-specific data
    entity_metadata = Column(JSONB, nullable=False, default=dict)
    """
    Flexible JSONB storage for entity-specific information. Examples:

    For companies:
    {
      "website_url": "https://acme.com",
      "linkedin_url": "https://linkedin.com/company/acme",
      "hq_city": "San Francisco",
      "hq_state": "CA",
      "industry": "Cloud Computing",
      "employee_count": 500
    }

    For government agencies:
    {
      "website_url": "https://www.gsa.gov",
      "gov_domain": "gsa.gov",
      "agency_code": "GSA",
      "jurisdiction": "federal",
      "parent_agency": "Independent Agency",
      "hq_city": "Washington",
      "hq_state": "DC"
    }

    For contractors:
    {
      "website_url": "https://acmeconstruction.com",
      "linkedin_url": "...",
      "sam_gov_uei": "ABC123DEF456",
      "duns_number": "123456789",
      "cage_code": "1A2B3",
      "naics_codes": ["236220", "238210"],
      "hq_city": "Miami",
      "hq_state": "FL"
    }
    """

    last_enriched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="entity", cascade="all, delete-orphan")
    lead = relationship("LeadCurrent", back_populates="entity", uselist=False, cascade="all, delete-orphan")
    location_leads = relationship("LocationLead", back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_entities_canonical_name', 'canonical_name'),
        Index('idx_entities_normalized_name', 'normalized_name'),
        Index('idx_entities_domain', 'domain'),
        Index('idx_entities_entity_type', 'entity_type'),
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

    # Government opportunity tracking (for upsert logic)
    opportunity_id = Column(String(255), nullable=True, index=True)  # Unique ID from SAM.gov
    expired_at = Column(DateTime, nullable=True)  # When response_deadline passed (soft delete)

    # Relationships
    entity = relationship("Entity", back_populates="events")

    __table_args__ = (
        Index('idx_events_entity_id', 'entity_id'),
        Index('idx_events_event_type', 'event_type'),
        Index('idx_events_event_time', 'event_time'),
        Index('idx_events_opportunity_id', 'opportunity_id'),
        Index('idx_events_expired_at', 'expired_at', postgresql_where=text('expired_at IS NULL')),
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


class LocationLead(Base):
    """Location-based leads - track entity activities per state."""
    __tablename__ = "location_leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)

    # Normalized location (always 2-letter state code)
    state = Column(String(2), nullable=False)  # "FL", "CA", "TX", etc.
    city = Column(String(255), nullable=True)  # Optional - most significant city for this entity in the state

    # Scoring
    score = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    status = Column(String(50), nullable=False, default="NEW")  # NEW, CONTACTED, QUALIFIED, CONVERTED, DISMISSED

    # Metadata
    event_count = Column(Integer, nullable=False, default=0)
    reasons = Column(JSONB, nullable=False, default=dict)  # Evidence + reasoning by event type
    last_event_date = Column(DateTime, nullable=True)  # Most recent event in this location
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="location_leads")

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('entity_id', 'state', name='uq_entity_state'),
        Index('idx_location_leads_state', 'state'),
        Index('idx_location_leads_score', 'score'),
        Index('idx_location_leads_status', 'status'),
        Index('idx_location_leads_entity_state', 'entity_id', 'state'),
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
