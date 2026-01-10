"""Entity resolution with domain-first matching."""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from src.db.models import Entity
from src.resolve.canonicalize import canonicalize_company_name, extract_domain_from_url
from src.llm.schemas import EnrichmentResult


class EntityResolver:
    """Resolve entity names to canonical entities with deduplication - works for all entity types."""

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
        entity_type: Optional[str] = None,
        entity_metadata: Optional[Dict[str, Any]] = None,
        enrichment: Optional[EnrichmentResult] = None
    ) -> Entity:
        """
        Resolve entity using domain-first matching, or create new entity.

        Resolution strategy:
        1. If enrichment has domain -> lookup by domain
        2. If entity_metadata has domain -> lookup by domain
        3. Else exact match on canonical_name
        4. Else fuzzy match on normalized_name
        5. Else create new entity

        Args:
            db: Database session
            canonical_name: Canonical entity name
            normalized_name: Normalized name (alphanumeric only)
            entity_type: Optional entity type (company, government_agency, etc.)
            entity_metadata: Optional entity metadata from extraction
            enrichment: Optional enrichment data

        Returns:
            Existing or newly created Entity
        """
        # Strategy 1: Domain-first matching (most reliable) - from enrichment
        if enrichment and enrichment.domain:
            domain = extract_domain_from_url(enrichment.domain)
            if domain:
                entity = db.query(Entity).filter(Entity.domain == domain).first()
                if entity:
                    print(f"  ✓ Matched entity by domain: {domain} -> {entity.canonical_name}")
                    # Update enrichment fields if we have new data
                    self._update_entity_enrichment(entity, entity_type, entity_metadata, enrichment)
                    return entity

        # Strategy 1b: Domain from entity_metadata (from extraction)
        if entity_metadata:
            domain_from_metadata = (
                entity_metadata.get('domain') or
                entity_metadata.get('gov_domain') or
                entity_metadata.get('official_domain')
            )
            if domain_from_metadata:
                domain = extract_domain_from_url(domain_from_metadata)
                if domain:
                    entity = db.query(Entity).filter(Entity.domain == domain).first()
                    if entity:
                        print(f"  ✓ Matched entity by domain (from metadata): {domain} -> {entity.canonical_name}")
                        self._update_entity_enrichment(entity, entity_type, entity_metadata, enrichment)
                        return entity

        # Strategy 2: Exact canonical name match
        entity = db.query(Entity).filter(Entity.canonical_name == canonical_name).first()
        if entity:
            print(f"  ✓ Matched entity by canonical name: {canonical_name}")
            # Update enrichment if we have new data
            self._update_entity_enrichment(entity, entity_type, entity_metadata, enrichment)
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

                    self._update_entity_enrichment(candidate, entity_type, entity_metadata, enrichment)
                    return candidate

        # Strategy 4: Create new entity
        print(f"  ✓ Creating new entity: {canonical_name}")
        entity = Entity(
            canonical_name=canonical_name,
            normalized_name=normalized_name,
            entity_type=entity_type,
            metadata=entity_metadata or {}
        )

        if enrichment:
            self._update_entity_enrichment(entity, entity_type, entity_metadata, enrichment)

        db.add(entity)
        db.flush()  # Get entity.id without committing

        return entity

    def _update_entity_enrichment(
        self,
        entity: Entity,
        entity_type: Optional[str],
        entity_metadata: Optional[Dict[str, Any]],
        enrichment: Optional[EnrichmentResult]
    ):
        """Update entity with enrichment data and extracted metadata."""
        from datetime import datetime

        updated = False

        # Update entity type if provided and not already set
        if entity_type and not entity.entity_type:
            entity.entity_type = entity_type
            updated = True

        # Merge entity_metadata from extraction
        if entity_metadata:
            if entity.metadata is None:
                entity.metadata = {}
            for key, value in entity_metadata.items():
                if value is not None and key not in entity.metadata:
                    entity.metadata[key] = value
                    updated = True

        # Update domain from enrichment (only if not already set)
        if enrichment and enrichment.domain and not entity.domain:
            entity.domain = extract_domain_from_url(enrichment.domain)
            updated = True

        # Merge enrichment metadata
        if enrichment and enrichment.metadata:
            if entity.metadata is None:
                entity.metadata = {}
            for key, value in enrichment.metadata.items():
                if value is not None and key not in entity.metadata:
                    entity.metadata[key] = value
                    updated = True

        # Update enrichment timestamp
        if updated and enrichment:
            entity.last_enriched_at = datetime.utcnow()
            print(f"    Enriched entity with: domain={entity.domain}, metadata_keys={list(entity.metadata.keys())}")
