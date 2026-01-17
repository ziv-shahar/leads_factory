-- ============================================================================
-- Lead Intelligence Pipeline - Supabase Migration
-- ============================================================================
-- Run this script in Supabase SQL Editor to create all required tables
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Table 1: Raw Events (File Tracking & Deduplication)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_events (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_events_status ON raw_events(status);
CREATE INDEX IF NOT EXISTS idx_raw_events_content_hash ON raw_events(content_hash);

COMMENT ON TABLE raw_events IS 'Tracks ingested files and processing status';
COMMENT ON COLUMN raw_events.content_hash IS 'SHA256 hash for deduplication';
COMMENT ON COLUMN raw_events.status IS 'NEW, PROCESSED, or FAILED';

-- ============================================================================
-- Table 2: Entities (Companies, Governments, Contractors, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(512) NOT NULL,
    normalized_name VARCHAR(512) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    entity_type VARCHAR(50),
    entity_metadata JSONB NOT NULL DEFAULT '{}',
    last_enriched_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);
CREATE INDEX IF NOT EXISTS idx_entities_normalized_name ON entities(normalized_name);
CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain);
CREATE INDEX IF NOT EXISTS idx_entities_entity_type ON entities(entity_type);

COMMENT ON TABLE entities IS 'Deduplicated entities (companies, governments, contractors, etc.)';
COMMENT ON COLUMN entities.canonical_name IS 'Normalized uppercase name (e.g., ACME CLOUD)';
COMMENT ON COLUMN entities.normalized_name IS 'Alphanumeric only (e.g., ACMECLOUD)';
COMMENT ON COLUMN entities.domain IS 'Primary domain (.com, .gov, .org, etc.)';
COMMENT ON COLUMN entities.entity_metadata IS 'Flexible JSONB for entity-specific data';

-- ============================================================================
-- Table 3: Events (Normalized Events from Data Sources)
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_time TIMESTAMP,
    ingest_time TIMESTAMP NOT NULL DEFAULT NOW(),
    strict JSONB NOT NULL DEFAULT '{}',
    dynamic_signals JSONB NOT NULL DEFAULT '[]',
    extraction_confidence FLOAT NOT NULL DEFAULT 0.0,
    raw_ref VARCHAR(1024) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_entity_id ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_event_time ON events(event_time);

COMMENT ON TABLE events IS 'Normalized events (funding, hiring, demolitions, acquisitions, etc.)';
COMMENT ON COLUMN events.strict IS 'Structured event data (summary, key_facts, etc.)';
COMMENT ON COLUMN events.dynamic_signals IS 'Catch-all signals array';
COMMENT ON COLUMN events.raw_ref IS 'Reference to source file/document';

-- ============================================================================
-- Table 4: Leads Current (Materialized Lead State)
-- ============================================================================
CREATE TABLE IF NOT EXISTS leads_current (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL UNIQUE REFERENCES entities(id) ON DELETE CASCADE,
    score INTEGER NOT NULL DEFAULT 0,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    reasons JSONB NOT NULL DEFAULT '{}',
    last_updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_current_score ON leads_current(score);
CREATE INDEX IF NOT EXISTS idx_leads_current_status ON leads_current(status);

COMMENT ON TABLE leads_current IS 'Current state of leads for UI/API queries';
COMMENT ON COLUMN leads_current.score IS 'Lead score (0-100+)';
COMMENT ON COLUMN leads_current.status IS 'NEW, ACTIVE, STALE, or DISMISSED';
COMMENT ON COLUMN leads_current.reasons IS 'Evidence and reasoning breakdown';

-- ============================================================================
-- Table 5: Lead State History (Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS lead_state_history (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    confidence_score FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,
    reasons JSONB NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_history_entity_id ON lead_state_history(entity_id);
CREATE INDEX IF NOT EXISTS idx_lead_history_changed_at ON lead_state_history(changed_at);

COMMENT ON TABLE lead_state_history IS 'Append-only audit trail of lead changes';

-- ============================================================================
-- Enable Row Level Security (RLS)
-- ============================================================================
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads_current ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_state_history ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Enable all for service role" ON raw_events;
DROP POLICY IF EXISTS "Enable all for service role" ON entities;
DROP POLICY IF EXISTS "Enable all for service role" ON events;
DROP POLICY IF EXISTS "Enable all for service role" ON leads_current;
DROP POLICY IF EXISTS "Enable all for service role" ON lead_state_history;

-- Create policies (allow all for authenticated users - adjust based on your needs)
CREATE POLICY "Enable all for authenticated users" ON raw_events
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON entities
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON events
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON leads_current
    FOR ALL USING (true);

CREATE POLICY "Enable all for authenticated users" ON lead_state_history
    FOR ALL USING (true);

-- ============================================================================
-- Helpful Views for Querying
-- ============================================================================

-- Drop view if exists
DROP VIEW IF EXISTS active_leads_view;

-- View: Active Leads with Entity Details
CREATE VIEW active_leads_view AS
SELECT
    lc.id as lead_id,
    e.id as entity_id,
    e.canonical_name,
    e.domain,
    e.entity_type,
    e.entity_metadata,
    lc.score,
    lc.confidence_score,
    lc.status,
    lc.reasons,
    lc.last_updated_at,
    COUNT(ev.id) as event_count
FROM leads_current lc
JOIN entities e ON lc.entity_id = e.id
LEFT JOIN events ev ON e.id = ev.entity_id
WHERE lc.status IN ('NEW', 'ACTIVE')
GROUP BY lc.id, e.id, e.canonical_name, e.domain, e.entity_type,
         e.entity_metadata, lc.score, lc.confidence_score, lc.status,
         lc.reasons, lc.last_updated_at
ORDER BY lc.score DESC;

COMMENT ON VIEW active_leads_view IS 'Active leads with entity details and event counts';

-- ============================================================================
-- Success Message
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration complete! All 5 tables created successfully.';
    RAISE NOTICE '📊 Tables: raw_events, entities, events, leads_current, lead_state_history';
    RAISE NOTICE '👀 View: active_leads_view';
END $$;
