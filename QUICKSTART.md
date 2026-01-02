# Quick Start Guide

## Current Status
✅ System is fully functional
✅ Database initialized
✅ Tested with 3 mock documents
✅ All code committed to git

## Step 1: Add Your Own Documents

### Supported Formats
- HTML files (web scrapes, articles)
- JSON files (API responses, structured data)
- TXT files (reports, emails, documents)

### How to Add Files

```bash
# Simply copy your files to the bucket
cp your_document.html raw_data_bucket/
cp your_data.json raw_data_bucket/
cp your_report.txt raw_data_bucket/
```

### What the System Extracts
The LLM looks for:
- Company/organization names
- Event types (funding, partnerships, hiring, etc.)
- Key facts (amounts, dates, people, locations)
- Dynamic signals (anything valuable that doesn't fit strict schema)

---

## Step 2: Configure LLM Provider (Optional)

### Current Setup: Mock Mode
The system runs with fake LLM responses - great for testing!

### To Use Real LLM (Better Extraction)

Edit `.env`:

```bash
# Option A: Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Option B: Use Anthropic (Claude)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Cost Estimate
- ~$0.01-0.05 per document (depending on size)
- Recommended: Start with OpenAI GPT-4o or Claude Sonnet

---

## Step 3: Configure Search Provider (Optional)

### Current Setup: Mock Search
Returns fake search results for enrichment.

### To Use Real Search (Better Entity Resolution)

Edit `.env`:

```bash
# Option A: Tavily (Recommended - best for company search)
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-your-key-here

# Option B: Exa
SEARCH_PROVIDER=exa
EXA_API_KEY=your-key-here
```

### Cost Estimate
- Tavily: ~$0.005 per search (enrichment runs once per entity)
- Only enriches when needed (no domain or >30 days old)

---

## Step 4: Run the Pipeline

```bash
# Process all files in raw_data_bucket/
python main.py run
```

### What Happens:
1. ✓ Scans raw_data_bucket/ for files
2. ✓ Deduplicates (skips already-processed files by hash)
3. ✓ Extracts structured events with LLM
4. ✓ Enriches entities with web search (if needed)
5. ✓ Resolves to deduplicated entities
6. ✓ Scores leads with time decay
7. ✓ Prints detailed summary

### Output Example:
```
ACME CLOUD
  Domain: acmecloud.io
  Events: 3
  Lead Score: 137
  Status: ACTIVE
  Top Signals:
    • funding_round: +20
    • hiring_surge: +15
    • partnership: +10
```

---

## Step 5: Query Your Data

### Option A: Direct SQL

```bash
# Connect to database
psql -U leadgen_user -d leadgen_db -h localhost

# View all leads
SELECT
  e.canonical_name,
  e.domain,
  l.score,
  l.status
FROM entities e
JOIN leads_current l ON l.entity_id = e.id
ORDER BY l.score DESC;

# View events for a specific entity
SELECT event_type, strict->>'summary' as summary
FROM events
WHERE entity_id = 1;
```

### Option B: Python Script

Create `query_leads.py`:

```python
from src.db.session import get_db
from src.db.models import Entity, LeadCurrent

with get_db() as db:
    # Get top leads
    leads = db.query(LeadCurrent).join(Entity)\
        .filter(LeadCurrent.score >= 50)\
        .order_by(LeadCurrent.score.desc())\
        .all()

    for lead in leads:
        print(f"{lead.entity.canonical_name}: {lead.score}")
```

---

## Customization

### Change Event Scoring Rules

Edit `src/config.py`:

```python
# In LeadScorer class (src/scoring/scorer.py)
self.event_scores = {
    "funding_round": 25,      # Increase funding importance
    "partnership": 15,         # Increase partnership value
    "layoffs": -20,            # More penalty for layoffs
    # ... customize for your domain
}
```

### Change Time Decay

Edit `.env`:

```bash
SCORING_TIME_DECAY_DAYS=60  # Faster decay (default: 90)
```

### Add Custom Event Types

Edit `src/config.py`:

```python
EVENT_TYPES = [
    "funding_round",
    "partnership",
    "your_custom_event",  # Add here
    # ...
]
```

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Restart if needed
sudo service postgresql restart
```

### Reset Database
```bash
# WARNING: Deletes all data
python main.py reset
```

### View Logs
```bash
# Run with verbose output
python main.py run 2>&1 | tee pipeline.log
```

---

## What's Next?

See PRODUCTION_GUIDE.md for scaling to production.
