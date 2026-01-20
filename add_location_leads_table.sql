-- ============================================================================
-- Location-Based Leads Migration
-- ============================================================================
-- Run this script in Supabase SQL Editor to add the location_leads table
-- This enables per-state lead tracking for entities operating in multiple locations
-- ============================================================================

-- ============================================================================
-- Table: Location Leads (Per-State Lead Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS location_leads (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

    -- Normalized location (always 2-letter state code)
    state VARCHAR(2) NOT NULL,
    city VARCHAR(255),

    -- Scoring
    score INTEGER NOT NULL DEFAULT 0,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'NEW',

    -- Metadata
    event_count INTEGER NOT NULL DEFAULT 0,
    reasons JSONB NOT NULL DEFAULT '{}',
    last_event_date TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Unique constraint: one lead per entity + state
    CONSTRAINT uq_entity_state UNIQUE (entity_id, state)
);

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_location_leads_state ON location_leads(state);
CREATE INDEX IF NOT EXISTS idx_location_leads_score ON location_leads(score);
CREATE INDEX IF NOT EXISTS idx_location_leads_entity_state ON location_leads(entity_id, state);
CREATE INDEX IF NOT EXISTS idx_location_leads_status ON location_leads(status);
CREATE INDEX IF NOT EXISTS idx_location_leads_last_event_date ON location_leads(last_event_date);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE location_leads IS 'Location-based leads tracking entity activities per state';
COMMENT ON COLUMN location_leads.entity_id IS 'Reference to the entity (company, agency, etc.)';
COMMENT ON COLUMN location_leads.state IS 'Normalized 2-letter state code (e.g., FL, CA, TX)';
COMMENT ON COLUMN location_leads.city IS 'Most significant city for this entity in this state';
COMMENT ON COLUMN location_leads.score IS 'Lead score for this entity in this state (0-100+)';
COMMENT ON COLUMN location_leads.confidence_score IS 'Average confidence across all events in this state';
COMMENT ON COLUMN location_leads.status IS 'NEW, ACTIVE, STALE, or DISMISSED';
COMMENT ON COLUMN location_leads.event_count IS 'Number of events for this entity in this state';
COMMENT ON COLUMN location_leads.reasons IS 'Evidence and reasoning breakdown per event type';
COMMENT ON COLUMN location_leads.last_event_date IS 'Most recent event date for this entity in this state';

-- ============================================================================
-- Row Level Security
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;

-- Create policy (allow all for authenticated users - adjust based on your needs)
CREATE POLICY "Enable all for authenticated users" ON location_leads
    FOR ALL USING (true);

-- ============================================================================
-- Helpful View for Location-Based Leads
-- ============================================================================

-- Drop view if exists
DROP VIEW IF EXISTS location_leads_view;

-- View: Location Leads with Entity Details
CREATE VIEW location_leads_view AS
SELECT
    ll.id as location_lead_id,
    e.id as entity_id,
    e.canonical_name,
    e.domain,
    e.entity_type,
    ll.state,
    ll.city,
    ll.score,
    ll.confidence_score,
    ll.status,
    ll.event_count,
    ll.reasons,
    ll.last_event_date,
    ll.last_updated_at
FROM location_leads ll
JOIN entities e ON ll.entity_id = e.id
WHERE ll.status IN ('NEW', 'ACTIVE')
ORDER BY ll.score DESC, ll.last_event_date DESC;

COMMENT ON VIEW location_leads_view IS 'Active location-based leads with entity details';

-- ============================================================================
-- Success Message
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Location leads table migration complete!';
    RAISE NOTICE '📊 Table: location_leads';
    RAISE NOTICE '👀 View: location_leads_view';
    RAISE NOTICE '🔑 Unique constraint on (entity_id, state)';
    RAISE NOTICE '📍 Now tracking entity activities per state!';
END $$;
