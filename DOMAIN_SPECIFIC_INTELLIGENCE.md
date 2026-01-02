# Domain-Specific Intelligence & Multi-Company Events

## Overview

The pipeline now supports:
1. **Domain-Specific Relevance**: Filter documents based on your business objective
2. **Multi-Company Extraction**: Extract multiple events from documents that mention several companies

---

## 🎯 Domain-Specific Relevance

### **What Changed**

Previously: Documents were marked relevant if they mentioned "any company event"

Now: Documents are relevant ONLY if they relate to your **specific business objective**

### **Default Objective: Office Space Prediction**

**Business Goal**: Predict which companies will need to expand, relocate, or change office space

**Relevant Signals**:
- ✅ Hiring surge → need more space
- ✅ Funding rounds → likely to hire and expand
- ✅ Layoffs → may downsize
- ✅ Office expansion announcements
- ✅ Acquisitions → consolidation/expansion needs
- ✅ Remote work policy changes → office space reduction

**Not Relevant**:
- ❌ Product launches (unless paired with hiring)
- ❌ Marketing campaigns
- ❌ Awards (unless indicating growth)
- ❌ Technology adoptions (unless infrastructure-related)

### **How It Works**

1. **Configuration** (`.env`):
```bash
BUSINESS_OBJECTIVE="Predict which companies will need to expand, relocate, or change office space based on growth signals (hiring, funding, acquisitions, layoffs, expansions)"
```

2. **LLM Evaluation**: The LLM assesses each document against this objective

3. **Filtering**: Only documents with relevant signals are processed

### **Example: Office Space Prediction**

**Document 1** (News Article):
```
"TechCo launches new AI-powered email marketing tool"
```

**LLM Assessment**:
```json
{
  "is_relevant": false,
  "relevance_reasoning": "Product launch with no hiring or expansion signals - not relevant to office space prediction"
}
```
→ **REJECTED**

---

**Document 2** (Press Release):
```
"TechCo raises $50M Series B, plans to triple headcount"
```

**LLM Assessment**:
```json
{
  "is_relevant": true,
  "relevance_reasoning": "Funding round paired with hiring surge indicates strong office space expansion needs"
}
```
→ **PROCESSED**

---

## 🏢 Multi-Company Event Extraction

### **The Problem**

Many documents mention multiple companies:
- "Company A acquires Company B for $100M"
- "Company X partners with Company Y and Company Z"
- "Startup A, B, and C all raise funding"

Previously: Only one event created (ambiguous which company)

Now: Separate events created for EACH company

### **How It Works**

**Input Document**:
```
Acme Cloud acquires BetaCorp for $50M to expand into enterprise market.
Acme will integrate BetaCorp's 200 employees into their SF office.
```

**LLM Extraction**:
```json
{
  "is_relevant": true,
  "relevance_reasoning": "Acquisition involving office integration - signals space needs",
  "events": [
    {
      "company_name_raw": "Acme Cloud",
      "company_name_canonical": "ACME CLOUD",
      "event_type": "acquisition",
      "summary": "Acme Cloud acquired BetaCorp for $50M to expand enterprise market",
      "key_facts": {
        "amount": "$50M",
        "companies": ["BetaCorp"],
        "people_count": "200 employees"
      },
      "extraction_confidence": 0.9,
      "dynamic_signals": [
        {
          "signal_type": "office_integration",
          "description": "Integrating 200 employees into SF office",
          "evidence_quote": "integrate BetaCorp's 200 employees into their SF office"
        }
      ]
    },
    {
      "company_name_raw": "BetaCorp",
      "company_name_canonical": "BETACORP",
      "event_type": "acquisition",
      "summary": "BetaCorp acquired by Acme Cloud for $50M",
      "key_facts": {
        "amount": "$50M",
        "companies": ["Acme Cloud"],
        "people_count": "200 employees"
      },
      "extraction_confidence": 0.9,
      "dynamic_signals": [
        {
          "signal_type": "office_relocation",
          "description": "Employees moving to Acme SF office",
          "evidence_quote": "integrate BetaCorp's 200 employees into their SF office"
        }
      ]
    }
  ]
}
```

**Pipeline Processing**:
1. Document passes relevance check ✅
2. Two events extracted
3. Creates separate entity records:
   - Entity: ACME CLOUD → Event: acquisition (acquirer perspective)
   - Entity: BETACORP → Event: acquisition (acquired perspective)
4. Both get scored and materialized as leads

### **Pipeline Output**:
```
✓ Document relevant: Acquisition involving office integration
✓ Extracted 2 event(s) from 2 company(ies)

  Event 1/2:
  → Company: Acme Cloud -> ACME CLOUD
  → Type: acquisition
  → Confidence: 0.90
  ✓ Event processed for ACME CLOUD

  Event 2/2:
  → Company: BetaCorp -> BETACORP
  → Type: acquisition
  → Confidence: 0.90
  ✓ Event processed for BETACORP

✓ File processing complete: 2/2 events processed
```

---

## 🔧 Configuration

### **Customize Your Business Objective**

Edit `.env` to change what's considered relevant:

**Example: SaaS Lead Generation**
```bash
BUSINESS_OBJECTIVE="Identify fast-growing SaaS companies that may need sales tools based on funding, hiring, and customer growth signals"
```

**Example: Real Estate Intelligence**
```bash
BUSINESS_OBJECTIVE="Find companies expanding into new markets or opening new offices to identify commercial real estate opportunities"
```

**Example: Recruiting**
```bash
BUSINESS_OBJECTIVE="Identify companies with hiring surges, funding rounds, or expansions to source engineering talent"
```

### **Relevance Signals**

The LLM automatically interprets your objective and looks for relevant signals.

For "office space prediction", it knows to look for:
- Hiring/layoffs
- Funding (→ growth)
- Acquisitions
- Office announcements
- Remote work changes
- Headcount metrics

For "SaaS lead generation", it would look for:
- Sales team growth
- Enterprise customer wins
- Funding for go-to-market
- International expansion

---

## 📊 Understanding the Results

### **Database Changes**

**Before** (one document → one event):
```
Document: "Acme acquires Beta"
├── Entity: ACME CLOUD
└── Event: acquisition
```

**After** (one document → multiple events):
```
Document: "Acme acquires Beta"
├── Entity: ACME CLOUD
│   └── Event: acquisition (acquirer perspective)
└── Entity: BETA
    └── Event: acquisition (acquired perspective)
```

### **Query Multi-Company Events**

```sql
-- Find documents that created multiple events
SELECT file_path, COUNT(DISTINCT entity_id) as company_count
FROM events
GROUP BY file_path
HAVING COUNT(DISTINCT entity_id) > 1;

-- See all companies mentioned in a document
SELECT e.file_path, ent.canonical_name, ev.event_type
FROM raw_events e
JOIN events ev ON ev.raw_ref = e.file_path
JOIN entities ent ON ent.id = ev.entity_id
WHERE e.file_path = '/path/to/doc.html';
```

---

## 🎯 Best Practices

### **1. Define Clear Objectives**

Good objectives are:
- ✅ Specific: "predict office space needs" not "find companies"
- ✅ Actionable: Tied to business decisions
- ✅ Signal-based: Clear indicators the LLM can identify

Poor objectives:
- ❌ "Find interesting companies" (too vague)
- ❌ "Get all company news" (not filtered)
- ❌ "Companies I like" (subjective)

### **2. Review Rejected Documents**

Check if legitimate documents are being filtered:

```bash
psql -U leadgen_user -d leadgen_db

# See rejection reasons
SELECT error, COUNT(*) as count
FROM raw_events
WHERE status = 'FAILED'
AND error LIKE '%not relevant%'
GROUP BY error
LIMIT 10;
```

If seeing false negatives, refine your `BUSINESS_OBJECTIVE`.

### **3. Monitor Multi-Company Extraction**

```sql
-- Count events per document
SELECT
  r.file_path,
  COUNT(e.id) as event_count,
  COUNT(DISTINCT e.entity_id) as unique_companies
FROM raw_events r
JOIN events e ON e.raw_ref = r.file_path
GROUP BY r.file_path
HAVING COUNT(e.id) > 1
ORDER BY event_count DESC;
```

### **4. Validate Cross-References**

For acquisitions/partnerships, check that companies reference each other:

```sql
-- Find acquisition events
SELECT
  ent.canonical_name,
  ev.strict->>'summary' as summary,
  ev.strict->'key_facts'->>'companies' as related_companies
FROM events ev
JOIN entities ent ON ent.id = ev.entity_id
WHERE ev.event_type = 'acquisition';
```

---

## 🧪 Testing Examples

### **Test 1: Single Company, Relevant**

`raw_data_bucket/test_single_relevant.txt`:
```
TechStartup raises $10M Series A and plans to hire 50 engineers.
The company will open a new office in Austin, Texas.
```

**Expected**:
- ✅ is_relevant=true (hiring + office expansion)
- ✅ 1 event extracted (TechStartup)
- ✅ Processed successfully

---

### **Test 2: Multiple Companies**

`raw_data_bucket/test_multi_company.txt`:
```
CloudCo announced a strategic partnership with DataInc today.
CloudCo will integrate DataInc's API and co-locate teams in Seattle.
```

**Expected**:
- ✅ is_relevant=true (partnership with co-location)
- ✅ 2 events extracted (CloudCo + DataInc)
- ✅ Both processed as separate entities

---

### **Test 3: Not Relevant**

`raw_data_bucket/test_not_relevant.txt`:
```
SoftwareCo releases version 2.0 of their mobile app with new dark mode.
```

**Expected**:
- ❌ is_relevant=false (product launch, no growth signals)
- ⊘ Rejected: "Product launch without hiring or expansion signals"

---

## 📈 Advanced: Custom Event Types for Your Domain

You can add domain-specific event types:

Edit `src/config.py`:

```python
EVENT_TYPES = [
    # Generic
    "funding_round",
    "hiring_surge",
    "layoffs",
    "acquisition",

    # Office-space specific
    "lease_renewal",
    "office_consolidation",
    "remote_first_transition",
    "co_working_adoption",

    # Your domain
    "other"
]
```

Then update prompts to include these types.

---

## Summary

**Key Changes**:
1. **Domain-Specific Relevance**: Only process documents relevant to your business objective
2. **Multi-Company Extraction**: One document can create events for multiple companies
3. **Configurable Objectives**: Customize via `BUSINESS_OBJECTIVE` in `.env`
4. **Better Signal Detection**: LLM interprets objective and finds relevant signals

**Benefits**:
- 🎯 Higher quality leads (filtered by relevance)
- 📊 More complete data (capture all mentioned companies)
- ⚙️ Customizable for any domain
- 🔍 Better explainability (relevance reasoning provided)

**Use Cases**:
- Office space prediction (default)
- SaaS lead generation
- Real estate intelligence
- Recruiting/talent sourcing
- M&A intelligence
- Market research
