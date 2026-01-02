"""End-to-end pipeline orchestrator."""
import hashlib
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from src.config import RAW_DATA_BUCKET
from src.db.session import get_db
from src.db.models import RawEvent, Entity, Event, LeadCurrent
from src.io.raw_reader import RawFileReader
from src.llm.normalizer import Normalizer, compute_content_hash
from src.llm.schemas import get_normalized_name
from src.enrich.enricher import Enricher
from src.resolve.resolver import EntityResolver
from src.resolve.canonicalize import canonicalize_company_name
from src.scoring.scorer import LeadScorer


class PipelineRunner:
    """Orchestrate the full lead intelligence pipeline."""

    def __init__(self):
        self.reader = RawFileReader(str(RAW_DATA_BUCKET))
        self.normalizer = Normalizer()
        self.enricher = Enricher()
        self.resolver = EntityResolver()
        self.scorer = LeadScorer()

    def run(self):
        """Run the complete pipeline."""
        print("\n" + "="*80)
        print("LEAD INTELLIGENCE PIPELINE - STARTING")
        print("="*80 + "\n")

        with get_db() as db:
            # Phase 1: Discover and dedupe raw files
            print("Phase 1: Discovering raw files...")
            files = self.reader.list_files()
            print(f"✓ Found {len(files)} files in {RAW_DATA_BUCKET}\n")

            if not files:
                print("⚠ No files to process. Exiting.")
                return

            # Phase 2: Process each file
            for file_path in files:
                print("-" * 80)
                print(f"Processing: {file_path}")
                print("-" * 80)

                try:
                    self._process_file(db, file_path)
                except Exception as e:
                    print(f"✗ Error processing {file_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()

                print()

            # Commit all changes
            db.commit()

            # Phase 3: Print summary
            print("\n" + "="*80)
            print("PIPELINE SUMMARY")
            print("="*80)
            self._print_summary(db)

    def _process_file(self, db: Session, file_path: str):
        """Process a single file through the pipeline."""
        # Read file
        content, file_type = self.reader.read_file(file_path)
        print(f"✓ Read file ({file_type}): {len(content)} chars")

        # Check if already processed (deduplication)
        content_hash = compute_content_hash(content)
        existing = db.query(RawEvent).filter(RawEvent.content_hash == content_hash).first()

        if existing:
            if existing.status == "PROCESSED":
                print(f"⊙ File already processed (hash: {content_hash[:8]}...), skipping")
                return
            else:
                print(f"⊙ File exists but not processed, reprocessing...")
                raw_event = existing
        else:
            # Create raw event record
            raw_event = RawEvent(
                source="local_bucket",
                file_path=file_path,
                content_hash=content_hash,
                status="NEW"
            )
            db.add(raw_event)
            db.flush()

        # Normalize (extract event)
        print("→ Normalizing document with LLM...")
        normalized_event = self.normalizer.normalize_document(
            content=content,
            file_path=file_path,
            source="local_bucket"
        )

        if not normalized_event:
            raw_event.status = "FAILED"
            raw_event.error = "Normalization failed"
            print("✗ Normalization failed")
            return

        print(f"✓ Extracted event: {normalized_event.event_type}")
        print(f"  Company: {normalized_event.company_name_raw} -> {normalized_event.company_name_canonical}")
        print(f"  Confidence: {normalized_event.extraction_confidence:.2f}")
        print(f"  Dynamic signals: {len(normalized_event.dynamic_signals)}")

        # Canonicalize name
        canonical_name, normalized_name = canonicalize_company_name(
            normalized_event.company_name_canonical
        )

        # Enrich entity (optional, based on freshness)
        print("→ Checking if enrichment needed...")
        enrichment = None

        # Try to find existing entity to check freshness
        existing_entity = db.query(Entity).filter(
            Entity.canonical_name == canonical_name
        ).first()

        should_enrich = self.enricher.should_enrich(
            entity_domain=existing_entity.domain if existing_entity else None,
            last_enriched_at=existing_entity.last_enriched_at if existing_entity else None,
            missing_fields=["domain"] if not existing_entity or not existing_entity.domain else []
        )

        if should_enrich:
            print("→ Enriching entity...")
            enrichment = self.enricher.enrich_entity(
                canonical_name=canonical_name,
                alternative_names=[normalized_event.company_name_raw]
            )
        else:
            print("⊙ Enrichment not needed (recent or has domain)")

        # Resolve entity (dedupe)
        print("→ Resolving entity...")
        entity = self.resolver.resolve_or_create_entity(
            db=db,
            canonical_name=canonical_name,
            normalized_name=normalized_name,
            enrichment=enrichment
        )
        db.flush()

        # Create event record
        print("→ Persisting event...")
        event = Event(
            entity_id=entity.id,
            source="local_bucket",
            event_type=normalized_event.event_type,
            event_time=self._parse_date(normalized_event.event_date),
            strict={
                "company_name_raw": normalized_event.company_name_raw,
                "company_name_canonical": normalized_event.company_name_canonical,
                "summary": normalized_event.summary,
                "key_facts": normalized_event.key_facts.model_dump() if normalized_event.key_facts else {},
                "source_url": normalized_event.source_url,
                "missing_fields": normalized_event.missing_fields
            },
            dynamic_signals=[s.model_dump() for s in normalized_event.dynamic_signals],
            extraction_confidence=normalized_event.extraction_confidence,
            raw_ref=file_path
        )
        db.add(event)
        db.flush()
        print(f"✓ Event persisted: {event.id}")

        # Score and materialize lead
        print("→ Scoring lead...")
        lead = self.scorer.score_and_materialize_lead(db, entity)
        db.flush()

        # Mark raw event as processed
        raw_event.status = "PROCESSED"
        print(f"✓ File processing complete")

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        if not date_str:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback: return None
        return None

    def _print_summary(self, db: Session):
        """Print pipeline summary."""
        # Counts
        entity_count = db.query(Entity).count()
        event_count = db.query(Event).count()
        lead_count = db.query(LeadCurrent).count()
        raw_processed = db.query(RawEvent).filter(RawEvent.status == "PROCESSED").count()
        raw_failed = db.query(RawEvent).filter(RawEvent.status == "FAILED").count()

        print(f"\nCounts:")
        print(f"  Entities: {entity_count}")
        print(f"  Events: {event_count}")
        print(f"  Leads: {lead_count}")
        print(f"  Raw files processed: {raw_processed}")
        print(f"  Raw files failed: {raw_failed}")

        # List entities with their leads
        print(f"\n{'Entity Details':=^80}")
        entities = db.query(Entity).all()

        for entity in entities:
            print(f"\n{entity.canonical_name}")
            print(f"  ID: {entity.id}")
            print(f"  Normalized: {entity.normalized_name}")
            print(f"  Domain: {entity.domain or 'N/A'}")
            print(f"  Website: {entity.website_url or 'N/A'}")
            print(f"  LinkedIn: {entity.linkedin_url or 'N/A'}")
            print(f"  HQ: {entity.hq_location or 'N/A'}")

            # Events
            events = db.query(Event).filter(Event.entity_id == entity.id).all()
            print(f"\n  Events ({len(events)}):")
            for event in events:
                print(f"    • {event.event_type}: {event.strict.get('summary', 'N/A')[:80]}")
                print(f"      Confidence: {event.extraction_confidence:.2f}, Signals: {len(event.dynamic_signals)}")

            # Lead
            lead = db.query(LeadCurrent).filter(LeadCurrent.entity_id == entity.id).first()
            if lead:
                print(f"\n  Lead Score: {lead.score}")
                print(f"  Confidence: {lead.confidence_score:.2f}")
                print(f"  Status: {lead.status}")
                print(f"  Reasons breakdown ({len(lead.reasons.get('breakdown', []))}):")
                for reason in lead.reasons.get('breakdown', [])[:5]:  # Top 5
                    print(f"    • {reason.get('event_type', reason.get('type', 'N/A'))}: "
                          f"+{reason.get('score_contribution', 0)}")

            print("-" * 80)

        print("\n" + "="*80)
        print("PIPELINE COMPLETE")
        print("="*80 + "\n")
