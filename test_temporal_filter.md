# Temporal Status Filter - Test Examples

This document shows how the new temporal status filter distinguishes between planned/future moves (what we want) vs completed/past moves (what we filter out).

## ✅ PLANNED - Will be EXTRACTED and SCORED

These indicate future moves that haven't happened yet:

### Example 1: Seeking Office Space
**Article:** "Waymo is seeking office space in Los Angeles for its autonomous vehicle operations."
- **temporal_status:** `planned`
- **Reason:** "seeking" = future intent, not yet happened
- **Lead Value:** HIGH - company is actively looking for space

### Example 2: Government RFP
**Article:** "GSA issued RFP for 50,000 sq ft office lease in Miami, FL."
- **temporal_status:** `planned`
- **Reason:** RFP = seeking tenant, future lease
- **Lead Value:** HIGH - government actively seeking space

### Example 3: Plans to Expand
**Article:** "TechCorp plans to open a new engineering hub in Austin, targeting Q3 2026."
- **temporal_status:** `planned`
- **Reason:** "plans to" = future action
- **Lead Value:** HIGH - announced future expansion

### Example 4: Will Hire
**Article:** "Anthropic will hire 1,000 AI researchers over the next 12 months."
- **temporal_status:** `planned`
- **Reason:** "will hire" = future hiring
- **Lead Value:** MEDIUM - future hiring indicates potential space needs

### Example 5: Considering Expansion
**Article:** "Meta is considering expanding its data center footprint in Virginia."
- **temporal_status:** `planned`
- **Reason:** "considering" = evaluating future action
- **Lead Value:** MEDIUM - potential future expansion

## ⏳ IN_PROGRESS - Will be EXTRACTED and SCORED

These indicate ongoing moves currently happening:

### Example 6: Currently Hiring
**Article:** "Salesforce is currently hiring 500 engineers across its US offices."
- **temporal_status:** `in_progress`
- **Reason:** "currently hiring" = active ongoing process
- **Lead Value:** MEDIUM - may need more space soon

### Example 7: In Negotiations
**Article:** "Amazon is in negotiations to lease 100,000 sq ft in Seattle."
- **temporal_status:** `in_progress`
- **Reason:** "in negotiations" = active process
- **Lead Value:** HIGH - deal in progress

## ❌ COMPLETED - Will be FILTERED OUT

These describe past moves that already happened:

### Example 8: Opened Office (Past Tense)
**Article:** "Google opened a new office in Boston last month."
- **temporal_status:** `completed`
- **Reason:** "opened" = past tense, already happened
- **Lead Value:** ZERO - not predictive of future needs
- **Filter:** ❌ EXCLUDED from scoring

### Example 9: Hired (Past Tense)
**Article:** "Target hired 500 seasonal workers in December."
- **temporal_status:** `completed`
- **Reason:** "hired" = past action, already done
- **Lead Value:** ZERO - already completed
- **Filter:** ❌ EXCLUDED from scoring

### Example 10: Signed Lease (Past Tense)
**Article:** "Nvidia signed a 10-year lease for office space in Israel."
- **temporal_status:** `completed`
- **Reason:** "signed" = completed action
- **Lead Value:** ZERO - deal already done
- **Filter:** ❌ EXCLUDED from scoring

### Example 11: Expanded (Past Tense)
**Article:** "Acme Corp expanded to three new cities last quarter."
- **temporal_status:** `completed`
- **Reason:** "expanded" = past action
- **Lead Value:** ZERO - expansion already happened
- **Filter:** ❌ EXCLUDED from scoring

### Example 12: Raised Funding (Past)
**Article:** "Startup XYZ raised $50M in Series B funding."
- **temporal_status:** `completed`
- **Reason:** "raised" = past tense, money already received
- **Lead Value:** ZERO for this specific event
- **Filter:** ❌ EXCLUDED from scoring
- **Note:** However, this might indicate FUTURE hiring/expansion

## Summary

### What Gets SCORED (Predictive):
- ✅ **planned** - "seeking", "plans to", "will", "considering", "to expand"
- ✅ **in_progress** - "is hiring", "currently", "in negotiations"

### What Gets FILTERED OUT (Not Predictive):
- ❌ **completed** - "opened", "hired", "raised", "signed", "expanded" (past tense)

## Impact

**Before Filter:**
- System captured 100% of events including completed moves
- Mixed predictive signals with historical data
- Lower lead quality

**After Filter:**
- System captures only planned/in_progress events (~30-40% of total)
- Higher quality leads - only future/active moves
- Better prediction of actual space needs

## Testing the Filter

To test if the filter is working:

1. Run pipeline with sample articles containing both planned and completed events
2. Check database: `SELECT event_type, temporal_status, strict->>'summary' FROM events LIMIT 20;`
3. Verify only planned/in_progress events are scored
4. Check lead scores reflect only future moves
