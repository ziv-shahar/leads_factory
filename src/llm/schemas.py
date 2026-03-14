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
    aboa_sf_min: Optional[int] = None  # Minimum office space (ABOA square feet) for government leases
    aboa_sf_max: Optional[int] = None  # Maximum office space (ABOA square feet) for government leases
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
    """Universal event extraction schema - works for any entity type."""
    # Core entity identification
    entity_name_raw: str = Field(..., description="Entity name exactly as it appears in source")
    entity_name_canonical: str = Field(..., description="Normalized entity name (UPPERCASE, legal suffixes removed)")

    # Optional: LLM infers entity type if clear from context
    entity_type: Optional[str] = Field(
        None,
        description="Entity type if identifiable: company, government_agency, municipality, contractor, nonprofit, etc. Leave null if unclear."
    )

    # Flexible entity metadata - LLM extracts what's relevant
    entity_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="""Any identifying information about the entity. Examples:
        - For companies: website_url, linkedin_url, industry, employee_count
        - For government: agency_code, jurisdiction (federal/state/local), parent_agency, gov_domain
        - For contractors: sam_gov_uei, duns_number, cage_code, naics_codes
        - Common: hq_city, hq_state, phone, address
        Extract whatever is present in the document."""
    )

    # Event classification
    event_type: str = Field(..., description="Event type from predefined list")
    summary: str = Field(..., description="Brief summary of the event (1-2 sentences)")

    # Temporal status - critical for filtering planned vs completed moves
    temporal_status: str = Field(
        default="completed",
        description="Whether this event is 'planned' (future/seeking/will do), 'in_progress' (currently happening), or 'completed' (already done/past tense)"
    )

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

    @field_validator('temporal_status')
    @classmethod
    def validate_temporal_status(cls, v):
        """Validate temporal status."""
        valid_statuses = ['planned', 'in_progress', 'completed']
        if v not in valid_statuses:
            # Default to 'completed' if unclear
            return 'completed'
        return v

    @field_validator('entity_name_canonical')
    @classmethod
    def canonicalize_name(cls, v):
        """Ensure canonical name is uppercase and normalized."""
        if not v:
            return v

        # Uppercase
        canonical = v.upper().strip()

        # Remove common suffixes (works for all entity types)
        suffixes = [
            # Company suffixes
            ' INC', ' INC.', ' INCORPORATED',
            ' LLC', ' LLC.', ' L.L.C', ' L.L.C.',
            ' LTD', ' LTD.', ' LIMITED',
            ' CORP', ' CORP.', ' CORPORATION',
            ' CO', ' CO.', ' COMPANY',
            ' LP', ' L.P.', ' LLP', ' L.L.P.',
            ' PLC', ' GMBH',

            # Government suffixes
            ' AGENCY', ' ADMINISTRATION', ' DEPARTMENT', ' DEPT', ' DEPT.',
            ' BUREAU', ' COMMISSION', ' AUTHORITY', ' BOARD', ' OFFICE', ' SERVICE',

            # Nonprofit suffixes
            ' FOUNDATION', ' TRUST', ' SOCIETY', ' ASSOCIATION', ' INSTITUTE'
        ]

        for suffix in suffixes:
            if canonical.endswith(suffix):
                canonical = canonical[:-len(suffix)].strip()

        # Remove common prefixes
        prefixes = ['THE ', 'U.S. ', 'UNITED STATES ']
        for prefix in prefixes:
            if canonical.startswith(prefix):
                canonical = canonical[len(prefix):].strip()

        # Normalize common patterns
        canonical = canonical.replace(' AND ', ' & ')
        canonical = canonical.replace(',', ' ')
        canonical = ' '.join(canonical.split())  # Normalize whitespace

        return canonical


class RelevanceCheck(BaseModel):
    """Lightweight relevance check for two-stage extraction (Stage 1)."""
    is_relevant: bool = Field(..., description="True if document relates to the business objective")
    relevance_reasoning: str = Field(..., description="Why this document is/isn't relevant to the business objective")


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
    """Universal enrichment result - works for any entity type."""

    # Core field (works for everyone)
    domain: Optional[str] = Field(None, description="Primary domain (.com, .gov, .org, etc.)")

    # Flexible metadata - LLM extracts what it finds
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Flexible storage for entity information. Examples:
        - Common: website_url, hq_city, hq_state, address, phone
        - Companies: linkedin_url, industry, employee_count, founded_year
        - Government: agency_code, jurisdiction (federal/state/local), parent_agency, gov_domain
        - Contractors: sam_gov_uei, duns_number, cage_code, naics_codes
        - Nonprofits: ein, tax_status
        Extract whatever is available in search results."""
    )

    enrichment_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in enrichment")
    reasoning: Optional[str] = Field(None, description="Why these values were chosen")


# Helper function to get normalized name (no punctuation/spaces)
def get_normalized_name(canonical_name: str) -> str:
    """Convert canonical name to normalized form (no punct, no spaces)."""
    import re
    # Remove all non-alphanumeric characters
    normalized = re.sub(r'[^A-Z0-9]', '', canonical_name.upper())
    return normalized


# ============================================================================
# Building Demolition Schemas
# ============================================================================

class BuildingInfo(BaseModel):
    """Extracted building demolition information from any source (permits, news, reports)."""

    # Core fields
    address: str = Field(..., description="Full street address of the building")
    building_name: Optional[str] = Field(None, description="Name of the building if mentioned")

    # Location details
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/province")
    zip_code: Optional[str] = Field(None, description="ZIP/postal code")

    # Demolition details
    demolition_date: Optional[str] = Field(None, description="Date of demolition (ISO format or natural language)")
    demolition_reason: Optional[str] = Field(None, description="Reason for demolition")
    estimated_date: Optional[str] = Field(None, description="Estimated demolition timeframe if exact date unknown")

    # Administrative details
    permit_id: Optional[str] = Field(None, description="Permit or reference ID")
    source_url: Optional[str] = Field(None, description="URL to source document/notice")

    # Building characteristics
    is_commercial: Optional[bool] = Field(None, description="True if commercial building (offices, not residential)")
    building_use: Optional[str] = Field(None, description="Type of building use")

    # Extraction quality
    is_demolition_related: bool = Field(..., description="True if document is about building demolition/destruction")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction (0.0-1.0)")


class CompanyAtBuilding(BaseModel):
    """Company found at a building address via web search."""

    company_name: str = Field(..., description="Company name")
    suite_or_floor: Optional[str] = Field(None, description="Suite number, floor, or unit designation")

    # Contact info if found
    website: Optional[str] = Field(None, description="Company website URL")
    domain: Optional[str] = Field(None, description="Company domain (e.g., 'acme.com')")
    phone: Optional[str] = Field(None, description="Phone number")

    # Extraction quality
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence this company is at the address")
    evidence_quote: Optional[str] = Field(None, description="Quote from search result confirming presence at address")


class BuildingExtractionResult(BaseModel):
    """Result of extracting building info from a document."""

    building_info: Optional[BuildingInfo] = Field(None, description="Building information if demolition-related")
    reasoning: str = Field(..., description="Explanation of extraction decision")
