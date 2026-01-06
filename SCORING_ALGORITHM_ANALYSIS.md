# Scoring Algorithm Analysis & Improvements

## Current System Analysis

### What Works Well ✓
1. **Clear Signal Hierarchy**: Event types and dynamic signals have well-defined scores
2. **Bidirectional Value**: Both expansion (hiring) and contraction (layoffs) signal office changes
3. **Event Deduplication**: Prevents duplicate news from inflating scores
4. **Time Decay**: Recent events weighted more heavily
5. **Source Diversity Bonus**: Rewards multi-source validation

### Current Limitations ⚠️

#### 1. **Linear Time Decay**
**Current**: Linear decay from 1.0 to 0.3 over time_decay_days
```python
decay = 1.0 - (0.7 * (age_days - 30) / (time_decay_days - 30))
```

**Problem**: Real-world relevance decays exponentially, not linearly
- A 90-day-old funding round is much more relevant than 180-day-old
- But 180-day vs 270-day difference is less significant

#### 2. **No Signal Co-occurrence Analysis**
**Current**: Each signal scored independently
```
funding_round (20) + hiring_surge (10) = 30 points
```

**Problem**: Signals that appear together are stronger predictors
- Funding + hiring surge + office_expansion = very strong signal
- Just hiring surge alone = weaker signal

#### 3. **Fixed Weights (No Learning)**
**Current**: Hardcoded scores (funding_round=20, acquisition=18, etc.)

**Problem**: No validation against actual outcomes
- Are layoffs really as valuable as hiring for office predictions?
- Which signal combinations predict office changes best?

#### 4. **Confidence Tracked But Unused**
**Current**: Confidence stored but not applied to scores
```python
confidence_scores.append(event.extraction_confidence)  # Tracked
# But never multiplied into the score!
```

**Problem**: High-confidence events should count more than low-confidence

#### 5. **No Entity-Level Features**
**Current**: Only event-based scoring

**Missing**:
- Company size (larger companies = bigger office changes)
- Industry (tech vs retail have different office needs)
- Growth trajectory (fast-growing companies more likely to need space)
- Geographic distribution (multi-location companies vs single office)

#### 6. **Simple Source Diversity**
**Current**: +5 points per additional source
```python
source_bonus = (unique_sources - 1) * 5
```

**Problem**: Doesn't account for source quality or independence
- 5 press releases vs 5 independent journalists
- Local news vs national outlets

## Recommended Improvements (Prioritized)

### Phase 1: Quick Wins (High Impact, Low Effort)

#### 1.1 Exponential Time Decay ⭐⭐⭐
**Replace linear with exponential decay**

```python
def _calculate_time_decay(self, event_date: datetime) -> float:
    """Exponential time decay - more realistic relevance degradation."""
    if not event_date:
        return 0.5

    age_days = (datetime.utcnow() - event_date).days

    if age_days < 0:
        return 1.0
    elif age_days <= 30:
        return 1.0  # Recent events, full score
    else:
        # Exponential decay: half-life of 90 days
        # After 90 days: 50% relevance
        # After 180 days: 25% relevance
        # After 270 days: 12.5% relevance
        half_life_days = 90
        decay = 0.5 ** ((age_days - 30) / half_life_days)
        return max(0.1, decay)  # Floor at 10%
```

**Why**: Research shows information relevance follows power law/exponential decay, not linear

**Impact**: Better discrimination between recent and old events

---

#### 1.2 Apply Confidence to Scores ⭐⭐⭐
**Use extraction confidence as multiplier**

```python
# Current (confidence ignored):
decayed_score = event_score * decay_multiplier

# Improved (confidence applied):
decayed_score = event_score * decay_multiplier * event.extraction_confidence
```

**Why**: Low-confidence extractions are less reliable and should contribute less

**Impact**:
- High confidence (0.9): Nearly full score
- Medium confidence (0.7): 70% of score
- Low confidence (0.5): Half score

**Caveat**: Requires confidence calibration (are your 0.9 confidences actually 90% accurate?)

---

#### 1.3 Signal Co-occurrence Multipliers ⭐⭐
**Boost scores when strong signal combinations appear**

```python
def _calculate_signal_multiplier(self, events: List[Event]) -> float:
    """
    Boost score when multiple correlated signals appear together.

    Strong combinations:
    - funding_round + hiring_surge + office_expansion = 1.5x
    - acquisition + office_integration + employee_relocation = 1.4x
    - layoffs + office_downsizing + remote_work_transition = 1.3x
    """
    # Collect all event types and signal types
    event_types = {e.event_type for e in events}
    signal_types = {
        sig.get('signal_type')
        for e in events
        for sig in e.dynamic_signals
    }

    # Check for strong combinations
    if ('funding_round' in event_types and
        'hiring_surge' in signal_types and
        'office_expansion' in signal_types):
        return 1.5

    if ('acquisition' in event_types and
        'office_integration' in signal_types):
        return 1.4

    if ('layoffs' in event_types and
        'office_downsizing' in signal_types):
        return 1.3

    # Mild boost for any 2+ correlated signals
    if len(event_types) >= 2 and len(signal_types) >= 2:
        return 1.2

    return 1.0  # No boost

# Apply in scoring:
total_score = base_score * signal_multiplier
```

**Why**: Correlated signals are stronger evidence than isolated signals

**Impact**: Separates truly strong leads (multiple signals) from weak ones (single signal)

---

### Phase 2: Medium-Complexity Improvements

#### 2.1 Entity Size Normalization ⭐⭐
**Adjust scores based on company size**

```python
def _get_entity_size_multiplier(self, entity: Entity) -> float:
    """
    Larger companies = bigger office changes = more valuable leads.

    Use heuristics:
    - Domain age (older = more established)
    - Funding amount (if in key_facts)
    - Employee count estimates (from signals)
    """
    # Simple version: Check funding amounts
    total_funding = 0
    for event in entity.events:
        amount_str = event.strict.get('key_facts', {}).get('amount', '')
        if 'M' in amount_str or 'B' in amount_str:
            # Parse "$100M" or "$1.5B"
            try:
                if 'B' in amount_str:
                    total_funding += float(amount_str.replace('$','').replace('B','')) * 1000
                elif 'M' in amount_str:
                    total_funding += float(amount_str.replace('$','').replace('M',''))
            except:
                pass

    # Multiplier based on funding
    if total_funding > 500:  # >$500M
        return 1.3
    elif total_funding > 100:  # >$100M
        return 1.2
    elif total_funding > 50:   # >$50M
        return 1.1
    else:
        return 1.0
```

**Why**: A $50M Series C for 500-person company is bigger office change than $5M for 10-person startup

---

#### 2.2 Smarter Source Diversity ⭐⭐
**Weight source diversity by quality and independence**

```python
def _calculate_source_diversity_score(self, events: List[Event]) -> int:
    """
    Better source diversity scoring.

    Tiers:
    - Tier 1: Major outlets (TechCrunch, Bloomberg, WSJ, etc.) = 10 points
    - Tier 2: Industry publications = 7 points
    - Tier 3: Press releases, company blogs = 3 points
    """
    sources = {}

    for event in events:
        source = event.source

        # Categorize source (simple heuristic)
        if any(outlet in source for outlet in ['techcrunch', 'bloomberg', 'wsj', 'reuters']):
            tier = 'tier1'
            points = 10
        elif any(outlet in source for outlet in ['theverge', 'apnews', 'cnbc']):
            tier = 'tier2'
            points = 7
        else:
            tier = 'tier3'
            points = 3

        # Only count once per tier (avoid duplicate tier inflation)
        if tier not in sources:
            sources[tier] = points

    return sum(sources.values())
```

**Why**: 5 TechCrunch articles worth more than 5 company press releases

---

### Phase 3: Advanced (Future Enhancements)

#### 3.1 Machine Learning Calibration ⭐⭐⭐⭐
**Learn optimal weights from historical data**

**Approach**:
1. Track lead outcomes (did they actually change office space?)
2. Train logistic regression or gradient boosting model
3. Features: event types, signal types, timing, company size
4. Learn which combinations best predict actual office changes

**Requirements**:
- Historical outcome data (ground truth labels)
- 100+ labeled examples minimum
- Periodic retraining

**Example Framework**:
```python
from sklearn.ensemble import GradientBoostingClassifier

# Features
X = [
    [event_type_encoded, signal_count, days_since_event, funding_amount, ...],
    ...
]

# Labels (1 = office change, 0 = no change)
y = [1, 0, 1, 1, 0, ...]

model = GradientBoostingClassifier()
model.fit(X, y)

# Use model predictions as scores
score = model.predict_proba(features)[0][1] * 100
```

---

#### 3.2 Location-Based Scoring ⭐⭐
**Different locations have different office market dynamics**

```python
def _get_location_multiplier(self, city: str, state: str) -> float:
    """
    High-demand office markets = higher value leads.

    Tier 1 markets (SF, NYC, London): 1.3x
    Tier 2 markets (Austin, Seattle, Boston): 1.2x
    Other: 1.0x
    """
    tier1_cities = ['San Francisco', 'New York', 'London', 'Singapore']
    tier2_cities = ['Austin', 'Seattle', 'Boston', 'Los Angeles', 'Chicago']

    if city in tier1_cities:
        return 1.3
    elif city in tier2_cities:
        return 1.2
    else:
        return 1.0
```

**Why**: Office space changes in SF are higher value than small markets

---

#### 3.3 Temporal Momentum ⭐⭐
**Multiple events in short timeframe = higher urgency**

```python
def _calculate_momentum_score(self, events: List[Event]) -> int:
    """
    Reward rapid succession of events (indicates momentum).

    3+ events in 30 days = +15 points
    2 events in 30 days = +5 points
    """
    recent_events = [
        e for e in events
        if (datetime.utcnow() - (e.event_time or e.ingest_time)).days <= 30
    ]

    if len(recent_events) >= 3:
        return 15
    elif len(recent_events) >= 2:
        return 5
    else:
        return 0
```

**Why**: Rapid changes indicate higher urgency and likelihood of action

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Implement exponential time decay
- [ ] Apply confidence multiplier to scores
- [ ] Add unit tests for new decay function

### Week 2: Signal Intelligence
- [ ] Add signal co-occurrence detection
- [ ] Implement combination multipliers
- [ ] Test on historical data

### Week 3: Entity Context
- [ ] Add entity size estimation
- [ ] Implement size-based multipliers
- [ ] Improve source diversity scoring

### Week 4: Validation
- [ ] Compare old vs new scores on test set
- [ ] Tune multiplier values
- [ ] Document changes and rationale

### Future: ML Pipeline
- [ ] Collect outcome labels
- [ ] Build feature extraction pipeline
- [ ] Train ML model
- [ ] A/B test ML scores vs rule-based

---

## Expected Impact

| Improvement | Effort | Impact | Priority |
|------------|--------|--------|----------|
| Exponential decay | Low | High | ⭐⭐⭐ |
| Confidence multiplier | Low | High | ⭐⭐⭐ |
| Signal co-occurrence | Medium | High | ⭐⭐⭐ |
| Entity size normalization | Medium | Medium | ⭐⭐ |
| Source quality tiers | Medium | Medium | ⭐⭐ |
| Location multipliers | Low | Medium | ⭐⭐ |
| Temporal momentum | Low | Medium | ⭐⭐ |
| ML calibration | High | Very High | ⭐⭐⭐⭐ (future) |

---

## Key Principles (Research-Backed)

1. **Exponential Decay**: Information half-life research (Ebbinghaus, 1885; Bates, 2002)
2. **Confidence Weighting**: Bayesian updating principles
3. **Signal Correlation**: Joint probability > individual probabilities (conditional independence)
4. **Feature Engineering**: Domain knowledge beats pure ML (Domingos, 2012)
5. **Iterative Improvement**: Start simple, validate, then add complexity

---

## Next Steps

**Immediate (Do Now)**:
1. Implement exponential time decay (30 min)
2. Apply confidence multiplier (15 min)
3. Test on existing data (30 min)

**Short-term (This Week)**:
4. Add signal co-occurrence multipliers (2 hours)
5. Implement entity size heuristics (2 hours)

**Long-term (Next Month)**:
6. Set up outcome tracking system
7. Collect labeled training data
8. Build ML scoring pipeline

Would you like me to implement any of these improvements?
