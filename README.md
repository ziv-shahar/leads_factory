# Lead Intelligence Pipeline

A professional, generic lead intelligence system that ingests messy sources (HTML/PDF/TXT/JSON), extracts structured events with dynamic insights, resolves them to deduplicated entities, enriches with web data, and materializes lead scores.

## Architecture Overview

```
Raw Documents → Normalization (LLM) → Entity Resolution → Enrichment → Event Storage → Scoring → Lead Materialization
```

### Key Features

- **Hybrid Schema**: Strict fields + dynamic catch-all signals
- **Domain-First Matching**: Reliable entity deduplication using official domains
- **Time Decay Scoring**: Recent events score higher
- **Multi-Source Intelligence**: Aggregates signals from various sources
- **Explainable Scoring**: Every score has detailed reasoning
- **Production-Ready Design**: Local development, easy S3 migration path

## Project Structure

```
leadgen/
├── raw_data_bucket/          # Simulated S3 (local files)
│   ├── doc_01.html
│   ├── doc_02.json
│   └── doc_03.txt
├── src/
│   ├── config.py             # Configuration management
│   ├── io/
│   │   └── raw_reader.py     # File reading (S3-ready interface)
│   ├── llm/
│   │   ├── schemas.py        # Pydantic models (hybrid schema)
│   │   ├── prompts.py        # LLM prompts
│   │   └── normalizer.py     # Document → Event extraction
│   ├── enrich/
│   │   ├── search_client.py  # Search abstraction (Tavily/Exa/Mock)
│   │   └── enricher.py       # Web-based entity enrichment
│   ├── resolve/
│   │   ├── canonicalize.py   # Name normalization
│   │   └── resolver.py       # Entity resolution (domain-first)
│   ├── scoring/
│   │   └── scorer.py         # Lead scoring + materialization
│   ├── db/
│   │   ├── models.py         # SQLAlchemy models
│   │   └── session.py        # Database session management
│   └── pipeline/
│       └── runner.py         # End-to-end orchestrator
├── docker-compose.yml        # Postgres container
├── requirements.txt
├── main.py                   # CLI entry point
├── .env.example
└── README.md
```

## Database Schema

### Tables

1. **raw_events**: Tracks ingested files and processing status
2. **entities**: Deduplicated companies/orgs (canonical names + domains)
3. **events**: Normalized events with strict + dynamic signals
4. **leads_current**: Materialized lead state (score, status, reasons)
5. **lead_state_history**: Append-only audit trail

### Key Design Decisions

- **Domain as Primary Key**: Most reliable global identifier
- **JSONB for Flexibility**: Strict schema + dynamic signals stored as JSON
- **Confidence Tracking**: Every extraction and enrichment has confidence score
- **Full Explainability**: Lead reasons include evidence event IDs + breakdowns

## Setup

### 1. Prerequisites

- Python 3.9+
- Docker & Docker Compose
- (Optional) OpenAI or Anthropic API key
- (Optional) Search API key (Tavily/Exa/SerpAPI)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

For testing without API keys, use:
```
LLM_PROVIDER=mock
SEARCH_PROVIDER=mock
```

### 4. Start Database

```bash
docker-compose up -d
```

### 5. Initialize Database

```bash
python main.py init
```

## Usage

### Run Pipeline

Process all files in `raw_data_bucket/`:

```bash
python main.py run
```

### Reset Database

Drop all tables and reinitialize:

```bash
python main.py reset
```

## How It Works

### Phase 1: Ingestion & Deduplication

- Scan `raw_data_bucket/` for files
- Compute content hash (SHA256)
- Skip already-processed files

### Phase 2: Normalization (LLM)

Extract structured data using hybrid schema:

**Strict Fields**:
- company_name_raw, company_name_canonical
- event_type (from predefined list)
- summary, key_facts, source_url, event_date
- extraction_confidence, missing_fields

**Dynamic Signals** (catch-all):
- signal_type, description, evidence_quote

### Phase 3: Enrichment (Optional)

- Search web for company information
- Extract official_domain, website_url, linkedin_url, hq_location
- Only enriches if:
  - No domain exists, OR
  - Last enriched >30 days ago

### Phase 4: Entity Resolution

**Domain-First Matching**:
1. If domain exists → match by domain
2. Else exact match on canonical_name
3. Else fuzzy match on normalized_name (RapidFuzz)
4. Else create new entity

### Phase 5: Event Storage

- Create Event record with entity_id
- Store strict fields + dynamic_signals (JSONB)
- Keep reference to raw file

### Phase 6: Scoring & Materialization

**Score Calculation**:
- Base score from event_type (funding=+20, layoffs=-10, etc.)
- Dynamic signal bonuses
- Time decay (30-day full score, linear decay over 90 days)
- Multi-source bonus (+5 per additional source)

**Lead Status**:
- ACTIVE: score ≥50
- NEW: score ≥20
- STALE: old events, low activity

**Materialization**:
- Upsert into `leads_current`
- Append to `lead_state_history`
- Store detailed reasons (evidence events + breakdowns)

## Example Output

```
================================================================================
LEAD INTELLIGENCE PIPELINE - STARTING
================================================================================

Phase 1: Discovering raw files...
✓ Found 3 files in /home/user/leads_factory/raw_data_bucket

--------------------------------------------------------------------------------
Processing: /home/user/leads_factory/raw_data_bucket/doc_01.html
--------------------------------------------------------------------------------
✓ Read file (html): 2156 chars
→ Normalizing document with LLM...
✓ Extracted event: funding_round
  Company: Acme Cloud Inc. -> ACME CLOUD
  Confidence: 0.95
  Dynamic signals: 3
→ Checking if enrichment needed...
→ Enriching entity...
  → Searching for: ACME CLOUD official website company
  ✓ Found 5 search results
  ✓ Enrichment complete (confidence: 0.95)
    Domain: acmecloud.io
→ Resolving entity...
  ✓ Creating new entity: ACME CLOUD
    Enriched entity with: domain=acmecloud.io, website=https://www.acmecloud.io
→ Persisting event...
✓ Event persisted: abc123...
→ Scoring lead...
  ✓ Created lead: score=58, status=ACTIVE
✓ File processing complete

[... processing doc_02.json and doc_03.txt ...]

================================================================================
PIPELINE SUMMARY
================================================================================

Counts:
  Entities: 1
  Events: 3
  Leads: 1
  Raw files processed: 3
  Raw files failed: 0

================================Entity Details=================================

ACME CLOUD
  ID: 1
  Normalized: ACMECLOUD
  Domain: acmecloud.io
  Website: https://www.acmecloud.io
  LinkedIn: https://www.linkedin.com/company/acme-cloud
  HQ: San Francisco, California

  Events (3):
    • funding_round: Acme Cloud Inc. raised $50M in Series B funding led by Venture Capital...
      Confidence: 0.95, Signals: 3
    • hiring_surge: ACME CLOUD is rapidly hiring with 47 active job postings, including sig...
      Confidence: 0.90, Signals: 3
    • partnership: acme cloud llc announced strategic partnership with GlobalTech Enterprise...
      Confidence: 0.88, Signals: 5

  Lead Score: 58
  Confidence: 0.91
  Status: ACTIVE
  Reasons breakdown (11):
    • funding_round: +20
    • acquisition_negotiation: +15
    • hiring_surge: +15
    • partnership: +10
    • government_expansion: +10

================================================================================
PIPELINE COMPLETE
================================================================================
```

## Event Types

Generic event types (customizable per domain):

- `funding_round` (+20)
- `partnership` (+10)
- `expansion` (+15)
- `product_launch` (+12)
- `acquisition` (+18)
- `hiring_surge` (+15)
- `layoffs` (-10)
- `leadership_change` (+8)
- `compliance_issue` (-15)
- `award_recognition` (+5)
- `technology_adoption` (+7)
- `market_entry` (+12)
- `other` (+5)

## Production Migration Path

To move to production:

1. **S3 Storage**:
   - Replace `RawFileReader` filesystem calls with boto3 S3 client
   - Update `raw_events.file_path` to store `s3://bucket/key`

2. **Queue System**:
   - Add Redis/RabbitMQ/Kafka between ingestion and workers
   - Convert `runner.py` to worker pool

3. **Monitoring**:
   - Add structured logging (JSON)
   - Implement metrics (Prometheus/DataDog)
   - Add distributed tracing (OpenTelemetry)

4. **API** (optional):
   - FastAPI endpoints for lead queries
   - Webhooks for real-time updates

## Configuration

See `.env.example` for all configuration options:

- **LLM Provider**: `openai`, `anthropic`, `mock`
- **Search Provider**: `tavily`, `exa`, `serpapi`, `mock`
- **Enrichment Freshness**: Days before re-enriching (default: 30)
- **Time Decay**: Days for scoring decay (default: 90)

## License

MIT License - use freely for any purpose.
