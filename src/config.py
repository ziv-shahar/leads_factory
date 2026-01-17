"""Configuration management for lead intelligence pipeline."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_BUCKET = PROJECT_ROOT / "raw_data_bucket/"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://leadgen_user:leadgen_pass@localhost:5432/leadgen_db")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, mock
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Two-Stage Extraction Configuration
# Enable two-stage extraction: cheap model filters irrelevant docs, expensive model extracts relevant ones
TWO_STAGE_EXTRACTION = os.getenv("TWO_STAGE_EXTRACTION", "false").lower() == "true"

# Stage 1: Relevance Filter (cheap model)
LLM_FILTER_PROVIDER = os.getenv("LLM_FILTER_PROVIDER", "openai")  # openai, anthropic, mock
LLM_FILTER_MODEL = os.getenv("LLM_FILTER_MODEL", "gpt-3.5-turbo")  # Cheap model for filtering

# Stage 2: Detailed Extraction (expensive model)
LLM_EXTRACTION_PROVIDER = os.getenv("LLM_EXTRACTION_PROVIDER", "openai")  # openai, anthropic, mock
LLM_EXTRACTION_MODEL = os.getenv("LLM_EXTRACTION_MODEL", "gpt-4o")  # Expensive model for extraction

# Search Configuration
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "tavily")  # tavily, exa, serpapi, mock
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Enrichment settings
ENRICHMENT_ENABLED = os.getenv("ENRICHMENT_ENABLED", "true").lower() == "true"
ENRICHMENT_FRESHNESS_DAYS = int(os.getenv("ENRICHMENT_FRESHNESS_DAYS", "30"))

# Building Processing Configuration
BUILDING_PROCESSING_ENABLED = os.getenv("BUILDING_PROCESSING_ENABLED", "true").lower() == "true"
BUILDING_COMPANY_SEARCH_MAX_RESULTS = int(os.getenv("BUILDING_COMPANY_SEARCH_MAX_RESULTS", "15"))
BUILDING_EVENT_TYPE = os.getenv("BUILDING_EVENT_TYPE", "contraction")  # Event type for companies needing relocation

# Model configuration helper (for building processor and other modules)
LLM_MODEL_EXPENSIVE = os.getenv("LLM_MODEL_EXPENSIVE", LLM_EXTRACTION_MODEL)

# Business Objective (defines relevance criteria)
BUSINESS_OBJECTIVE = os.getenv(
    "BUSINESS_OBJECTIVE",
    "Predict which companies will need to expand, relocate, or change office space based on growth signals (hiring, funding, acquisitions, layoffs, expansions)"
)

# Scoring settings
SCORING_TIME_DECAY_DAYS = int(os.getenv("SCORING_TIME_DECAY_DAYS", "90"))

# Parallel Processing Configuration
PARALLEL_PROCESSING = os.getenv("PARALLEL_PROCESSING", "true").lower() == "true"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))  # Number of parallel workers (4-8 recommended)
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))  # API rate limit

# Event types (universal - work for all entity types)
EVENT_TYPES = [
    # Generic events (work for companies, governments, contractors, etc.)
    "expansion",  # Growing, opening new locations, leasing space
    "contraction",  # Downsizing, closing locations, reducing space
    "funding",  # Raising money, receiving grants, budget allocation (formerly funding_round)
    "hiring_surge",  # Significant hiring or workforce changes
    "layoffs",  # Workforce reductions
    "contract_awarded",  # Contracts, bids, procurement
    "permit_issued",  # Building permits, regulatory approvals
    "partnership",  # Collaborations, agreements
    "acquisition",  # Mergers, acquisitions
    "product_launch",  # New products, services, initiatives
    "leadership_change",  # Executive changes
    "compliance_issue",  # Regulatory or legal issues
    "award_recognition",  # Awards, certifications, recognition
    "technology_adoption",  # Technology or infrastructure changes
    "market_entry",  # Entering new markets or regions

    # Legacy events (keep for backward compatibility)
    "funding_round",  # Alias for "funding"

    "other"  # Catch-all
]

# Lead statuses
LEAD_STATUSES = ["NEW", "ACTIVE", "STALE", "DISMISSED"]

# Raw event statuses
RAW_EVENT_STATUSES = ["NEW", "PROCESSED", "FAILED"]
