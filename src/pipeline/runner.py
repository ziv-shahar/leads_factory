"""End-to-end pipeline orchestrator."""
import hashlib
import threading
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from src.config import (
    RAW_DATA_BUCKET, ENRICHMENT_ENABLED, TWO_STAGE_EXTRACTION,
    PARALLEL_PROCESSING, MAX_WORKERS, RATE_LIMIT_REQUESTS_PER_MINUTE,
    BUILDING_PROCESSING_ENABLED
)
from src.db.session import get_db
from src.db.models import RawEvent, Entity, Event, LeadCurrent
from src.io.raw_reader import RawFileReader
from src.llm.normalizer import Normalizer, compute_content_hash
from src.llm.schemas import get_normalized_name
from src.enrich.enricher import Enricher
from src.resolve.resolver import EntityResolver
from src.resolve.canonicalize import canonicalize_company_name
from src.scoring.scorer import LeadScorer
from src.scoring.location_lead_scorer import LocationLeadScorer

# Log directory (created once)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        if self.min_interval == 0:
            return

        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()


class ProgressTracker:
    """Thread-safe progress tracker for parallel processing."""

    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.processed = 0
        self.failed = 0
        self.skipped = 0
        self.lock = threading.Lock()

    def increment_completed(self):
        with self.lock:
            self.completed += 1

    def increment_processed(self):
        with self.lock:
            self.processed += 1

    def increment_failed(self):
        with self.lock:
            self.failed += 1

    def increment_skipped(self):
        with self.lock:
            self.skipped += 1

    def get_status(self):
        with self.lock:
            return {
                'completed': self.completed,
                'processed': self.processed,
                'failed': self.failed,
                'skipped': self.skipped,
                'total': self.total
            }


class PipelineRunner:
    """Orchestrate the full lead intelligence pipeline."""

    def __init__(self):
        self.reader = RawFileReader(str(RAW_DATA_BUCKET))
        self.normalizer = Normalizer()
        self.enricher = Enricher()
        self.resolver = EntityResolver()
        self.scorer = LeadScorer()
        self.location_scorer = LocationLeadScorer()
        self.rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS_PER_MINUTE)

    def run(self):
        """Run the complete pipeline."""
        # Create new log file for this run
        log_file = LOG_DIR / f"pipeline_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Configure logger for this run
        logger = logging.getLogger('pipeline_runner')
        logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        logger.handlers = []

        # Add file handler for this run
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only show warnings/errors in console
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(console_handler)

        # Store logger for use in other methods
        self.logger = logger
        self.log_file = log_file

        print("\n" + "="*80)
        print("LEAD INTELLIGENCE PIPELINE - STARTING")
        if PARALLEL_PROCESSING:
            print(f"MODE: PARALLEL ({MAX_WORKERS} workers)")
        else:
            print("MODE: SEQUENTIAL")
        print(f"ERROR LOG: {log_file}")
        print("="*80 + "\n")

        logger.info("Pipeline started")
        logger.info(f"Mode: {'PARALLEL' if PARALLEL_PROCESSING else 'SEQUENTIAL'}")

        # Phase 1: Discover files (non-recursive, explicit discovery)
        # Discovers: root files, directories with merge.txt, directories with files
        print("Phase 1: Discovering raw files...")
        file_entries = self.reader.list_files_with_merge()

        # Count total files (for display)
        total_files = sum(len(entry['files']) for entry in file_entries)
        print(f"✓ Found {len(file_entries)} entries ({total_files} files) in {RAW_DATA_BUCKET}")

        # Show merge info
        merged_count = sum(1 for e in file_entries if e['type'] == 'merged')
        if merged_count > 0:
            print(f"  → {merged_count} directories with merge.txt will be processed as single documents")
        print()

        if not file_entries:
            print("⚠ No files to process. Exiting.")
            return

        # Phase 2: Process files (parallel or sequential)
        if PARALLEL_PROCESSING:
            self._run_parallel(file_entries)
        else:
            self._run_sequential(file_entries)

        # Phase 3: Print summary
        print("\n" + "="*80)
        print("PIPELINE SUMMARY")
        print("="*80)
        with get_db() as db:
            self._print_summary(db)

    def _run_sequential(self, file_entries: List[dict]):
        """Run pipeline sequentially (original behavior)."""
        with get_db() as db:
            for entry in file_entries:
                print("-" * 80)
                if entry['type'] == 'merged':
                    print(f"Processing MERGED: {entry['path']} ({len(entry['files'])} files)")
                else:
                    print(f"Processing: {entry['path']}")
                print("-" * 80)

                try:
                    self._process_entry(db, entry)
                except Exception as e:
                    display_path = entry['path']
                    print(f"✗ Error processing {display_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()

                print()

            # Commit all changes
            db.commit()

    def _run_parallel(self, file_entries: List[dict]):
        """Run pipeline in parallel using ThreadPoolExecutor."""
        print(f"Phase 2: Processing {len(file_entries)} entries in parallel (max {MAX_WORKERS} workers)...\n")

        progress = ProgressTracker(len(file_entries))
        print_lock = threading.Lock()  # For thread-safe printing

        def process_entry_wrapper(entry: dict) -> dict:
            """Wrapper to process an entry with its own database session."""
            display_path = entry['path']
            result = {
                'path': display_path,
                'status': 'unknown',
                'error': None
            }

            # Each thread gets its own database session
            with get_db() as db:
                try:
                    # Rate limiting
                    self.rate_limiter.wait_if_needed()

                    # Thread-safe printing
                    with print_lock:
                        if entry['type'] == 'merged':
                            print(f"[{progress.completed + 1}/{len(file_entries)}] Processing MERGED: {display_path} ({len(entry['files'])} files)")
                        else:
                            print(f"[{progress.completed + 1}/{len(file_entries)}] Processing: {display_path}")

                    # Process entry
                    status = self._process_entry(db, entry, quiet=True)

                    # Update progress
                    if status == 'skipped':
                        progress.increment_skipped()
                        result['status'] = 'skipped'
                    elif status == 'failed':
                        progress.increment_failed()
                        result['status'] = 'failed'
                    else:
                        progress.increment_processed()
                        result['status'] = 'processed'

                    progress.increment_completed()

                    # Commit this thread's changes
                    db.commit()

                except Exception as e:
                    result['status'] = 'error'
                    result['error'] = str(e)
                    progress.increment_failed()
                    progress.increment_completed()

                    with print_lock:
                        print(f"✗ Error processing {display_path}: {str(e)}")
                        import traceback
                        traceback.print_exc()

            return result

        # Process entries in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_entry_wrapper, entry): entry for entry in file_entries}

            # Wait for all to complete
            for future in as_completed(futures):
                result = future.result()

        # Print final progress
        status = progress.get_status()
        print(f"\n✓ Parallel processing complete:")
        print(f"  Processed: {status['processed']}")
        print(f"  Skipped: {status['skipped']}")
        print(f"  Failed: {status['failed']}")
        print(f"  Total: {status['total']}")

    def _process_entry(self, db: Session, entry: dict, quiet: bool = False) -> str:
        """Process a file entry (either individual file or merged directory).

        Args:
            db: Database session
            entry: Entry dict with 'type', 'path', 'files', and 'data_source_type' keys
            quiet: If True, suppress verbose output (for parallel processing)

        Returns:
            Status string: 'processed', 'skipped', or 'failed'
        """
        def _print(msg):
            """Conditional print based on quiet mode."""
            if not quiet:
                print(msg)

        # Check data source type and route accordingly
        data_source_type = entry.get('data_source_type', 'companies')

        # Route to building processor if this is a building data source
        if data_source_type == 'buildings' and BUILDING_PROCESSING_ENABLED:
            return self._process_building_entry(db, entry, quiet)

        # Route to government opportunities processor if this is a government data source
        if data_source_type == 'government':
            return self._process_government_entry(db, entry, quiet)

        # Standard processing for companies data sources
        # Get content based on entry type
        if entry['type'] == 'merged':
            # Merge multiple files
            from pathlib import Path
            directory = Path(entry['path'])
            merge_patterns = entry['merge_patterns']

            _print(f"→ Merging {len(entry['files'])} files from {directory.name}/...")
            content, merged_files = self.reader.merge_directory_files(directory, merge_patterns)
            file_type = 'merged'
            file_path = str(directory)  # Use directory path as identifier
            _print(f"✓ Merged {len(merged_files)} files: {len(content)} chars")
        else:
            # Process single file
            file_path = entry['path']
            content, file_type = self.reader.read_file(file_path)
            _print(f"✓ Read file ({file_type}): {len(content)} chars")

        return self._process_content(db, content, file_path, file_type, quiet)

    def _process_content(self, db: Session, content: str, file_path: str, file_type: str, quiet: bool = False) -> str:
        """Process file content through the pipeline.

        Args:
            db: Database session
            content: File content
            file_path: Path identifier (file or directory)
            file_type: Type of content
            quiet: If True, suppress verbose output

        Returns:
            Status string: 'processed', 'skipped', or 'failed'
        """
        def _print(msg):
            """Conditional print based on quiet mode."""
            if not quiet:
                print(msg)

        # Check if already processed (deduplication)
        content_hash = compute_content_hash(content)
        existing = db.query(RawEvent).filter(RawEvent.content_hash == content_hash).first()

        if existing:
            if existing.status == "PROCESSED":
                _print(f"⊙ File already processed (hash: {content_hash[:8]}...), skipping")
                return 'skipped'
            else:
                _print(f"⊙ File exists but not processed, reprocessing...")
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

        # Normalize (extract events - may be multiple companies)
        if TWO_STAGE_EXTRACTION:
            if not quiet:
                print("→ Two-stage extraction (filter + extract)...")
            extraction = self.normalizer.normalize_document_two_stage(
                content=content,
                file_path=file_path,
                source="local_bucket"
            )
        else:
            _print("→ Normalizing document with LLM...")
            extraction = self.normalizer.normalize_document(
                content=content,
                file_path=file_path,
                source="local_bucket"
            )

        if not extraction:
            raw_event.status = "FAILED"
            raw_event.error = "Normalization failed"
            _print("✗ Normalization failed")
            return 'failed'

        # Check relevance
        if not extraction.is_relevant:
            raw_event.status = "FAILED"
            raw_event.error = f"Document not relevant: {extraction.relevance_reasoning}"
            _print(f"⊘ Document not relevant: {extraction.relevance_reasoning}")
            return 'failed'

        # Check if any events were extracted
        if not extraction.events:
            raw_event.status = "FAILED"
            raw_event.error = "No companies/events extracted from document"
            _print(f"⊘ No events extracted (document relevant but no actionable companies found)")
            return 'failed'

        _print(f"✓ Document relevant: {extraction.relevance_reasoning}")
        _print(f"✓ Extracted {len(extraction.events)} event(s) from {len(set(e.entity_name_canonical for e in extraction.events))} entity(ies)")

        # Process each event (one per company)
        MIN_CONFIDENCE = 0.3  # Configurable threshold
        processed_count = 0
        failed_events = []  # Track failed events

        for idx, normalized_event in enumerate(extraction.events, 1):
            _print(f"\n  Event {idx}/{len(extraction.events)}:")
            _print(f"  → Entity: {normalized_event.entity_name_raw} -> {normalized_event.entity_name_canonical}")
            _print(f"  → Type: {normalized_event.event_type}")
            _print(f"  → Confidence: {normalized_event.extraction_confidence:.2f}")

            # Check minimum confidence threshold
            if normalized_event.extraction_confidence < MIN_CONFIDENCE:
                _print(f"  ⊘ Skipped (confidence too low: {normalized_event.extraction_confidence:.2f} < {MIN_CONFIDENCE})")
                continue

            # Process this event with error handling
            try:
                self._process_event(db, normalized_event, file_path, "local_bucket", quiet=quiet)
                processed_count += 1
            except Exception as e:
                error_msg = f"Failed to process event for {normalized_event.entity_name_canonical}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                _print(f"  ✗ Error: {error_msg}")

                failed_events.append({
                    'entity_name': normalized_event.entity_name_canonical,
                    'event_type': normalized_event.event_type,
                    'error': str(e),
                    'file_path': file_path
                })

                # Continue processing other events instead of failing
                continue

        # Report results
        if failed_events:
            _print(f"\n⚠ {len(failed_events)} event(s) failed to process (see {self.log_file} for details)")
            for failed in failed_events:
                _print(f"  ✗ {failed['entity_name']} ({failed['event_type']}): {failed['error'][:80]}")

        if processed_count == 0:
            if len(extraction.events) == len(failed_events):
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(extraction.events)} events failed to process"
                _print(f"\n✗ All events failed")
                return 'failed'
            else:
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(extraction.events)} events below confidence threshold"
                _print(f"\n✗ All events filtered out (low confidence)")
                return 'failed'

        # Mark as processed (even with some failures)
        raw_event.status = "PROCESSED"
        success_msg = f"File processing complete: {processed_count}/{len(extraction.events)} events processed"
        if failed_events:
            success_msg += f", {len(failed_events)} failed"
        _print(f"\n✓ {success_msg}")
        return 'processed'

    def _process_building_entry(self, db: Session, entry: dict, quiet: bool = False) -> str:
        """Process a building demolition entry.

        This is a specialized processor for building data sources that:
        1. Extracts building demolition information
        2. Searches for companies at the building address
        3. Creates events for each company found
        4. Processes events through standard enrichment/scoring pipeline

        Args:
            db: Database session
            entry: Entry dict with 'type', 'path', and 'files' keys
            quiet: If True, suppress verbose output

        Returns:
            Status string: 'processed', 'skipped', or 'failed'
        """
        from src.pipeline.buildings_processor import process_building_document

        def _print(msg):
            """Conditional print based on quiet mode."""
            if not quiet:
                print(msg)

        # Get content based on entry type
        if entry['type'] == 'merged':
            # Merge multiple files
            from pathlib import Path
            directory = Path(entry['path'])
            merge_patterns = entry['merge_patterns']

            _print(f"→ [BUILDING] Merging {len(entry['files'])} files from {directory.name}/...")
            content, merged_files = self.reader.merge_directory_files(directory, merge_patterns)
            file_path = str(directory)
            _print(f"✓ Merged {len(merged_files)} files: {len(content)} chars")
        else:
            # Process single file
            file_path = entry['path']
            content, file_type = self.reader.read_file(file_path)
            _print(f"✓ [BUILDING] Read file ({file_type}): {len(content)} chars")

        # Check if already processed (deduplication)
        content_hash = compute_content_hash(content)
        existing = db.query(RawEvent).filter(RawEvent.content_hash == content_hash).first()

        if existing:
            if existing.status == "PROCESSED":
                _print(f"⊙ Building file already processed (hash: {content_hash[:8]}...), skipping")
                return 'skipped'
            else:
                _print(f"⊙ Building file exists but not processed, reprocessing...")
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

        # Process building document
        _print("→ [BUILDING] Extracting building demolition info...")
        try:
            result = process_building_document(
                content=content,
                file_path=file_path,
                llm_client=self.normalizer.llm,
                search_client=self.enricher.search
            )
        except Exception as e:
            raw_event.status = "FAILED"
            raw_event.error = f"Building processing failed: {str(e)}"
            self.logger.error(f"Building processing error for {file_path}: {e}", exc_info=True)
            _print(f"✗ Building processing failed: {str(e)}")
            return 'failed'

        # Handle result
        if result['status'] == 'skipped':
            raw_event.status = "FAILED"
            raw_event.error = f"Not demolition-related: {result.get('reason', 'unknown')}"
            _print(f"⊘ Not a building demolition document")
            return 'skipped'

        if result['status'] == 'completed' and result['companies_found'] == 0:
            raw_event.status = "PROCESSED"
            raw_event.error = f"No companies found: {result.get('reason', 'unknown')}"

            # Handle multi-permit vs single building display
            if 'permits_processed' in result:
                _print(f"⊙ Processed {result['permits_processed']} permits but no companies found")
            else:
                _print(f"⊙ Building processed but no companies found at {result.get('building_address')}")
            return 'processed'

        # Process events for each company found
        events = result.get('events', [])
        if not events:
            raw_event.status = "PROCESSED"

            # Handle multi-permit vs single building display
            if 'permits_processed' in result:
                _print(f"⊙ No events created from {result.get('permits_processed')} permits")
            else:
                _print(f"⊙ No events created for {result.get('building_address')}")
            return 'processed'

        # Display summary based on processing mode
        if 'permits_processed' in result:
            # Multiple permits mode
            _print(f"✓ Processed {result['permits_processed']} permits")
            _print(f"✓ Found companies at {result['permits_with_companies']} buildings")
            _print(f"✓ Total: {result['companies_found']} companies, {result['events_created']} events")
        else:
            # Single building mode (LLM extraction)
            _print(f"✓ Building: {result.get('building_address')}")
            _print(f"✓ Found {result['companies_found']} companies, created {result['events_created']} events")

        # Process each event through standard pipeline
        MIN_CONFIDENCE = 0.3
        processed_count = 0
        failed_events = []

        for idx, normalized_event in enumerate(events, 1):
            _print(f"\n  Company {idx}/{len(events)}:")
            _print(f"  → Entity: {normalized_event.entity_name_raw}")
            _print(f"  → Confidence: {normalized_event.extraction_confidence:.2f}")

            # Check minimum confidence threshold
            if normalized_event.extraction_confidence < MIN_CONFIDENCE:
                _print(f"  ⊘ Skipped (confidence too low: {normalized_event.extraction_confidence:.2f} < {MIN_CONFIDENCE})")
                continue

            # Process this event with error handling
            try:
                self._process_event(db, normalized_event, file_path, "local_bucket", quiet=quiet)
                processed_count += 1
            except Exception as e:
                error_msg = f"Failed to process event for {normalized_event.entity_name_canonical}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                _print(f"  ✗ Error: {error_msg}")

                failed_events.append({
                    'entity_name': normalized_event.entity_name_canonical,
                    'event_type': normalized_event.event_type,
                    'error': str(e),
                    'file_path': file_path
                })
                continue

        # Report results
        if failed_events:
            _print(f"\n⚠ {len(failed_events)} event(s) failed to process (see {self.log_file} for details)")
            for failed in failed_events:
                _print(f"  ✗ {failed['entity_name']}: {failed['error'][:80]}")

        if processed_count == 0:
            if len(events) == len(failed_events):
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(events)} company events failed to process"
                _print(f"\n✗ All company events failed")
                return 'failed'
            else:
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(events)} company events below confidence threshold"
                _print(f"\n✗ All company events filtered out (low confidence)")
                return 'failed'

        # Mark as processed
        raw_event.status = "PROCESSED"
        success_msg = f"Building processing complete: {processed_count}/{len(events)} company events processed"
        if failed_events:
            success_msg += f", {len(failed_events)} failed"
        _print(f"\n✓ {success_msg}")
        return 'processed'

    def _process_government_entry(self, db: Session, entry: dict, quiet: bool = False) -> str:
        """Process a government opportunities entry.

        This is a specialized processor for government data sources that:
        1. Parses opportunities array from JSON
        2. Extracts location from each opportunity
        3. Creates events with entity names including location (agency + state)

        Args:
            db: Database session
            entry: Entry dict with 'type', 'path', and 'files' keys
            quiet: If True, suppress verbose output

        Returns:
            Status string: 'processed', 'skipped', or 'failed'
        """
        from src.pipeline.government_opportunities_processor import process_government_opportunities_document

        def _print(msg):
            """Conditional print based on quiet mode."""
            if not quiet:
                print(msg)

        # Get content based on entry type
        if entry['type'] == 'merged':
            # Merge multiple files
            from pathlib import Path
            directory = Path(entry['path'])
            merge_patterns = entry['merge_patterns']

            _print(f"→ [GOVERNMENT] Merging {len(entry['files'])} files from {directory.name}/...")
            content, merged_files = self.reader.merge_directory_files(directory, merge_patterns)
            file_path = str(directory)
            _print(f"✓ Merged {len(merged_files)} files: {len(content)} chars")
        else:
            # Process single file
            file_path = entry['path']
            content, file_type = self.reader.read_file(file_path)
            _print(f"✓ [GOVERNMENT] Read file ({file_type}): {len(content)} chars")

        # Check if already processed (deduplication)
        content_hash = compute_content_hash(content)
        existing = db.query(RawEvent).filter(RawEvent.content_hash == content_hash).first()

        if existing:
            if existing.status == "PROCESSED":
                _print(f"⊙ Government file already processed (hash: {content_hash[:8]}...), skipping")
                return 'skipped'
            else:
                _print(f"⊙ Government file exists but not processed, reprocessing...")
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

        # Process government opportunities document
        _print("→ [GOVERNMENT] Processing opportunities...")
        try:
            result = process_government_opportunities_document(
                content=content,
                file_path=file_path
            )
        except Exception as e:
            raw_event.status = "FAILED"
            raw_event.error = f"Government processing failed: {str(e)}"
            self.logger.error(f"Government processing error for {file_path}: {e}", exc_info=True)
            _print(f"✗ Government processing failed: {str(e)}")
            return 'failed'

        # Check if we got structured data or need to fall back to LLM
        if result['status'] == 'no_structured_data':
            _print("⊙ No structured opportunities found, falling back to LLM extraction...")
            # Fall back to standard content processing
            return self._process_content(db, content, file_path, 'json', quiet)

        # Process events for each opportunity found
        events = result.get('events', [])
        if not events:
            raw_event.status = "PROCESSED"
            _print(f"⊙ No events created from {result.get('opportunities_processed', 0)} opportunities")
            return 'processed'

        _print(f"✓ Processed {result['opportunities_processed']} opportunities, created {result['events_created']} events")

        # Process each event through standard pipeline
        MIN_CONFIDENCE = 0.3
        processed_count = 0
        failed_events = []

        for idx, normalized_event in enumerate(events, 1):
            _print(f"\n  Opportunity {idx}/{len(events)}:")
            _print(f"  → Entity: {normalized_event.entity_name_raw}")
            _print(f"  → Confidence: {normalized_event.extraction_confidence:.2f}")

            # Check minimum confidence threshold
            if normalized_event.extraction_confidence < MIN_CONFIDENCE:
                _print(f"  ⊘ Skipped (confidence too low: {normalized_event.extraction_confidence:.2f} < {MIN_CONFIDENCE})")
                continue

            # Process this event with error handling
            try:
                self._process_event(db, normalized_event, file_path, "local_bucket", quiet=quiet)
                processed_count += 1
            except Exception as e:
                error_msg = f"Failed to process event for {normalized_event.entity_name_canonical}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                _print(f"  ✗ Error: {error_msg}")

                failed_events.append({
                    'entity_name': normalized_event.entity_name_canonical,
                    'event_type': normalized_event.event_type,
                    'error': str(e),
                    'file_path': file_path
                })
                continue

        # Report results
        if failed_events:
            _print(f"\n⚠ {len(failed_events)} event(s) failed to process (see {self.log_file} for details)")
            for failed in failed_events:
                _print(f"  ✗ {failed['entity_name']}: {failed['error'][:80]}")

        if processed_count == 0:
            if len(events) == len(failed_events):
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(events)} opportunity events failed to process"
                _print(f"\n✗ All opportunity events failed")
                return 'failed'
            else:
                raw_event.status = "FAILED"
                raw_event.error = f"All {len(events)} opportunity events below confidence threshold"
                _print(f"\n✗ All opportunity events filtered out (low confidence)")
                return 'failed'

        # Mark as processed
        raw_event.status = "PROCESSED"
        success_msg = f"Government processing complete: {processed_count}/{len(events)} opportunity events processed"
        if failed_events:
            success_msg += f", {len(failed_events)} failed"
        _print(f"\n✓ {success_msg}")
        return 'processed'

    def _process_event(self, db: Session, normalized_event, file_path: str, source: str, quiet: bool = False):
        """Process a single event for an entity."""
        def _print(msg):
            """Conditional print based on quiet mode."""
            if not quiet:
                print(msg)

        # Canonicalize name
        canonical_name, normalized_name = canonicalize_company_name(
            normalized_event.entity_name_canonical
        )

        # Enrich entity (optional, based on config and freshness)
        enrichment = None

        if ENRICHMENT_ENABLED:
            _print("→ Checking if enrichment needed...")

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
                _print("→ Enriching entity...")
                enrichment = self.enricher.enrich_entity(
                    canonical_name=canonical_name,
                    alternative_names=[normalized_event.entity_name_raw]
                )
            else:
                _print("⊙ Enrichment not needed (recent or has domain)")
        else:
            _print("⊙ Enrichment disabled (set ENRICHMENT_ENABLED=true to enable)")

        # Add location fallback: If event doesn't have location, use company HQ from enrichment
        from src.utils.location_utils import normalize_state, normalize_city

        # Get current location from event
        event_city = normalized_event.key_facts.city if normalized_event.key_facts else None
        event_state = normalized_event.key_facts.state if normalized_event.key_facts else None

        # If no location in event and enrichment has HQ location, use it
        if not event_state and enrichment and enrichment.metadata:
            hq_state = enrichment.metadata.get("hq_state")
            hq_city = enrichment.metadata.get("hq_city")

            if hq_state:
                # Normalize HQ location
                normalized_hq_state = normalize_state(hq_state)
                normalized_hq_city = normalize_city(hq_city) if hq_city else None

                # Update event key_facts with HQ location
                if not normalized_event.key_facts:
                    from src.llm.schemas import KeyFact
                    normalized_event.key_facts = KeyFact()

                if not normalized_event.key_facts.state:
                    normalized_event.key_facts.state = normalized_hq_state
                if not normalized_event.key_facts.city and normalized_hq_city:
                    normalized_event.key_facts.city = normalized_hq_city

                _print(f"  → Using HQ location: {normalized_hq_city}, {normalized_hq_state}")

        # Normalize location regardless of source (from event or HQ fallback)
        if normalized_event.key_facts:
            if normalized_event.key_facts.state:
                normalized_event.key_facts.state = normalize_state(normalized_event.key_facts.state)
            if normalized_event.key_facts.city:
                normalized_event.key_facts.city = normalize_city(normalized_event.key_facts.city)

        # Resolve entity (dedupe)
        _print("→ Resolving entity...")
        entity = self.resolver.resolve_or_create_entity(
            db=db,
            canonical_name=canonical_name,
            normalized_name=normalized_name,
            entity_type=normalized_event.entity_type,
            entity_metadata=normalized_event.entity_metadata,
            enrichment=enrichment
        )
        db.flush()

        # Create event record
        _print("→ Persisting event...")
        event = Event(
            entity_id=entity.id,
            source="local_bucket",
            event_type=normalized_event.event_type,
            event_time=self._parse_date(normalized_event.event_date),
            strict={
                "entity_name_raw": normalized_event.entity_name_raw,
                "entity_name_canonical": normalized_event.entity_name_canonical,
                "entity_type": normalized_event.entity_type,
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
        _print(f"✓ Event persisted: {event.id}")

        # Score and materialize lead
        _print(f"  → Scoring lead for {canonical_name}...")
        lead = self.scorer.score_and_materialize_lead(db, entity)
        db.flush()

        # Score and materialize location-based lead (if event has location)
        if normalized_event.key_facts and normalized_event.key_facts.state:
            state = normalized_event.key_facts.state
            city = normalized_event.key_facts.city if normalized_event.key_facts else None

            _print(f"  → Scoring location lead for {canonical_name} in {state}...")
            location_lead = self.location_scorer.score_and_materialize_location_lead(
                db=db,
                entity=entity,
                state=state,
                city=city
            )
            if location_lead:
                db.flush()
                _print(f"  ✓ Location lead updated: {state} (score={location_lead.score})")

        _print(f"  ✓ Event processed for {canonical_name}")

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
            print(f"  Type: {entity.entity_type or 'N/A'}")
            print(f"  Domain: {entity.domain or 'N/A'}")

            # Get metadata fields
            metadata = entity.entity_metadata or {}
            website = metadata.get('website_url') or metadata.get('gov_domain')
            linkedin = metadata.get('linkedin_url')
            hq_city = metadata.get('hq_city')
            hq_state = metadata.get('hq_state')

            if website:
                print(f"  Website: {website}")
            if linkedin:
                print(f"  LinkedIn: {linkedin}")
            if hq_city or hq_state:
                hq = f"{hq_city or 'Unknown'}, {hq_state or 'Unknown'}"
                print(f"  HQ: {hq}")

            # Show some entity-specific metadata
            if entity.entity_type == 'government_agency' and metadata.get('agency_code'):
                print(f"  Agency Code: {metadata.get('agency_code')}")
                print(f"  Jurisdiction: {metadata.get('jurisdiction', 'N/A')}")
            elif entity.entity_type == 'contractor' and metadata.get('duns_number'):
                print(f"  DUNS: {metadata.get('duns_number')}")

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
