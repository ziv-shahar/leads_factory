"""Location-based lead scoring and materialization."""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
from statistics import mean

from src.db.models import Entity, Event, LocationLead
from src.config import SCORING_TIME_DECAY_DAYS


class LocationLeadScorer:
    """Score leads per (entity + state) based on events in that location."""

    def __init__(self, time_decay_days: int = None):
        """
        Initialize location-based scorer.

        Args:
            time_decay_days: Days for time decay (older events score less)
        """
        self.time_decay_days = time_decay_days or SCORING_TIME_DECAY_DAYS

        # Event type scoring rules (same as regular scorer)
        self.event_scores = {
            "funding_round": 20,
            "acquisition": 18,
            "hiring_surge": 15,
            "layoffs": 15,
            "expansion": 18,  # Direct office space signal - increased from 15
            "contraction": 12,  # Building demolition, downsizing
            "market_entry": 12,
            "product_launch": 3,  # Reduced from 12 - rarely indicates office needs
            "partnership": 10,  # Keep at 10 since we're now filtering to only physical partnerships
            "leadership_change": 6,  # Reduced from 8 - weak signal
            "contract_awarded": 10,
            "permit_issued": 5,
            "technology_adoption": 2,  # Reduced from 7 - almost never indicates office needs
            "award_recognition": 2,  # Reduced from 5 - not predictive
            "compliance_issue": 5,
            "other": 3  # Reduced from 5
        }

        # Dynamic signal scoring
        self.signal_scores = {
            "acquisition_negotiation": 15,
            "office_expansion": 12,
            "office_downsizing": 12,
            "office_consolidation": 12,
            "office_relocation_urgent": 15,  # Building demolition
            "office_closure": 10,
            "international_expansion": 12,
            "government_expansion": 10,
            "government_lease_opportunity": 10,
            "employee_growth": 10,
            "market_expansion": 10,
            "remote_work_transition": 8,
            "hq_expansion": 12,
        }

    def score_and_materialize_location_lead(
        self,
        db: Session,
        entity: Entity,
        state: str,
        city: Optional[str] = None
    ) -> Optional[LocationLead]:
        """
        Score entity's activities in a specific state and materialize LocationLead.

        Args:
            db: Database session
            entity: Entity to score
            state: 2-letter state code (normalized)
            city: Optional city name (most significant city for this entity in the state)

        Returns:
            LocationLead record or None if no events in this state
        """
        # Get all events for this entity in this state
        events = db.query(Event).filter(
            Event.entity_id == entity.id
        ).all()

        # Filter events by state (check key_facts.state)
        # Also filter out "completed" events - we only want planned/in_progress
        state_events = []
        for event in events:
            event_state = event.strict.get("key_facts", {}).get("state")
            temporal_status = event.strict.get("temporal_status", "completed")

            # Only include events in this state that are planned or in_progress
            # Skip completed events (already happened - not predictive)
            if event_state == state and temporal_status in ["planned", "in_progress"]:
                state_events.append(event)

        if not state_events:
            # No planned/in_progress events in this state - don't create LocationLead
            return None

        # Group events by (event_type, date) to avoid duplicate inflation
        event_groups = defaultdict(list)
        for event in state_events:
            event_date = (event.event_time or event.ingest_time).date()
            key = (event.event_type, event_date)
            event_groups[key].append(event)

        # Calculate score with deduplication
        total_score = 0
        confidence_scores = []
        reasons_dict = {}
        latest_event_date = None

        for (event_type, event_date), duplicate_events in event_groups.items():
            # Calculate score for each duplicate event in this group
            group_event_scores = []
            group_signal_scores = []

            for event in duplicate_events:
                # Base score from event type
                event_score = self.event_scores.get(event.event_type, 0)

                # Apply time decay and confidence multiplier
                event_time = event.event_time or event.ingest_time
                decay_multiplier = self._calculate_time_decay(event_time)
                confidence = event.extraction_confidence
                decayed_score = event_score * decay_multiplier * confidence

                group_event_scores.append(decayed_score)
                confidence_scores.append(confidence)

                # Update latest event date
                if not latest_event_date or event_time > latest_event_date:
                    latest_event_date = event_time

                # Score dynamic signals
                event_signal_score = 0
                for signal in event.dynamic_signals:
                    signal_type = signal.get("signal_type", "")
                    signal_score = self.signal_scores.get(signal_type, 3)
                    signal_score = signal_score * decay_multiplier * confidence
                    event_signal_score += signal_score

                group_signal_scores.append(event_signal_score)

            # Average scores for this group (deduplication)
            avg_event_score = mean(group_event_scores)
            avg_signal_score = mean(group_signal_scores) if group_signal_scores else 0
            group_total_score = int(avg_event_score + avg_signal_score)

            total_score += group_total_score

            # Build reasons dict
            if group_total_score != 0:
                if event_type not in reasons_dict:
                    reasons_dict[event_type] = {
                        "count": 0,
                        "score": 0
                    }
                reasons_dict[event_type]["count"] += 1
                reasons_dict[event_type]["score"] += group_total_score

        # Calculate overall confidence
        overall_confidence = mean(confidence_scores) if confidence_scores else 0.0

        # Determine status based on score
        if total_score >= 25:
            status = "NEW"  # High value lead
        elif total_score >= 10:
            status = "NEW"
        else:
            status = "NEW"

        # Find most significant city if not provided
        if not city:
            city = self._find_most_significant_city(state_events)

        # Create or update LocationLead
        location_lead = db.query(LocationLead).filter(
            LocationLead.entity_id == entity.id,
            LocationLead.state == state
        ).first()

        if location_lead:
            # Update existing
            location_lead.score = total_score
            location_lead.confidence_score = overall_confidence
            location_lead.status = status
            location_lead.event_count = len(state_events)
            location_lead.reasons = reasons_dict
            location_lead.last_event_date = latest_event_date
            location_lead.last_updated_at = datetime.utcnow()
            if city:
                location_lead.city = city
        else:
            # Create new
            location_lead = LocationLead(
                entity_id=entity.id,
                state=state,
                city=city,
                score=total_score,
                confidence_score=overall_confidence,
                status=status,
                event_count=len(state_events),
                reasons=reasons_dict,
                last_event_date=latest_event_date
            )
            db.add(location_lead)

        return location_lead

    def _calculate_time_decay(self, event_time: datetime) -> float:
        """Calculate time decay multiplier (0.0 to 1.0)."""
        age_days = (datetime.utcnow() - event_time).days

        if age_days <= 0:
            return 1.0  # Future or today = full weight

        # Linear decay over time_decay_days
        # e.g., if decay_days = 365:
        #   0 days old = 1.0
        #   182 days old = 0.5
        #   365+ days old = 0.0
        decay = max(0.0, 1.0 - (age_days / self.time_decay_days))
        return decay

    def _find_most_significant_city(self, events: list) -> Optional[str]:
        """
        Find the most significant city from events.

        Uses the city from the most recent event.
        """
        if not events:
            return None

        # Sort by event time (most recent first)
        sorted_events = sorted(
            events,
            key=lambda e: e.event_time or e.ingest_time,
            reverse=True
        )

        # Get city from most recent event
        for event in sorted_events:
            city = event.strict.get("key_facts", {}).get("city")
            if city:
                return city

        return None
