"""Lead scoring and materialization."""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

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

        # Event type scoring rules (generic, adjust for your domain)
        self.event_scores = {
            "funding_round": 20,
            "partnership": 10,
            "expansion": 15,
            "product_launch": 12,
            "acquisition": 18,
            "hiring_surge": 15,
            "leadership_change": 8,
            "award_recognition": 5,
            "technology_adoption": 7,
            "market_entry": 12,
            "layoffs": -10,
            "compliance_issue": -15,
            "other": 5
        }

        # Dynamic signal scoring
        self.signal_scores = {
            "acquisition_negotiation": 15,
            "government_expansion": 10,
            "new_product_line": 8,
            "international_expansion": 12,
            "office_expansion": 7,
            "patent_filing": 6,
            "customer_growth": 8,
            "employee_growth": 10,
            "market_expansion": 10,
            "engineering_capacity_buildup": 8,
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
        events = db.query(Event).filter(Event.entity_id == entity.id).all()

        if not events:
            # No events = minimal lead
            return self._create_or_update_lead(
                db, entity,
                score=0,
                confidence=0.0,
                status="NEW",
                reasons={"reason": "No events found for this entity"}
            )

        # Calculate score
        total_score = 0
        confidence_scores = []
        reasons = []
        evidence_events = []

        for event in events:
            # Base score from event type
            event_score = self.event_scores.get(event.event_type, 0)

            # Apply time decay
            decay_multiplier = self._calculate_time_decay(event.event_time or event.ingest_time)
            decayed_score = int(event_score * decay_multiplier)

            # Add to total
            total_score += decayed_score

            # Track confidence
            confidence_scores.append(event.extraction_confidence)

            # Build reason
            if decayed_score != 0:
                age_days = (datetime.utcnow() - (event.event_time or event.ingest_time)).days
                reasons.append({
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "summary": event.strict.get("summary", "No summary"),
                    "score_contribution": decayed_score,
                    "age_days": age_days,
                    "source": event.source
                })
                evidence_events.append(str(event.id))

            # Score dynamic signals
            for signal in event.dynamic_signals:
                signal_type = signal.get("signal_type", "")
                signal_score = self.signal_scores.get(signal_type, 3)  # Default +3
                signal_score = int(signal_score * decay_multiplier)

                total_score += signal_score

                if signal_score > 0:
                    reasons.append({
                        "event_id": str(event.id),
                        "type": "dynamic_signal",
                        "signal_type": signal_type,
                        "description": signal.get("description", ""),
                        "score_contribution": signal_score
                    })

        # Calculate aggregate confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Bonus for multiple independent sources
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
