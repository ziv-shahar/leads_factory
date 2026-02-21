"""Lead scoring and materialization."""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
from statistics import mean

from src.db.models import Entity, Event, LeadCurrent, LeadStateHistory
from src.config import SCORING_TIME_DECAY_DAYS


class LeadScorer:
    """Score leads based on events and signals."""

    def __init__(self, time_decay_days: int = None):
        """
        Initialize scorer.

        Args:
            time_decay_days: Days for time decay (older events score less)
        """
        self.time_decay_days = time_decay_days or SCORING_TIME_DECAY_DAYS

        # Event type scoring rules for OFFICE SPACE PREDICTION
        # Both expansion and downsizing indicate office space changes = valuable leads
        self.event_scores = {
            "funding_round": 20,          # Strong expansion signal
            "acquisition": 18,             # Office integration/consolidation
            "hiring_surge": 15,            # Expansion signal
            "layoffs": 15,                 # Downsizing signal (equally valuable!)
            "expansion": 15,               # Direct expansion signal
            "market_entry": 12,            # Potential new offices
            "product_launch": 12,          # May indicate growth
            "partnership": 10,             # Potential co-location
            "leadership_change": 8,        # May drive changes
            "technology_adoption": 7,      # Infrastructure changes
            "award_recognition": 5,        # Weak signal
            "compliance_issue": 5,       # Risk signal (not office-related)
            "other": 5
        }

        # Dynamic signal scoring for OFFICE SPACE PREDICTION
        # Both expansion and downsizing signals are positive
        self.signal_scores = {
            "acquisition_negotiation": 15,
            "office_expansion": 12,              # Direct office expansion
            "office_downsizing": 12,             # Direct office downsizing (positive!)
            "office_consolidation": 12,          # Office changes (positive!)
            "office_closure": 10,                # Office closure = relocation need
            "office_integration": 10,            # Post-acquisition integration
            "international_expansion": 12,
            "employee_growth": 10,
            "employee_relocation": 10,           # Relocation = office changes
            "government_expansion": 10,
            "market_expansion": 10,
            "remote_work_transition": 8,         # May reduce office needs (still valuable signal)
            "hq_expansion": 12,                  # HQ expansion
            "customer_growth": 8,
            "engineering_capacity_buildup": 8,
            "hiring_surge": 10,                  # As dynamic signal
            "new_product_line": 8,
            "patent_filing": 6,
        }

    def score_and_materialize_lead(self, db: Session, entity: Entity) -> LeadCurrent:
        """
        Score entity and materialize lead state.

        Args:
            db: Database session
            entity: Entity to score

        Returns:
            LeadCurrent record
        """
        # Get all events for this entity
        all_events = db.query(Event).filter(Event.entity_id == entity.id).all()

        # Filter out "completed" events - we only want planned/in_progress for predictive leads
        # Skip events that already happened (not predictive of future space needs)
        events = []
        for event in all_events:
            temporal_status = event.strict.get("temporal_status", "completed")
            if temporal_status in ["planned", "in_progress"]:
                events.append(event)

        if not events:
            # No planned/in_progress events = minimal lead
            return self._create_or_update_lead(
                db, entity,
                score=0,
                confidence=0.0,
                status="NEW",
                reasons={"reason": "No planned or in-progress events found for this entity"}
            )

        # Group events by (event_type, date) to avoid duplicate event inflation
        # Multiple articles about same event on same day should be averaged, not summed
        event_groups = defaultdict(list)
        for event in events:
            event_date = (event.event_time or event.ingest_time).date()
            key = (event.event_type, event_date)
            event_groups[key].append(event)

        # Calculate score with deduplication
        total_score = 0
        confidence_scores = []
        reasons = []
        evidence_events = []

        for (event_type, event_date), duplicate_events in event_groups.items():
            # Calculate score for each duplicate event in this group
            group_event_scores = []
            group_signal_scores = []

            for event in duplicate_events:
                # Base score from event type
                event_score = self.event_scores.get(event.event_type, 0)

                # Apply time decay and confidence multiplier
                decay_multiplier = self._calculate_time_decay(event.event_time or event.ingest_time)
                confidence = event.extraction_confidence
                decayed_score = event_score * decay_multiplier * confidence

                group_event_scores.append(decayed_score)

                # Track confidence for aggregate
                confidence_scores.append(confidence)

                # Score dynamic signals for this event
                event_signal_score = 0
                for signal in event.dynamic_signals:
                    signal_type = signal.get("signal_type", "")
                    signal_score = self.signal_scores.get(signal_type, 3)  # Default +3
                    # Apply both time decay and confidence to signals
                    signal_score = signal_score * decay_multiplier * confidence
                    event_signal_score += signal_score

                group_signal_scores.append(event_signal_score)

                evidence_events.append(str(event.id))

            # Average the scores for this group (deduplication)
            avg_event_score = mean(group_event_scores)
            avg_signal_score = mean(group_signal_scores) if group_signal_scores else 0
            group_total_score = int(avg_event_score + avg_signal_score)

            total_score += group_total_score

            # Build reason for this group
            if group_total_score != 0:
                # Use the first event as representative
                representative_event = duplicate_events[0]
                age_days = (datetime.utcnow() - (representative_event.event_time or representative_event.ingest_time)).days

                reason_entry = {
                    "event_type": event_type,
                    "event_date": str(event_date),
                    "summary": representative_event.strict.get("summary", "No summary"),
                    "score_contribution": group_total_score,
                    "age_days": age_days,
                    "duplicate_count": len(duplicate_events),
                    "sources": [e.source for e in duplicate_events]
                }

                if len(duplicate_events) > 1:
                    reason_entry["note"] = f"Averaged {len(duplicate_events)} duplicate events"

                reasons.append(reason_entry)

        # Calculate aggregate confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Bonus for multiple independent sources (still valuable even with deduplication)
        unique_sources = len(set(e.source for e in events))
        if unique_sources > 1:
            source_bonus = (unique_sources - 1) * 5
            total_score += source_bonus
            reasons.append({
                "type": "source_diversity",
                "description": f"Multiple independent sources ({unique_sources})",
                "score_contribution": source_bonus
            })

        # Determine status
        status = self._determine_status(total_score, events)

        # Build final reasons object
        final_reasons = {
            "total_score": total_score,
            "confidence": round(avg_confidence, 2),
            "event_count": len(events),
            "unique_event_groups": len(event_groups),  # Number of unique events after deduplication
            "unique_sources": unique_sources,
            "evidence_events": evidence_events,
            "breakdown": sorted(reasons, key=lambda x: x.get("score_contribution", 0), reverse=True)
        }

        # Create or update lead
        return self._create_or_update_lead(
            db, entity,
            score=total_score,
            confidence=avg_confidence,
            status=status,
            reasons=final_reasons
        )

    def _calculate_time_decay(self, event_date: datetime) -> float:
        """
        Calculate time decay multiplier.

        Args:
            event_date: When event occurred

        Returns:
            Decay multiplier (0.0 - 1.0)
        """
        if not event_date:
            return 0.5  # Unknown date = medium decay

        age_days = (datetime.utcnow() - event_date).days

        if age_days < 0:
            return 1.0  # Future event (shouldn't happen)
        elif age_days <= 30:
            return 1.0  # Recent event, full score
        elif age_days <= self.time_decay_days:
            # Linear decay from 1.0 to 0.3 over time_decay_days
            decay = 1.0 - (0.7 * (age_days - 30) / (self.time_decay_days - 30))
            return max(0.3, decay)
        else:
            return 0.3  # Very old event, 30% score

    def _determine_status(self, score: int, events: List[Event]) -> str:
        """Determine lead status based on score and recency."""
        if not events:
            return "NEW"

        # Check recency of latest event
        latest_event = max(events, key=lambda e: e.event_time or e.ingest_time)
        days_since_latest = (datetime.utcnow() - (latest_event.event_time or latest_event.ingest_time)).days

        if score >= 50:
            return "ACTIVE"
        elif score >= 20:
            return "NEW"
        elif days_since_latest > 180:
            return "STALE"
        else:
            return "NEW"

    def _create_or_update_lead(
        self,
        db: Session,
        entity: Entity,
        score: int,
        confidence: float,
        status: str,
        reasons: Dict[str, Any]
    ) -> LeadCurrent:
        """Create or update lead in leads_current table."""
        # Check if lead exists
        lead = db.query(LeadCurrent).filter(LeadCurrent.entity_id == entity.id).first()

        if lead:
            # Update existing lead
            old_score = lead.score
            lead.score = score
            lead.confidence_score = confidence
            lead.status = status
            lead.reasons = reasons
            lead.last_updated_at = datetime.utcnow()

            print(f"  ✓ Updated lead: score {old_score} -> {score}, status={status}")

            # Append to history
            self._append_history(db, entity.id, score, confidence, status, reasons)
        else:
            # Create new lead
            lead = LeadCurrent(
                entity_id=entity.id,
                score=score,
                confidence_score=confidence,
                status=status,
                reasons=reasons
            )
            db.add(lead)

            print(f"  ✓ Created lead: score={score}, status={status}")

            # Initial history entry
            self._append_history(db, entity.id, score, confidence, status, reasons)

        return lead

    def _append_history(
        self,
        db: Session,
        entity_id: int,
        score: int,
        confidence: float,
        status: str,
        reasons: Dict[str, Any]
    ):
        """Append entry to lead state history."""
        history_entry = LeadStateHistory(
            entity_id=entity_id,
            score=score,
            confidence_score=confidence,
            status=status,
            reasons=reasons
        )
        db.add(history_entry)
