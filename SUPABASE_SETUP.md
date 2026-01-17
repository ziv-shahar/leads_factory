# 🚀 Supabase Migration Guide

Complete guide to migrate your Lead Intelligence Pipeline to Supabase.

---

## ✅ What's Already Done

1. **`.env` file created** - Your Supabase connection string is configured
2. **Migration SQL ready** - `supabase_migration.sql` contains all table definitions
3. **Test script ready** - `test_supabase_connection.py` to verify setup

---

## 📋 Step-by-Step Setup

### **Step 1: Run Migration SQL**

1. Go to your **Supabase Dashboard**: https://app.supabase.com
2. Navigate to **SQL Editor** (in left sidebar)
3. Click **New Query**
4. Copy the entire contents of `supabase_migration.sql`
5. Paste into the SQL editor
6. Click **Run** (or press Ctrl/Cmd + Enter)

You should see:
```
✅ Migration complete! All 5 tables created successfully.
📊 Tables: raw_events, entities, events, leads_current, lead_state_history
👀 View: active_leads_view
```

---

### **Step 2: Verify Tables**

Run the test script to verify everything is set up correctly:

```bash
python test_supabase_connection.py
```

**Expected output:**
```
✅ Connected to PostgreSQL: PostgreSQL 15.x...
📊 Found 5 table(s):
✅ raw_events              (7 columns)
✅ entities                (8 columns)
✅ events                  (10 columns)
✅ leads_current           (7 columns)
✅ lead_state_history      (6 columns)

👀 Found 1 view(s):
✅ active_leads_view

✅ All tables present and ready!
🚀 You can now run: python main.py
```

---

### **Step 3: Run Your Pipeline**

Once tables are verified, run your pipeline:

```bash
python main.py
```

This will:
1. Read files from `raw_data_bucket/`
2. Extract events using LLM
3. Process building demolitions (search for companies)
4. Enrich entities with web search
5. Score leads
6. Store everything in Supabase!

---

## 📊 Database Schema Overview

### **5 Core Tables**

1. **`raw_events`** - File tracking & deduplication
   - Prevents reprocessing same files
   - Tracks processing status (NEW → PROCESSED/FAILED)

2. **`entities`** - Deduplicated companies/organizations
   - Canonical names (e.g., "ACME CLOUD")
   - Domains for resolution
   - Flexible JSONB metadata

3. **`events`** - Normalized events
   - Funding, hiring, demolitions, acquisitions
   - Linked to entities
   - Includes confidence scores

4. **`leads_current`** - Current lead state (materialized view)
   - Lead scores
   - Status (NEW, ACTIVE, STALE)
   - Evidence and reasoning

5. **`lead_state_history`** - Audit trail
   - Full history of score changes
   - Explainability

---

## 🔍 Querying Your Data

### **View Active Leads in Supabase**

Go to **Table Editor** and browse:

**High-Priority Leads:**
```sql
SELECT * FROM active_leads_view
WHERE score >= 50
ORDER BY score DESC
LIMIT 20;
```

**Companies from Building Demolitions:**
```sql
SELECT
    e.canonical_name,
    e.domain,
    ev.strict->>'summary' as event_summary,
    ev.strict->'key_facts'->>'current_address' as building_address,
    lc.score
FROM events ev
JOIN entities e ON ev.entity_id = e.id
LEFT JOIN leads_current lc ON e.id = lc.entity_id
WHERE ev.event_type = 'contraction'
  AND ev.dynamic_signals::text LIKE '%office_relocation_urgent%'
ORDER BY lc.score DESC;
```

**Event Timeline:**
```sql
SELECT
    e.canonical_name,
    ev.event_type,
    ev.strict->>'summary' as summary,
    ev.event_time,
    ev.extraction_confidence
FROM events ev
JOIN entities e ON ev.entity_id = e.id
ORDER BY ev.event_time DESC
LIMIT 50;
```

---

## 🛠️ Useful Supabase Features

### **1. Table Editor**
- Browse data visually
- Edit records directly
- Export to CSV

### **2. SQL Editor**
- Run custom queries
- Save favorite queries
- Query history

### **3. Database Settings**
- Connection pooling (already enabled)
- Daily backups
- Database metrics

### **4. API (Optional)**
Auto-generated REST/GraphQL APIs if you want to build a UI:
- `https://[project].supabase.co/rest/v1/leads_current`
- `https://[project].supabase.co/rest/v1/entities`

---

## 🔒 Security Notes

### **Row Level Security (RLS)**
Your tables have RLS enabled with permissive policies for development. For production:

1. Tighten policies based on your auth needs
2. Use service role key for pipeline (already in your connection string)
3. Use anon key for public queries (if building a UI)

### **Connection Strings**
Your `.env` file contains:
- **Database URL** - Full access (keep secret!)
- Use this for your pipeline

If you build a UI later, use:
- **API URL** - For REST/GraphQL
- **Anon Key** - For public access (respects RLS)

---

## 📈 Monitoring & Maintenance

### **Check Pipeline Runs**
```sql
-- Recent file processing
SELECT
    file_path,
    status,
    ingested_at,
    error
FROM raw_events
ORDER BY ingested_at DESC
LIMIT 20;

-- Processing stats
SELECT
    status,
    COUNT(*) as count
FROM raw_events
GROUP BY status;
```

### **Lead Performance**
```sql
-- Score distribution
SELECT
    CASE
        WHEN score >= 80 THEN 'Very High (80+)'
        WHEN score >= 50 THEN 'High (50-79)'
        WHEN score >= 20 THEN 'Medium (20-49)'
        ELSE 'Low (<20)'
    END as score_range,
    COUNT(*) as count
FROM leads_current
GROUP BY score_range
ORDER BY MIN(score) DESC;

-- Top lead sources
SELECT
    ev.event_type,
    COUNT(DISTINCT ev.entity_id) as entities,
    AVG(lc.score) as avg_score
FROM events ev
JOIN leads_current lc ON ev.entity_id = lc.entity_id
WHERE lc.status IN ('NEW', 'ACTIVE')
GROUP BY ev.event_type
ORDER BY avg_score DESC;
```

---

## 🐛 Troubleshooting

### **Connection Failed**
```bash
# Check your .env file
cat .env | grep DATABASE_URL

# Verify Supabase project is active
# Check: https://app.supabase.com/project/[your-project]/settings/database

# Test connection
python test_supabase_connection.py
```

### **Missing Tables**
```bash
# Run migration again
# Copy supabase_migration.sql to Supabase SQL Editor
# Click Run
```

### **Permission Errors**
```sql
-- Check if RLS is blocking
ALTER TABLE [table_name] DISABLE ROW LEVEL SECURITY;
-- Or update policies in Supabase Dashboard → Authentication → Policies
```

---

## 🎯 Next Steps

1. ✅ Run migration SQL in Supabase
2. ✅ Verify with `python test_supabase_connection.py`
3. ✅ Run pipeline with `python main.py`
4. ✅ Query your data in Supabase Table Editor
5. 🚀 **Optional:** Build a dashboard UI using Supabase APIs

---

## 📚 Resources

- **Supabase Docs**: https://supabase.com/docs
- **SQL Editor Guide**: https://supabase.com/docs/guides/database/overview
- **Python Client**: https://supabase.com/docs/reference/python/introduction

---

**Your Supabase setup is ready! Follow steps 1-3 above and you're good to go.** 🎉
