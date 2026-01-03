# Event Deduplication for Scoring Plan

## Problem
Multiple news sources often report the same event (e.g., "Google acquires Wiz for $32B"). Currently, each duplicate event gets scored separately, artificially inflating scores:
- 100 articles about same acquisition → 100 events → score multiplied by 100x ❌

## Goal
Group duplicate events by company + event_type + same day, then average them before scoring:
- 100 articles about same acquisition → 1 consolidated event → correct score ✓

## Implementation Strategy

### 1. Event Deduplication Logic (New Module)
**File**: `src/score/deduplicator.py`

```python
class EventDeduplicator:
    """Deduplicate events before scoring."""

    def deduplicate_events(self, events: List[Event]) -> List[ConsolidatedEvent]:
        """
        Group events by (entity, event_type, date) and consolidate duplicates.

        Grouping keys:
        - entity_id (same company)
        - event_type (same type: acquisition, funding, etc.)
        - event_date (same day, using event_time.date())

        Returns consolidated events with:
        - averaged confidence
        - combined dynamic_signals
        - list of source_ids for audit trail
        """
        pass
```

**ConsolidatedEvent structure**:
```python
class ConsolidatedEvent:
    entity_id: int
    event_type: str
    event_date: date

    # Averaged/consolidated fields
    average_confidence: float
    combined_dynamic_signals: List[DynamicSignal]

    # Metadata
    source_count: int  # How many duplicate sources
    event_ids: List[str]  # Original event IDs for audit
    representative_summary: str  # Best summary from duplicates
```

### 2. Deduplication Algorithm

**Step-by-step**:

1. **Group events** by key: `(entity_id, event_type, event_date)`
   ```python
   groups = defaultdict(list)
   for event in events:
       key = (event.entity_id, event.event_type, event.event_time.date())
       groups[key].append(event)
   ```

2. **For each group, consolidate**:
   ```python
   consolidated = []
   for (entity_id, event_type, event_date), duplicate_events in groups.items():
       # Average confidence
       avg_confidence = mean([e.extraction_confidence for e in duplicate_events])

       # Combine unique dynamic signals (dedupe by signal_type)
       all_signals = []
       for event in duplicate_events:
           all_signals.extend(event.dynamic_signals)
       unique_signals = dedupe_signals_by_type(all_signals)

       # Pick best summary (highest confidence event)
       best_event = max(duplicate_events, key=lambda e: e.extraction_confidence)

       consolidated.append(ConsolidatedEvent(
           entity_id=entity_id,
           event_type=event_type,
           event_date=event_date,
           average_confidence=avg_confidence,
           combined_dynamic_signals=unique_signals,
           source_count=len(duplicate_events),
           event_ids=[e.id for e in duplicate_events],
           representative_summary=best_event.summary
       ))
   ```

3. **Dedupe dynamic signals**:
   ```python
   def dedupe_signals_by_type(signals: List[Dict]) -> List[Dict]:
       """Keep only one signal per signal_type, picking highest evidence quality."""
       seen = {}
       for signal in signals:
           sig_type = signal['signal_type']
           if sig_type not in seen or len(signal.get('evidence_quote', '')) > len(seen[sig_type].get('evidence_quote', '')):
               seen[sig_type] = signal
       return list(seen.values())
   ```

### 3. Integration with Scorer

**Update**: `src/score/scorer.py`

**Current flow**:
```
get events for entity → score each event → sum scores
```

**New flow**:
```
get events for entity → deduplicate events → score consolidated events → sum scores
```

**Changes**:
```python
class Scorer:
    def __init__(self):
        self.deduplicator = EventDeduplicator()

    def score_entity(self, entity: Entity, events: List[Event]) -> float:
        # NEW: Deduplicate events first
        consolidated_events = self.deduplicator.deduplicate_events(events)

        # Score consolidated events (not raw events)
        total_score = 0
        for cons_event in consolidated_events:
            event_score = self._score_event_type(cons_event.event_type)
            signal_score = self._score_dynamic_signals(cons_event.combined_dynamic_signals)

            # Apply average confidence
            total_score += (event_score + signal_score) * cons_event.average_confidence

        return total_score
```

### 4. Date Handling Considerations

**What counts as "same day"?**
- Use `event_time.date()` for grouping (ignores time)
- Events on different days are NOT duplicates (even if same type)

**Example**:
- Google acquisition on 2026-01-03 → Group A
- Google acquisition on 2026-01-05 → Group B (different event!)
- Google acquisition on 2026-01-03 (from another source) → Group A (duplicate)

**Edge case**: What if `event_date` is null?
```python
# Group by event_date if available, otherwise use event_time.date()
def get_event_date(event: Event) -> date:
    if event.event_time:
        return event.event_time.date()
    return None  # Group separately as "unknown date"
```

### 5. Audit Trail & Transparency

**Problem**: User needs to see which events were consolidated.

**Solution**: Add metadata to LeadCurrent:
```python
# In scoring result
class ScoringMetadata:
    total_events: int  # Raw event count
    unique_events: int  # After deduplication
    consolidation_ratio: float  # unique/total (lower = more duplicates)
```

**Display in view_data.py**:
```
Entity: GOOGLE
  Score: 18
  Total Events: 47
  Unique Events: 3  (consolidated from 47 sources)
  Event Types:
    - acquisition (15 sources → 1 consolidated event)
    - expansion (2 sources → 1 consolidated event)
    - hiring_surge (30 sources → 1 consolidated event)
```

### 6. Testing Strategy

**Test cases**:

1. **No duplicates** (control)
   - 3 different events (acquisition, funding, layoffs) → 3 consolidated events
   - Score = sum of all 3

2. **Perfect duplicates**
   - 10 identical acquisition events (same day) → 1 consolidated event
   - Score = 1x acquisition score (NOT 10x)

3. **Partial duplicates**
   - 5 acquisition events on Jan 3
   - 3 expansion events on Jan 5
   - 2 acquisition events on Jan 10
   - Result: 3 consolidated events

4. **Different confidence levels**
   - Event A: confidence 0.9
   - Event B: confidence 0.7 (duplicate of A)
   - Event C: confidence 0.8 (duplicate of A)
   - Consolidated: confidence = (0.9 + 0.7 + 0.8) / 3 = 0.8

5. **Dynamic signal merging**
   - Event A: signals [office_expansion, hiring_surge]
   - Event B: signals [office_expansion, technology_adoption] (duplicate)
   - Consolidated: signals [office_expansion, hiring_surge, technology_adoption]

### 7. Implementation Order

**Phase 1: Core deduplication** (MVP)
1. Create `src/score/deduplicator.py` with `EventDeduplicator` class
2. Implement grouping by (entity_id, event_type, date)
3. Implement consolidation (average confidence, merge signals)
4. Add unit tests

**Phase 2: Integration**
5. Update `Scorer` to use deduplicator
6. Test with real data (100 duplicate events)
7. Verify scores are correct

**Phase 3: Transparency**
8. Add consolidation metadata to scoring
9. Update view_data.py to show consolidation stats
10. Add audit trail (which events were consolidated)

### 8. Edge Cases to Handle

**Q: What if same event type but different key_facts?**
- Example: "Google layoffs - 100 people" vs "Google layoffs - 200 people"
- **Answer**: Still consolidate (same day, same type). Pick highest confidence for key_facts.

**Q: What if event_time is null?**
- **Answer**: Group separately as "unknown_date" category, don't consolidate with dated events.

**Q: What about events spanning multiple days?**
- Example: "Layoffs announced Monday, effective Friday"
- **Answer**: Use `event_date` field if available, otherwise `event_time`. Single canonical date per event.

**Q: Should we consolidate across different event_types?**
- Example: "Google acquisition" + "Google expansion" on same day
- **Answer**: NO. Different event types = different events. Only consolidate within same type.

### 9. Database Schema Changes

**Option A**: No schema changes
- Deduplication happens in-memory during scoring
- All raw events stay in database
- ✓ Simple, no migration needed

**Option B**: Add consolidation table
- New table: `consolidated_events`
- Stores pre-computed consolidations
- ✓ Faster scoring, ✗ More complexity

**Recommendation**: Start with Option A (in-memory), migrate to Option B if performance issues.

### 10. Success Metrics

**Before deduplication**:
- 100 news articles about Google acquisition → Score: 1500 (15 per event * 100)

**After deduplication**:
- 100 news articles about Google acquisition → 1 consolidated event → Score: 15
- Confidence: average of 100 confidences (e.g., 0.92)

**Validation**:
- Check consolidation_ratio for popular companies (Google, Apple, etc.)
- Should see ratio < 0.5 (more than 50% duplicates)
- Scores should be more reasonable (not inflated by news coverage)

## Summary

This plan implements event deduplication **before scoring** to prevent duplicate events from inflating scores. The key insight is:

**Raw events** (stored in DB) → **Consolidated events** (in-memory grouping) → **Scoring** (on consolidated)

This preserves all source data while ensuring fair scoring.
