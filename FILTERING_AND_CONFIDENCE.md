# Document Filtering & Confidence Scoring Guide

## 🚫 Document Filtering

### **How It Works**

The pipeline now has **two-stage filtering**:

1. **Relevance Check** (is_relevant)
2. **Confidence Threshold** (extraction_confidence)

### **Stage 1: Relevance Check**

The LLM evaluates if the document is about a company/organization.

**Relevant Documents (is_relevant=true):**
- Company news (funding, partnerships, hiring)
- Corporate announcements
- Business events
- Industry reports about specific companies

**Irrelevant Documents (is_relevant=false):**
- Personal blogs (not about company executives)
- Product reviews by consumers
- Generic news without company focus
- Academic papers
- General industry reports

**Example:**
```json
{
  "is_relevant": false,
  "relevance_reasoning": "This is a personal blog post about productivity, not a company event"
}
```

→ Document **rejected**, not processed further

---

### **Stage 2: Confidence Threshold**

After relevance check, the extraction confidence must meet minimum threshold.

**Default:** 0.3 (30%)

**Configurable in:** `src/pipeline/runner.py:119`

```python
MIN_CONFIDENCE = 0.3  # Set higher for stricter filtering
```

**Example:**
- Document is relevant
- But confidence = 0.25 (ambiguous, incomplete data)
→ Document **rejected** (too low confidence)

---

## 📊 Confidence Scoring Explained

### **1. Extraction Confidence (Per Event)**

**Set by:** The LLM during extraction

**Scale:** 0.0 to 1.0

**Meaning:**

| Score | Label | Meaning | When Used |
|-------|-------|---------|-----------|
| **0.9-1.0** | Very High | Clear, complete data | Well-structured documents |
| **0.7-0.9** | High | Most info present | Typical news articles |
| **0.5-0.7** | Medium | Some ambiguity | Partial information |
| **0.3-0.5** | Low | Unclear/missing data | Vague documents |
| **< 0.3** | Very Low | Highly uncertain | Should be rejected |

**What Affects It:**
- ✅ Clear company name
- ✅ Explicit event type
- ✅ Specific details (dates, amounts, people)
- ✅ Multiple confirming facts
- ❌ Ambiguous language
- ❌ Missing key information
- ❌ Contradictions

**Example from OpenAI:**
```
Document: "Acme Cloud Inc. raised $50M in Series B funding from VC Partners on Dec 15, 2025"

extraction_confidence: 0.90
Reasoning: Clear company name, explicit event type (funding_round), specific amount and date
```

---

### **2. Aggregated Confidence (Per Lead)**

**Calculated in:** `src/scoring/scorer.py:129`

**Formula:**
```python
avg_confidence = sum(all_event_confidences) / count(events)
```

**Simple Average** across all events for that entity.

**Example:**
```
Entity: ACME CLOUD
├── Event 1 (funding):    0.90 confidence
├── Event 2 (hiring):     0.90 confidence
└── Event 3 (partnership): 0.90 confidence

Lead Confidence: (0.90 + 0.90 + 0.90) / 3 = 0.90
```

---

## 🎯 How Confidence Affects Scoring

**Confidence does NOT directly affect the lead score.**

It's a **quality indicator**, not a score multiplier.

**Lead Score** is based on:
- Event types (funding +20, partnership +10, etc.)
- Dynamic signals
- Time decay
- Multi-source bonus

**Confidence** tells you:
- How trustworthy the extraction is
- Whether to investigate further
- Filter threshold for low-quality data

---

## ⚙️ Configuration

### **Minimum Confidence Threshold**

Edit `src/pipeline/runner.py`:

```python
MIN_CONFIDENCE = 0.3  # Default: accept docs with 30%+ confidence

# Stricter filtering:
MIN_CONFIDENCE = 0.5  # Only accept 50%+ confidence

# Very strict:
MIN_CONFIDENCE = 0.7  # Only high-quality extractions
```

**Recommendation:**
- **0.3**: Good default, catches most valid documents
- **0.5**: If you're getting too much noise
- **0.7**: Only when you need high-quality data

---

### **Disable Filtering**

To accept ALL documents regardless of relevance:

```python
# Comment out relevance check in runner.py
# if not normalized_event.is_relevant:
#     ...
#     return
```

To accept ALL confidence levels:

```python
MIN_CONFIDENCE = 0.0  # Accept everything
```

---

## 🧪 Testing Filter Effectiveness

### **Create a test file with irrelevant content:**

`raw_data_bucket/test_irrelevant.txt`:
```
My Top 10 Productivity Tips for 2026

1. Wake up early
2. Exercise daily
3. Use a to-do list
...
```

**Run pipeline:**
```bash
python main.py run
```

**Expected output:**
```
⊘ Document not relevant: This is a personal blog about productivity tips, not a company event
```

✅ Document filtered out!

---

### **Create a test file with low confidence:**

`raw_data_bucket/test_vague.txt`:
```
There's a company doing something interesting.
They might be getting funding or maybe hiring.
```

**Run pipeline:**
```bash
python main.py run
```

**Expected output:**
```
⊘ Confidence too low: 0.25 (minimum: 0.3)
```

✅ Low-quality document filtered out!

---

## 📈 Monitoring Filter Statistics

Check how many documents are being filtered:

```bash
# Connect to database
psql -U leadgen_user -d leadgen_db -h localhost

# Count by status
SELECT status, COUNT(*)
FROM raw_events
GROUP BY status;
```

**Example output:**
```
  status   | count
-----------+-------
 PROCESSED |   50
 FAILED    |   15
```

**Check failure reasons:**
```sql
SELECT error, COUNT(*)
FROM raw_events
WHERE status = 'FAILED'
GROUP BY error;
```

**Example output:**
```
                    error                      | count
----------------------------------------------+-------
 Document not relevant: personal blog         |   8
 Confidence too low: 0.28 < 0.3               |   5
 Normalization failed                          |   2
```

---

## 🎓 Best Practices

### **1. Start Permissive**
- Begin with MIN_CONFIDENCE = 0.3
- Monitor what gets filtered
- Adjust upward if needed

### **2. Review Failed Documents**
```sql
SELECT file_path, error
FROM raw_events
WHERE status = 'FAILED'
LIMIT 10;
```

Check if legitimate documents are being filtered.

### **3. Tune for Your Domain**

**If processing financial news:**
- Keep MIN_CONFIDENCE = 0.5+ (need accuracy)

**If processing social media:**
- Use MIN_CONFIDENCE = 0.3 (more noise, but catch signals)

**If processing curated sources:**
- Can lower to 0.2 (sources already filtered)

### **4. Create a Review Queue**

For documents with 0.3-0.5 confidence:
```sql
SELECT * FROM raw_events
WHERE status = 'FAILED'
AND error LIKE 'Confidence too low%';
```

Manually review these periodically.

---

## 🔍 Example Scenarios

### **Scenario 1: Tech Company Newsletter**

**Document:** Newsletter with multiple company mentions

**LLM Response:**
```json
{
  "is_relevant": true,
  "relevance_reasoning": "Contains multiple company funding announcements",
  "extraction_confidence": 0.85,
  "company_name_raw": "TechStartup Inc",
  ...
}
```

✅ **Accepted** (relevant + high confidence)

---

### **Scenario 2: Personal LinkedIn Post**

**Document:** "Just got promoted to VP of Engineering!"

**LLM Response:**
```json
{
  "is_relevant": false,
  "relevance_reasoning": "Personal achievement post, not about company event",
  ...
}
```

❌ **Rejected** (not relevant)

---

### **Scenario 3: Unclear Press Release**

**Document:** "A company announced something today."

**LLM Response:**
```json
{
  "is_relevant": true,
  "relevance_reasoning": "Appears to be company news but very vague",
  "extraction_confidence": 0.25,
  "company_name_raw": "Unknown",
  ...
}
```

❌ **Rejected** (confidence too low: 0.25 < 0.3)

---

### **Scenario 4: Well-Written Company News**

**Document:** "Acme Cloud raises $50M Series B led by VC Partners"

**LLM Response:**
```json
{
  "is_relevant": true,
  "relevance_reasoning": "Clear company funding announcement",
  "extraction_confidence": 0.95,
  "company_name_raw": "Acme Cloud",
  ...
}
```

✅ **Accepted** (relevant + very high confidence)

---

## 🛠️ Advanced: Custom Relevance Rules

You can add domain-specific rules in the prompt.

**Example for SaaS companies only:**

Edit `src/llm/prompts.py`:

```python
RELEVANCE CHECK:
Set is_relevant=true ONLY if the document discusses:
- A SaaS, software, or cloud company
- B2B software businesses
- Tech startups

Set is_relevant=false for:
- Hardware companies
- Retail businesses
- Personal blogs
- ...
```

---

## Summary

**Filtering Stages:**
1. ✅ Relevance check → Filter out non-company documents
2. ✅ Confidence threshold → Filter out low-quality extractions

**Confidence Scoring:**
- **Extraction confidence**: Set by LLM per event (0.0-1.0)
- **Lead confidence**: Simple average of all event confidences
- **Does NOT affect lead score** (just a quality indicator)

**Configuration:**
- `MIN_CONFIDENCE` in `runner.py:119` (default: 0.3)
- Start permissive, tighten based on results
- Monitor `raw_events` table for filter statistics

**Best Practice:**
- Review failed documents periodically
- Adjust threshold for your domain
- Use relevance for broad filtering
- Use confidence for quality filtering
