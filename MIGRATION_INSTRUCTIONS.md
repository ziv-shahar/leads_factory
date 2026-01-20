# Location Leads Table Migration Instructions

## Overview
This migration adds the `location_leads` table to enable per-state lead tracking for entities operating in multiple locations.

## Prerequisites
- Access to Supabase project dashboard
- SQL Editor permissions

## Migration Steps

### 1. Access Supabase SQL Editor
1. Go to your Supabase project dashboard: https://app.supabase.com
2. Navigate to **SQL Editor** in the left sidebar
3. Click **New Query**

### 2. Run Migration Script
1. Open the file: `add_location_leads_table.sql`
2. Copy the entire contents of the file
3. Paste into the Supabase SQL Editor
4. Click **Run** (or press `Ctrl+Enter`)

### 3. Verify Migration Success
You should see a success message:
```
✅ Location leads table migration complete!
📊 Table: location_leads
👀 View: location_leads_view
🔑 Unique constraint on (entity_id, state)
📍 Now tracking entity activities per state!
```

### 4. Verify Table Creation
Run this query to verify the table exists:
```sql
SELECT * FROM location_leads LIMIT 1;
```

### 5. Test Location Leads View
Run this query to verify the view works:
```sql
SELECT * FROM location_leads_view LIMIT 10;
```

## What This Migration Does

### Creates Table: `location_leads`
- Tracks entity activities per state
- Unique constraint on `(entity_id, state)` - one lead per entity+state combination
- Stores normalized 2-letter state codes (e.g., "FL", "CA", "TX")
- Includes scoring, confidence, and metadata per location

### Creates View: `location_leads_view`
- Joins location leads with entity details
- Filters for active leads only (NEW, ACTIVE status)
- Ordered by score and recent activity

### Enables Row Level Security (RLS)
- RLS enabled for security
- Policy allows all operations for authenticated users
- Adjust policies based on your security requirements

## Schema Details

```sql
location_leads (
    id                  SERIAL PRIMARY KEY,
    entity_id           INTEGER REFERENCES entities(id),
    state               VARCHAR(2) NOT NULL,      -- "FL", "CA", etc.
    city                VARCHAR(255),             -- Optional
    score               INTEGER DEFAULT 0,
    confidence_score    FLOAT DEFAULT 0.0,
    status              VARCHAR(50) DEFAULT 'NEW',
    event_count         INTEGER DEFAULT 0,
    reasons             JSONB DEFAULT '{}',
    last_event_date     TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW(),
    last_updated_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (entity_id, state)
)
```

## Rollback (if needed)

If you need to rollback this migration:
```sql
DROP VIEW IF EXISTS location_leads_view;
DROP TABLE IF EXISTS location_leads;
```

## Next Steps

After running the migration:
1. Test the pipeline with all three data sources (permits, government opportunities, finance news)
2. Verify LocationLead records are being created correctly
3. Check that location normalization is working (all states are 2-letter codes)
4. Query the `location_leads_view` to see results

## Support

If you encounter issues:
1. Check Supabase logs for errors
2. Verify all previous migrations completed successfully
3. Ensure the `entities` table exists (required foreign key)
