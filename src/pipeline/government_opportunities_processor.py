"""Government opportunities processor - extracts agency expansion events with locations."""
import logging
import json
from typing import List, Optional, Dict, Any

from src.llm.schemas import NormalizedEvent, KeyFact, DynamicSignal
from src.config import EVENT_TYPES

logger = logging.getLogger(__name__)


def parse_opportunities_from_json(content: str) -> List[Dict[str, Any]]:
    """
    Parse opportunities from JSON file.

    Handles both:
    - Structured format: {"opportunities": [...]}
    - Single opportunity: {...}
    - Plain text/HTML (returns empty list to fall back to LLM)

    Args:
        content: File content

    Returns:
        List of opportunity dictionaries
    """
    try:
        data = json.loads(content)

        # Check for opportunities array
        if isinstance(data, dict) and "opportunities" in data:
            opportunities = data["opportunities"]
            if isinstance(opportunities, list):
                logger.info(f"Found {len(opportunities)} opportunities in structured JSON")
                return opportunities

        # Single opportunity object
        if isinstance(data, dict):
            # Check if it looks like an opportunity
            if any(key in data for key in ["opportunity_id", "notice_id", "solicitation_number", "title"]):
                logger.info("Found single opportunity in JSON")
                return [data]

        logger.info("JSON doesn't contain opportunity structure, will use LLM extraction")
        return []

    except json.JSONDecodeError:
        # Not JSON - could be HTML, text, PDF, etc.
        logger.info("Content is not JSON, will use LLM extraction")
        return []


def extract_agency_name(opportunity: Dict[str, Any]) -> str:
    """
    Extract agency name from opportunity data.

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Agency name
    """
    # Try to get from fullParentPathName in raw_api_response
    raw_api = opportunity.get("raw_api_response", {})
    full_path = raw_api.get("fullParentPathName", "")

    if full_path:
        # Example: "VETERANS AFFAIRS, DEPARTMENT OF.VETERANS AFFAIRS, DEPARTMENT OF.248-NETWORK CONTRACT OFFICE 8"
        # Extract first meaningful part
        parts = full_path.split(".")
        if parts:
            agency_name = parts[0].strip()
            # Remove trailing ", DEPARTMENT OF" etc
            agency_name = agency_name.replace(", DEPARTMENT OF", "")
            agency_name = agency_name.replace(", DEPT OF", "")
            return agency_name

    # Fallback to agency field
    if opportunity.get("agency"):
        return opportunity["agency"]

    # Last resort - extract from title
    title = opportunity.get("title", "")
    if "VA" in title or "Veterans" in title:
        return "Veterans Affairs"

    return "Unknown Agency"


def extract_location(opportunity: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Extract city and state from opportunity placeOfPerformance.

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Tuple of (city, state)
    """
    raw_api = opportunity.get("raw_api_response", {})
    place_of_performance = raw_api.get("placeOfPerformance", {})

    city_data = place_of_performance.get("city", {})
    state_data = place_of_performance.get("state", {})

    city = None
    state = None

    if isinstance(city_data, dict):
        city = city_data.get("name")
    elif isinstance(city_data, str):
        city = city_data

    if isinstance(state_data, dict):
        state = state_data.get("name")
    elif isinstance(state_data, str):
        state = state_data

    return city, state


def create_opportunity_event(
    opportunity: Dict[str, Any],
    file_path: str
) -> Optional[NormalizedEvent]:
    """
    Create NormalizedEvent from a government opportunity.

    Args:
        opportunity: Opportunity dictionary
        file_path: Path to source file

    Returns:
        NormalizedEvent or None if data is insufficient
    """
    try:
        # Extract key data
        agency_name = extract_agency_name(opportunity)
        city, state = extract_location(opportunity)

        title = opportunity.get("title", "")
        solicitation_number = opportunity.get("solicitation_number", "")
        source_url = opportunity.get("source_url")
        posted_date = opportunity.get("posted_date")
        response_deadline = opportunity.get("response_deadline")

        # Create entity name with location
        if state:
            entity_name_raw = f"{agency_name} - {state}"
            entity_name_canonical = f"{agency_name.upper().replace(' ', '')}-{state.upper().replace(' ', '')}"
        else:
            entity_name_raw = agency_name
            entity_name_canonical = agency_name.upper().replace(" ", "")

        # Build summary
        location_str = ""
        if city and state:
            location_str = f" in {city}, {state}"
        elif city:
            location_str = f" in {city}"
        elif state:
            location_str = f" in {state}"

        summary = f"{agency_name} is seeking a new lease{location_str}: {title}"

        # Build key facts
        key_facts_dict = {}

        if city:
            key_facts_dict["city"] = city
        if state:
            key_facts_dict["state"] = state
        if solicitation_number:
            key_facts_dict["solicitation_number"] = solicitation_number
        if response_deadline:
            key_facts_dict["response_deadline"] = response_deadline

        # Add NAICS code if available
        naics_code = opportunity.get("naics_code")
        if naics_code:
            key_facts_dict["naics_code"] = naics_code

        # Create dynamic signals
        dynamic_signals = [
            DynamicSignal(
                signal_type="government_lease_opportunity",
                description=f"New lease opportunity posted for {title}",
                evidence_quote=title
            )
        ]

        # Prepare entity metadata
        entity_metadata = {
            "solicitation_number": solicitation_number,
        }

        # Extract agency code from fullParentPathCode
        raw_api = opportunity.get("raw_api_response", {})
        if raw_api.get("fullParentPathCode"):
            entity_metadata["agency_code"] = raw_api["fullParentPathCode"].split(".")[0]

        entity_metadata["jurisdiction"] = "federal"  # Assuming SAM.gov is federal

        if city:
            entity_metadata["opportunity_city"] = city
        if state:
            entity_metadata["opportunity_state"] = state

        # Create normalized event
        event = NormalizedEvent(
            entity_name_raw=entity_name_raw,
            entity_name_canonical=entity_name_canonical,
            entity_type="government_agency",
            entity_metadata=entity_metadata,
            event_type="expansion",  # New lease = expansion
            summary=summary,
            key_facts=KeyFact(**key_facts_dict) if key_facts_dict else None,
            source_url=source_url,
            event_date=posted_date,
            extraction_confidence=1.0,  # Direct from structured data
            missing_fields=[],
            dynamic_signals=dynamic_signals
        )

        logger.info(f"Created event for {entity_name_raw}: {title}")
        return event

    except Exception as e:
        logger.error(f"Error creating event for opportunity: {e}", exc_info=True)
        return None


def process_government_opportunities_document(
    content: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Process government opportunities document.

    Handles two modes:
    1. Structured JSON with opportunities array - processes each opportunity separately
    2. Unstructured text/HTML - returns empty (falls back to LLM in main pipeline)

    Args:
        content: Document content
        file_path: Path to source file

    Returns:
        Dict with processing results and list of events
    """
    # Try to parse as structured opportunities JSON
    opportunities = parse_opportunities_from_json(content)

    if opportunities:
        # Process all opportunities in the file
        logger.info(f"Processing {len(opportunities)} opportunities from structured JSON")

        events = []
        for idx, opportunity_data in enumerate(opportunities, 1):
            logger.info(f"Processing opportunity {idx}/{len(opportunities)}: {opportunity_data.get('opportunity_id', 'unknown')}")

            event = create_opportunity_event(opportunity_data, file_path)
            if event:
                events.append(event)

        logger.info(
            f"Processed {len(opportunities)} opportunities, "
            f"created {len(events)} events"
        )

        return {
            "status": "completed",
            "opportunities_processed": len(opportunities),
            "events_created": len(events),
            "events": events
        }

    # No structured opportunities found - signal to use LLM extraction
    return {
        "status": "no_structured_data",
        "events": []
    }
