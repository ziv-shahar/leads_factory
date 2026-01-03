# Event Deduplication for Scoring Plan

## Problem
Multiple news sources often report the same event (e.g., "Google acquires Wiz for $32B"). Currently, each duplicate event gets scored separately, artificially inflating scores:
- 100 articles about same acquisition → 100 events → score multiplied by 100x ❌

## Goal
Group duplicate events by **company + event_type + same day** during scoring, then average their confidence/score:
- 100 articles about Google's acquisition on Jan 3 → average confidence and score → correct score ✓

**IMPORTANT**:
- We do NOT modify the database. All events stay as-is. Deduplication happens only during scoring calculation.
- Events from different companies are NEVER grouped together (even if same type and date)

## Implementation Strategy

### 1. Simplified Scoring Logic (In-Memory Grouping)

**No new classes needed!** Just modify `Scorer` to group events during calculation.

**Approach**:
```python
def score_entity(self, entity: Entity, events: List[Event]) -> float:
    # NOTE: events parameter already contains only this entity's events
    # Group events by (event_type, date) - no need for entity_id since we're scoring one entity
    groups = defaultdict(list)
    for event in events:
        key = (event.event_type, event.event_time.date())
        groups[key].append(event)

    # Score each group (averaging duplicates)
    total_score = 0
    for (event_type, date), duplicate_events in groups.items():
        # Average confidence across duplicates
        avg_confidence = mean([e.extraction_confidence for e in duplicate_events])

        # Score the event_type once
        event_score = self._score_event_type(event_type)

        # Average dynamic signal scores
        avg_signal_score = mean([
            self._score_dynamic_signals(e.dynamic_signals)
            for e in duplicate_events
        ])

        # Apply averaged confidence
        group_score = (event_score + avg_signal_score) * avg_confidence
        total_score += group_score

    return total_score
```

**Key insight**: No data modification, just smart grouping during calculation!

**Why no entity_id in grouping key?**
The `score_entity(entity, events)` function is called **once per entity** with only that entity's events. So we don't need to include entity_id in the key - all events are already from the same company!

### 2. Updated Scorer Implementation

**File**: `src/score/scorer.py`

**Current flow**:
```
get events for entity → score each event individually → sum scores
```

**New flow**:
```
get events for entity → group by (type, date) → average each group → sum scores
```

**Complete implementation**:
```python
from collections import defaultdict
from statistics import mean

class Scorer:
    def score_entity(self, entity: Entity, events: List[Event]) -> float:
        """
        Score entity by averaging duplicate events before summing.

        Grouping: Events with same event_type on same date are averaged.
        """
        if not events:
            return 0.0

        # Group events by (event_type, date)
        groups = defaultdict(list)
        for event in events:
            event_date = event.event_time.date() if event.event_time else None
            key = (event.event_type, event_date)
            groups[key].append(event)

        # Score each group
        total_score = 0.0
        for (event_type, date), duplicate_events in groups.items():
            # Calculate scores for each duplicate
            event_scores = []
            for event in duplicate_events:
                event_type_score = self._score_event_type(event.event_type)
                signal_score = self._score_dynamic_signals(event.dynamic_signals)
                event_total = event_type_score + signal_score

                # Apply confidence
                weighted_score = event_total * event.extraction_confidence
                event_scores.append(weighted_score)

            # Average the scores for this group
            avg_score = mean(event_scores)
            total_score += avg_score

        return total_score
```

**Example**:
```
# Before (100 duplicate acquisitions):
score = 15 * 100 = 1500

# After (100 duplicates averaged):
scores = [15*0.9, 15*0.85, 15*0.92, ...] (100 scores)
avg_score = mean(scores) = ~13.5
total = 13.5 (NOT 1500!)
```

### 3. Date Handling

**What counts as "same day"?**
- Use `event_time.date()` for grouping (ignores time)
- Events on different days are NOT duplicates (even if same type)

**Example** (for Google entity):
- Google acquisition on 2026-01-03 → Group A
- Google acquisition on 2026-01-05 → Group B (different event!)
- Google acquisition on 2026-01-03 (from another source) → Group A (duplicate)

**Important**: Microsoft acquisition on 2026-01-03 is scored separately (different entity, different call to `score_entity()`)

**Edge case**: What if `event_time` is null?
```python
event_date = event.event_time.date() if event.event_time else None
key = (event.event_type, event_date)
# Events with None date group separately
```

### 4. Testing Strategy

**Test cases**:

1. **No duplicates** (control)
   - 3 different events (acquisition, funding, layoffs) → 3 groups
   - Score = sum of all 3

2. **Perfect duplicates**
   - 10 identical acquisition events (same day) → 1 group with 10 events
   - Score = average of 10 scores (NOT sum!)

3. **Partial duplicates**
   - 5 acquisition events on Jan 3
   - 3 expansion events on Jan 5
   - 2 acquisition events on Jan 10
   - Result: 3 groups, each averaged separately

4. **Different confidence levels**
   - Event A: acquisition, score 15 * 0.9 = 13.5
   - Event B: acquisition, score 15 * 0.7 = 10.5 (same day)
   - Event C: acquisition, score 15 * 0.8 = 12.0 (same day)
   - Group average: (13.5 + 10.5 + 12.0) / 3 = 12.0

### 5. Implementation Steps

1. Read current `src/score/scorer.py` to understand existing logic
2. Update `score_entity()` method to group events before scoring
3. Test with duplicate events
4. Verify scores are reasonable (not inflated)

### 6. Edge Cases to Handle

**Q: What if same event type but different key_facts?**
- Example: "Google layoffs - 100 people" vs "Google layoffs - 200 people" (same day)
- **Answer**: Still group together and average. Both are reporting the same event.

**Q: What if event_time is null?**
- **Answer**: Group key = `(event_type, None)`. Events with null dates group separately.

**Q: Should we group across different event_types?**
- Example: "Google acquisition" + "Google expansion" on same day
- **Answer**: NO. Different event types = different groups. Only average within same type.

### 7. Success Metrics

**Before averaging (current)**:
- 100 news articles about Google acquisition (same day) → Score: 15 * 100 = **1,500**

**After averaging (new)**:
- 100 news articles about Google acquisition (same day) → Averaged score: **~13-15**
- Each article has slightly different confidence (0.85-0.95)
- Average of (15*0.9 + 15*0.85 + ... + 15*0.92) / 100 ≈ 13.5

**Validation**:
- Scores for popular companies (Google, Apple) should be reasonable (not 1000+)
- Multiple events of different types should still add up
- Example: Google has acquisition (15) + expansion (18) = 33 points total

## Summary

This plan implements **in-memory event averaging during scoring** to prevent duplicate events from inflating scores:

1. **Keep all events in database** (no changes to data)
2. **During scoring**: Group events by (event_type, date)
3. **Average each group's score** instead of summing
4. **Sum the averaged groups** for final score

**Key insight**: All events stay in database. Averaging happens only during score calculation.
