"""Entity resolution with domain-first matching."""
from typing import Optional
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from src.db.models import Entity
from src.resolve.canonicalize import canonicalize_company_name, extract_domain_from_url
from src.llm.schemas import EnrichmentResult


class EntityResolver:
    """Resolve company names to canonical entities with deduplication."""

    def __init__(self, fuzzy_threshold: int = 85):
        """
        Initialize resolver.

        Args:
            fuzzy_threshold: Minimum fuzzy match score (0-100) for name matching
        """
        self.fuzzy_threshold = fuzzy_threshold

    def resolve_or_create_entity(
        self,
        db: Session,
        canonical_name: str,
        normalized_name: str,
        enrichment: Optional[EnrichmentResult] = None
    ) -> Entity:
        """
        Resolve entity using domain-first matching, or create new entity.

        Resolution strategy:
        1. If enrichment has domain -> lookup by domain
        2. Else exact match on canonical_name
        3. Else fuzzy match on normalized_name
        4. Else create new entity

        Args:
            db: Database session
            canonical_name: Canonical company name
            normalized_name: Normalized name (alphanumeric only)
            enrichment: Optional enrichment data

        Returns:
            Existing or newly created Entity
        """
        # Strategy 1: Domain-first matching (most reliable)
        if enrichment and enrichment.official_domain:
            domain = extract_domain_from_url(enrichment.official_domain)
            if domain:
                entity = db.query(Entity).filter(Entity.domain == domain).first()
                if entity:
                    print(f"  ✓ Matched entity by domain: {domain} -> {entity.canonical_name}")
                    # Update enrichment fields if we have new data
                    self._update_entity_enrichment(entity, enrichment)
                    return entity

        # Strategy 2: Exact canonical name match
        entity = db.query(Entity).filter(Entity.canonical_name == canonical_name).first()
        if entity:
            print(f"  ✓ Matched entity by canonical name: {canonical_name}")
            # Update enrichment if we have new data
            if enrichment:
                self._update_entity_enrichment(entity, enrichment)
            return entity

        # Strategy 3: Fuzzy match on normalized name
        if normalized_name:
            similar_entities = db.query(Entity).filter(
                Entity.normalized_name.like(f"{normalized_name[:3]}%")  # Prefix filter for performance
            ).all()

            for candidate in similar_entities:
                score = fuzz.ratio(normalized_name, candidate.normalized_name)
                if score >= self.fuzzy_threshold:
                    print(f"  ✓ Fuzzy matched entity: {canonical_name} -> {candidate.canonical_name} (score: {score})")
                    # Update name to canonical if different
                    if candidate.canonical_name != canonical_name:
                        print(f"    Updated canonical name: {candidate.canonical_name} -> {canonical_name}")
                        candidate.canonical_name = canonical_name

                    if enrichment:
                        self._update_entity_enrichment(candidate, enrichment)

                    return candidate

        # Strategy 4: Create new entity
        print(f"  ✓ Creating new entity: {canonical_name}")
        entity = Entity(
            canonical_name=canonical_name,
            normalized_name=normalized_name
        )

        if enrichment:
            self._update_entity_enrichment(entity, enrichment)

        db.add(entity)
        db.flush()  # Get entity.id without committing

        return entity

    def _update_entity_enrichment(self, entity: Entity, enrichment: EnrichmentResult):
        """Update entity with enrichment data."""
        from datetime import datetime

        updated = False

        # Update domain (only if not set or higher confidence)
        if enrichment.official_domain and not entity.domain:
            entity.domain = extract_domain_from_url(enrichment.official_domain)
            updated = True

        # Update website
        if enrichment.website_url and not entity.website_url:
            entity.website_url = enrichment.website_url
            updated = True

        # Update LinkedIn
        if enrichment.linkedin_url and not entity.linkedin_url:
            entity.linkedin_url = enrichment.linkedin_url
            updated = True

        # Update HQ location (city and state)
        if enrichment.hq_city and not entity.hq_city:
            entity.hq_city = enrichment.hq_city
            updated = True
        if enrichment.hq_state and not entity.hq_state:
            entity.hq_state = enrichment.hq_state
            updated = True

        # Update enrichment timestamp
        if updated:
            entity.last_enriched_at = datetime.utcnow()
            print(f"    Enriched entity with: domain={entity.domain}, website={entity.website_url}")
