# Enrichment Options: Do You Need Search APIs?

## TL;DR: You Can Skip It Entirely! 🎯

The enrichment step is **completely optional**. The pipeline works great without it.

---

## What Does Enrichment Do?

Enrichment finds a company's **official domain** (like "acmecloud.io") and additional details:
- Official domain (for better deduplication)
- Website URL
- LinkedIn company page
- Headquarters location

**Main benefit:** Better entity deduplication
- "Acme Cloud Inc" + "ACME CLOUD LLC" → both have domain "acmecloud.io" → merged into 1 entity

**Without enrichment:**
- Relies on fuzzy name matching (still works well!)
- No web data (domain, LinkedIn, etc.)

---

## Option 1: Disable Enrichment (Simplest) ⭐

**Set in `.env`:**
```bash
ENRICHMENT_ENABLED=false
```

**When to use:**
- Your documents have consistent company names
- You don't need web enrichment data
- You want to minimize costs and complexity

**Pros:**
- ✅ No search API needed
- ✅ No extra costs
- ✅ Faster processing
- ✅ Fewer dependencies

**Cons:**
- ❌ Deduplication relies only on name matching
- ❌ No domain/website/LinkedIn data

**Cost:** $0

---

## Option 2: Use Real LLM Without Search

Keep `ENRICHMENT_ENABLED=true` but use **mock search** (default).

The system will:
1. Use mock search results (fake but structured)
2. Feed them to the LLM
3. LLM extracts domain based on the fake results

Or modify to skip search and ask LLM directly from its training data.

**When to use:**
- Testing the pipeline
- Well-known companies (in LLM training data)

**Pros:**
- ✅ No search API cost
- ✅ Works for famous companies

**Cons:**
- ❌ Limited to LLM's knowledge cutoff
- ❌ No data for new/small companies
- ❌ May hallucinate

**Cost:** $0 (just LLM API for extraction, which you're already using)

---

## Option 3: OpenAI + Bing Search API

**No, OpenAI doesn't have built-in search in the API.**

But you can use **Bing Web Search API**:

**Setup:**
```bash
# Get free API key from Azure
# https://azure.microsoft.com/en-us/services/cognitive-services/bing-web-search-api/

# Modify src/enrich/search_client.py
import requests

def bing_search(query):
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    response = requests.get(
        "https://api.bing.microsoft.com/v7.0/search",
        headers=headers,
        params={"q": query, "count": 5}
    )
    return response.json()['webPages']['value']
```

**Free Tier:** 1,000 searches/month
**Paid:** $7 per 1,000 searches

**Pros:**
- ✅ Microsoft ecosystem integration
- ✅ Good free tier
- ✅ Reliable results

**Cons:**
- ❌ Need Azure account
- ❌ More complex setup than Tavily

**Cost:** $0-7 per 1,000 entities

---

## Option 4: OpenAI + Google Custom Search

**Setup:**
```bash
# Get API key from Google Cloud Console
# https://developers.google.com/custom-search/v1/introduction

GOOGLE_SEARCH_API_KEY=your_key
GOOGLE_SEARCH_ENGINE_ID=your_engine_id
```

**Free Tier:** 100 searches/day
**Paid:** $5 per 1,000 searches (after 100/day)

**Pros:**
- ✅ Google's search quality
- ✅ Decent free tier

**Cons:**
- ❌ Need Google Cloud account
- ❌ Lower free tier than Bing

**Cost:** $0-5 per 1,000 entities (after free tier)

---

## Option 5: Tavily (Current Implementation)

**Why Tavily exists:**
- Designed specifically for AI/LLM applications
- Clean, structured results (no parsing needed)
- Good for company/entity search
- Simple API

**Setup:**
```bash
# Get key from tavily.com
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-your-key
```

**Free Tier:** 1,000 searches/month
**Paid:** $50/month for 10,000 searches (~$0.005 per search)

**Pros:**
- ✅ LLM-optimized results
- ✅ Simple API
- ✅ Good for entities/companies

**Cons:**
- ❌ Another service to manage
- ❌ Slightly pricier at scale

**Cost:** $0-50/month

---

## Option 6: Exa (Alternative to Tavily)

Similar to Tavily, designed for AI applications.

**Setup:**
```bash
SEARCH_PROVIDER=exa
EXA_API_KEY=your_key
```

**Pricing:** Similar to Tavily (~$0.005-0.01 per search)

---

## Cost Comparison

| Option | Setup | Cost/1K entities | Best For |
|--------|-------|------------------|----------|
| **No enrichment** | Edit .env | $0 | Simple use cases, consistent names |
| **Mock search** | Already set up | $0 | Testing, well-known companies |
| **Bing Search** | Azure account | $7 | Microsoft ecosystem users |
| **Google Search** | GCP account | $5 | Google ecosystem users |
| **Tavily** | Tavily account | $5 | Simplicity, LLM focus |
| **Exa** | Exa account | $5 | Alternative to Tavily |

---

## My Recommendation 🎯

### For Getting Started (This Week)
```bash
ENRICHMENT_ENABLED=false
```
**Just turn it off!** Test the pipeline without enrichment. See if name matching works for your data.

### If You Need Better Deduplication (Next Month)
**Option A: Use Bing** (if you have Azure)
- Good free tier
- Microsoft integration

**Option B: Use Tavily** (if you want simplicity)
- Easy setup
- AI-optimized

### At Scale (Later)
**Compare costs:**
- If processing <1,000 entities/month → Any free tier
- If processing 10,000+ entities/month → Compare Bing ($70) vs Tavily ($50)

---

## Quick Setup: Disable Enrichment Right Now

**Edit `.env`:**
```bash
ENRICHMENT_ENABLED=false
```

**Run pipeline:**
```bash
python main.py run
```

You'll see:
```
⊙ Enrichment disabled (set ENRICHMENT_ENABLED=true to enable)
```

**That's it!** Pipeline works perfectly without enrichment.

---

## FAQ

**Q: Will deduplication still work without enrichment?**
Yes! It uses fuzzy name matching. "Acme Cloud Inc" and "ACME CLOUD" will still merge (85%+ similarity).

**Q: Can I add enrichment later?**
Yes! Just enable it and re-run the pipeline. It will enrich existing entities.

**Q: Does OpenAI's API have built-in search?**
No. ChatGPT (the web interface) has browsing via Bing, but the API doesn't include search.

**Q: Which search is best?**
For simplicity: **Tavily**
For free tier: **Bing** (1,000/month vs Tavily's 1,000/month, similar)
For Google ecosystem: **Google Custom Search**

**Q: Can the LLM just "know" the domain without search?**
Sometimes, for famous companies. But it will be limited to its training data cutoff and may hallucinate.

---

## Bottom Line

**Start simple:** Disable enrichment (`ENRICHMENT_ENABLED=false`)

**Test:** See if name-based deduplication is good enough

**Add later:** If you need better matching, choose:
- Bing (Azure users)
- Tavily (simplicity)
- Google (GCP users)

You don't need Tavily specifically - it's just one of several options!
