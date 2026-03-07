-- Migration 002: Add Government Opportunity Tracking
-- Date: 2026-03-07
-- Purpose: Add opportunity_id for upsert logic, backup existing data, prepare for clean slate

-- ============================================================================
-- STEP 1: BACKUP ALL EXISTING TABLES
-- ============================================================================

-- Backup entities
DROP TABLE IF EXISTS entities_backup CASCADE;
CREATE TABLE entities_backup AS SELECT * FROM entities;

-- Backup events
DROP TABLE IF EXISTS events_backup CASCADE;
CREATE TABLE events_backup AS SELECT * FROM events;

-- Backup location_leads
DROP TABLE IF EXISTS location_leads_backup CASCADE;
CREATE TABLE location_leads_backup AS SELECT * FROM location_leads;

-- Backup leads_current
DROP TABLE IF EXISTS leads_current_backup CASCADE;
CREATE TABLE leads_current_backup AS SELECT * FROM leads_current;

-- Backup lead_state_history
DROP TABLE IF EXISTS lead_state_history_backup CASCADE;
CREATE TABLE lead_state_history_backup AS SELECT * FROM lead_state_history;

-- Backup raw_events
DROP TABLE IF EXISTS raw_events_backup CASCADE;
CREATE TABLE raw_events_backup AS SELECT * FROM raw_events;

COMMENT ON TABLE entities_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';
COMMENT ON TABLE events_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';
COMMENT ON TABLE location_leads_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';
COMMENT ON TABLE leads_current_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';
COMMENT ON TABLE lead_state_history_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';
COMMENT ON TABLE raw_events_backup IS 'Backup created before opportunity tracking migration (2026-03-07)';

-- ============================================================================
-- STEP 2: ADD OPPORTUNITY_ID TO EVENTS TABLE
-- ============================================================================

-- Add opportunity_id column (nullable, only for government opportunities)
ALTER TABLE events
ADD COLUMN IF NOT EXISTS opportunity_id VARCHAR(255) DEFAULT NULL;

-- Add index for fast lookup
CREATE INDEX IF NOT EXISTS idx_events_opportunity_id ON events(opportunity_id);

-- Add unique constraint when opportunity_id is not null
-- This prevents duplicate events for the same opportunity
-- Using partial unique index (only when opportunity_id is not null)
DROP INDEX IF EXISTS idx_events_opportunity_id_unique;
CREATE UNIQUE INDEX idx_events_opportunity_id_unique ON events(opportunity_id) WHERE opportunity_id IS NOT NULL;

COMMENT ON COLUMN events.opportunity_id IS 'Unique identifier for government opportunities (from SAM.gov). Used for upsert logic to update existing opportunities.';

-- ============================================================================
-- STEP 3: ADD EXPIRED_AT COLUMN FOR SOFT DELETION
-- ============================================================================

-- Add expired_at column for soft-deleting expired opportunities
ALTER TABLE events
ADD COLUMN IF NOT EXISTS expired_at TIMESTAMP DEFAULT NULL;

-- Add index for querying non-expired events
CREATE INDEX IF NOT EXISTS idx_events_expired_at ON events(expired_at) WHERE expired_at IS NULL;

COMMENT ON COLUMN events.expired_at IS 'When this opportunity expired (response_deadline passed). NULL means still active.';

-- ============================================================================
-- STEP 4: CLEAN SLATE - TRUNCATE TABLES (OPTIONAL - UNCOMMENT TO USE)
-- ============================================================================

-- WARNING: This will delete all data from live tables (backups are safe)
-- Uncomment the lines below if you want to start fresh

-- TRUNCATE TABLE lead_state_history CASCADE;
-- TRUNCATE TABLE location_leads CASCADE;
-- TRUNCATE TABLE leads_current CASCADE;
-- TRUNCATE TABLE events CASCADE;
-- TRUNCATE TABLE entities CASCADE;
-- TRUNCATE TABLE raw_events CASCADE;

-- Reset sequences
-- ALTER SEQUENCE entities_id_seq RESTART WITH 1;
-- ALTER SEQUENCE location_leads_id_seq RESTART WITH 1;
-- ALTER SEQUENCE leads_current_id_seq RESTART WITH 1;
-- ALTER SEQUENCE lead_state_history_id_seq RESTART WITH 1;
-- ALTER SEQUENCE raw_events_id_seq RESTART WITH 1;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check backup table counts
SELECT
  'entities_backup' AS table_name, COUNT(*) AS row_count FROM entities_backup
UNION ALL
SELECT 'events_backup', COUNT(*) FROM events_backup
UNION ALL
SELECT 'location_leads_backup', COUNT(*) FROM location_leads_backup
UNION ALL
SELECT 'leads_current_backup', COUNT(*) FROM leads_current_backup
UNION ALL
SELECT 'lead_state_history_backup', COUNT(*) FROM lead_state_history_backup
UNION ALL
SELECT 'raw_events_backup', COUNT(*) FROM raw_events_backup;

-- Verify new columns exist
SELECT
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_name = 'events'
  AND column_name IN ('opportunity_id', 'expired_at')
ORDER BY column_name;

-- Verify indexes exist
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'events'
  AND indexname LIKE '%opportunity%'
ORDER BY indexname;
