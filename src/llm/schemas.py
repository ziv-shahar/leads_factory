"""Pydantic schemas for LLM extraction and enrichment."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DynamicSignal(BaseModel):
    """A catch-all signal for information not fitting strict schema."""
    signal_type: str = Field(..., description="Type of signal (e.g., 'acquisition_rumor', 'government_expansion')")
    description: str = Field(..., description="Clear description of the signal")
    evidence_quote: Optional[str] = Field(None, description="Direct quote from source as evidence")


class KeyFact(BaseModel):
    """Structured key facts extracted from the event."""
    amount: Optional[str] = None  # e.g., "$50M", "500 employees"
    city: Optional[str] = None  # City where event occurred
    state: Optional[str] = None  # State/country where event occurred
    people: Optional[List[str]] = None
    dates: Optional[List[str]] = None
    companies: Optional[List[str]] = None  # Related companies (partners, competitors, etc.)
    products: Optional[List[str]] = None
    other: Optional[Dict[str, Any]] = None

    @field_validator('amount', 'city', 'state', mode='before')
    @classmethod
    def convert_empty_list_to_none(cls, v):
        """Convert empty lists to None for string fields (LLM sometimes returns [])."""
        if isinstance(v, list) and len(v) == 0:
            return None
        if isinstance(v, list):
            # If it's a non-empty list, take the first item (shouldn't happen, but be defensive)
            return v[0] if v else None
        return v


class NormalizedEvent(BaseModel):
    """Strict schema for normalized event extraction for a single company."""
    # Core identification
    company_name_raw: str = Field(..., description="Company name exactly as it appears in source")
    company_name_canonical: str = Field(..., description="Normalized company name (UPPERCASE, legal suffixes removed)")

    # Event classification
    event_type: str = Field(..., description="Event type from predefined list")
    summary: str = Field(..., description="Brief summary of the event (1-2 sentences)")

    # Optional structured data
    key_facts: Optional[KeyFact] = Field(None, description="Structured facts extracted from event")
    source_url: Optional[str] = Field(None, description="URL mentioned in source if available")
    event_date: Optional[str] = Field(None, description="When the event occurred (ISO format if possible)")

    # Quality metrics
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction (0.0-1.0)")
    missing_fields: List[str] = Field(default_factory=list, description="List of fields that couldn't be extracted")

    # Dynamic catch-all
    dynamic_signals: List[DynamicSignal] = Field(
        default_factory=list,
        description="Additional valuable signals not fitting strict schema"
    )

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type against known types."""
        from src.config import EVENT_TYPES
        # Allow "other" as fallback
        if v not in EVENT_TYPES:
            return "other"
        return v

    @field_validator('company_name_canonical')
    @classmethod
    def canonicalize_name(cls, v):
        """Ensure canonical name is uppercase and normalized."""
        if not v:
            return v

        # Uppercase
        canonical = v.upper().strip()

        # Remove common legal suffixes
        suffixes = [
            ' INC', ' INC.', ' INCORPORATED',
            ' LLC', ' LLC.', ' L.L.C', ' L.L.C.',
            ' LTD', ' LTD.', ' LIMITED',
            ' CORP', ' CORP.', ' CORPORATION',
            ' CO', ' CO.', ' COMPANY',
            ' LP', ' L.P.', ' LLP', ' L.L.P.'
        ]

        for suffix in suffixes:
            if canonical.endswith(suffix):
                canonical = canonical[:-len(suffix)].strip()

        # Normalize common patterns
        canonical = canonical.replace(' AND ', ' & ')
        canonical = canonical.replace(',', ' ')
        canonical = ' '.join(canonical.split())  # Normalize whitespace

        return canonical


class DocumentExtraction(BaseModel):
    """Complete extraction result from a document, supporting multiple companies."""
    # Document-level relevance check
    is_relevant: bool = Field(..., description="True if document relates to the business objective")
    relevance_reasoning: str = Field(..., description="Why this document is/isn't relevant to the business objective")

    # Events extracted (one per company mentioned)
    events: List[NormalizedEvent] = Field(
        ...,
        min_length=0,
        description="List of events, one for each company mentioned in the document"
    )


class EnrichmentResult(BaseModel):
    """Result from enrichment LLM step."""
    official_domain: Optional[str] = Field(None, description="Official domain (e.g., 'acmecloud.io')")
    website_url: Optional[str] = Field(None, description="Full website URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company page URL")
    hq_city: Optional[str] = Field(None, description="Headquarters city")
    hq_state: Optional[str] = Field(None, description="Headquarters state/country")
    enrichment_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in enrichment")
    reasoning: Optional[str] = Field(None, description="Why these values were chosen")

    @field_validator('hq_city', 'hq_state', mode='before')
    @classmethod
    def convert_empty_list_to_none(cls, v):
        """Convert empty lists to None for string fields (LLM sometimes returns [])."""
        if isinstance(v, list) and len(v) == 0:
            return None
        if isinstance(v, list):
            return v[0] if v else None
        return v


# Helper function to get normalized name (no punctuation/spaces)
def get_normalized_name(canonical_name: str) -> str:
    """Convert canonical name to normalized form (no punct, no spaces)."""
    import re
    # Remove all non-alphanumeric characters
    normalized = re.sub(r'[^A-Z0-9]', '', canonical_name.upper())
    return normalized
