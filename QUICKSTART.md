# 🚀 Quick Start Guide

Your Leads Factory pipeline is now configured for Supabase! Follow these steps to get started.

## ✅ What's Already Done

1. ✅ **Building demolition feature implemented** - Processes building data and finds companies at addresses
2. ✅ **Directory structure organized** - `raw_data_bucket/` with companies/, buildings/, government/
3. ✅ **Supabase configured** - `.env` file has correct connection string
4. ✅ **Migration SQL ready** - `supabase_migration.sql` contains all table definitions

---

## 🏃 Quick Start (3 Steps)

### Step 1: Verify Setup

Run the verification script on your local machine:

```bash
python verify_setup.py
```

This will check:
- ✅ Database connection works
- ✅ All tables exist
- ✅ Configuration is correct
- ✅ Dependencies are installed

**Expected output:** All checks should pass ✅

---

### Step 2: Ensure Tables Exist

If the verification shows missing tables, run the migration in Supabase:

1. Go to https://app.supabase.com
2. Open **SQL Editor**
3. Create new query
4. Copy contents of `supabase_migration.sql`
5. Click **Run**

**Expected output:**
```
✅ Migration complete! All 5 tables created successfully.
```

---

### Step 3: Run the Pipeline

Once verification passes, run the pipeline:

```bash
python main.py
```

This will:
1. 📂 Read files from `raw_data_bucket/`
2. 🏢 Process company news (companies/)
3. 🏗️ Process building demolitions (buildings/) → Find companies at addresses
4. 🏛️ Process government contracts (government/)
5. 🔍 Enrich entities with web search
6. 📊 Score leads
7. 💾 Store everything in Supabase!

---

## 📊 View Your Data

### Option 1: Supabase Dashboard

1. Go to https://app.supabase.com
2. Navigate to **Table Editor**
3. Browse tables:
   - `leads_current` - Scored leads
   - `entities` - Companies/organizations
   - `events` - All events (funding, hiring, demolitions, etc.)
   - `active_leads_view` - High-priority leads

### Option 2: SQL Queries

Go to **SQL Editor** and run:

**High-priority leads:**
```sql
SELECT
    canonical_name,
    domain,
    score,
    status,
    reasons
FROM active_leads_view
WHERE score >= 50
ORDER BY score DESC
LIMIT 20;
```

**Companies from building demolitions:**
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

**Recent events timeline:**
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

## 📁 Directory Structure

```
raw_data_bucket/
├── companies/          # Company news, funding, hiring
│   ├── file1.json
│   └── file2.txt
├── buildings/          # Building demolitions (NEW!)
│   ├── miami_dade_demolition_permit.json
│   └── downtown_office_demolition.txt
└── government/         # Government contracts, bids
    └── contract_awards.json
```

**Pro tip:** You can create subdirectories and use `merge.txt` files to combine multiple sources!

---

## 🔧 Configuration (.env)

### Database (Required)
```bash
DATABASE_URL=postgresql://postgres.qmnsqztyduzvfimnkhtu:Wk2sQvM2fFjPlgLM@aws-1-us-west-1.pooler.supabase.com:5432/postgres
```

### LLM Provider (Choose one)
```bash
# Option 1: Mock (no API key needed - for testing)
LLM_PROVIDER=mock

# Option 2: OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Option 3: Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Search Provider (Choose one)
```bash
# Option 1: Mock (no API key needed - for testing)
SEARCH_PROVIDER=mock

# Option 2: Tavily
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-...

# Option 3: Exa
SEARCH_PROVIDER=exa
EXA_API_KEY=...
```

### Building Processing (NEW!)
```bash
BUILDING_PROCESSING_ENABLED=true
BUILDING_COMPANY_SEARCH_MAX_RESULTS=15
BUILDING_EVENT_TYPE=contraction  # Event type for companies in demolished buildings
```

---

## 🏗️ How Building Processing Works

1. **File Detection**: Pipeline detects files in `buildings/` directory
2. **Extract Building Info**: LLM extracts address, demolition date, reason
3. **Search for Companies**: Web search finds companies at that address
4. **Extract Company List**: LLM parses search results to find company names
5. **Create Events**: Creates `contraction` event for each company
6. **Enrichment**: Companies get enriched like any other lead
7. **Scoring**: Scored based on office relocation urgency

**Example flow:**
```
buildings/demolition_permit.json
  ↓ (Extract building info)
"123 Main St, Miami, FL - Demolition scheduled 2024-03-15"
  ↓ (Search companies)
Google: "companies at 123 Main St Miami FL"
  ↓ (Extract companies)
["ACME Corp (Suite 200)", "TechStart Inc (Floor 3)"]
  ↓ (Create events)
Event: ACME Corp - contraction - office_relocation_urgent
Event: TechStart Inc - contraction - office_relocation_urgent
  ↓ (Enrich & Score)
Lead: ACME Corp - Score: 65 (urgent office space need)
```

---

## 🐛 Troubleshooting

### Connection Failed
```bash
# Check what's loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DATABASE_URL'))"

# Verify tables exist
python test_supabase_connection.py

# Check Supabase project status
# Visit: https://app.supabase.com/project/qmnsqztyduzvfimnkhtu
```

### No Events Created
```bash
# Check if files are being detected
# Pipeline will log: "Found X files to process"

# Check LLM provider is configured
# If using mock, extraction will use dummy data

# Check building processing is enabled
echo $BUILDING_PROCESSING_ENABLED  # Should be "true"
```

### Low Lead Scores
```bash
# Leads need multiple signals to score high
# Add more data sources to raw_data_bucket/

# Check enrichment is enabled
ENRICHMENT_ENABLED=true  # In .env file
```

---

## 📚 Next Steps

1. ✅ Run `python verify_setup.py` to ensure everything works
2. ✅ Run `python main.py` to process your data
3. ✅ View results in Supabase Dashboard
4. 🎯 Add more data files to `raw_data_bucket/`
5. 🎯 Adjust scoring rules in `src/pipeline/lead_scorer.py`
6. 🎯 Build a UI using Supabase REST API (optional)

---

## 🎉 You're Ready!

Your pipeline now supports:
- ✅ Company news & announcements
- ✅ Building demolitions (finds companies at addresses)
- ✅ Government contracts
- ✅ Automatic enrichment
- ✅ Smart lead scoring
- ✅ Supabase cloud database

**Run `python verify_setup.py` now to get started!** 🚀
