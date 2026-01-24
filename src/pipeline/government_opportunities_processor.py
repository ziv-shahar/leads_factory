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


def fetch_agency_from_sam_url(source_url: str) -> Optional[str]:
    """
    Fetch agency information from SAM.gov URL using Tavily.

    Args:
        source_url: SAM.gov opportunity URL

    Returns:
        Agency name or None if not found
    """
    try:
        from tavily import TavilyClient
        import os

        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.warning("TAVILY_API_KEY not set, cannot fetch agency from URL")
            return None

        client = TavilyClient(api_key=tavily_key)

        # Fetch the page content directly
        logger.info(f"Fetching agency info from: {source_url}")
        results = client.search(source_url, max_results=1, include_raw_content=True)

        if not results.get("results"):
            logger.warning(f"No results from Tavily for: {source_url}")
            return None

        # Get the content from the result
        result = results["results"][0]
        content = result.get("raw_content", "") or result.get("content", "")

        if not content:
            logger.warning(f"No content returned from Tavily for: {source_url}")
            return None

        # Extract agency from content
        # Look for "Department/Agency" field or similar patterns in SAM.gov pages
        import re

        # Common patterns in SAM.gov pages
        patterns = [
            r"Department/Ind\. Agency:\s*([^\n<]+)",
            r"Department:\s*([^\n<]+)",
            r"Agency:\s*([^\n<]+)",
            r"fullParentPathName[\"']:\s*[\"']([^\"']+)[\"']",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                agency = match.group(1).strip()
                # Clean up
                agency = agency.replace(", DEPARTMENT OF", "")
                agency = agency.replace(", DEPT OF", "")
                # If it has dots, take the first part
                if "." in agency:
                    agency = agency.split(".")[0].strip()
                logger.info(f"Extracted agency from SAM.gov: {agency}")
                return agency

        # If patterns don't match, look for known agencies in content
        content_upper = content.upper()
        known_agencies = {
            "VETERANS AFFAIRS": "Veterans Affairs",
            "GENERAL SERVICES ADMINISTRATION": "General Services Administration",
            "DEPARTMENT OF DEFENSE": "Department of Defense",
            "DEPARTMENT OF STATE": "Department of State",
            "DEPARTMENT OF ENERGY": "Department of Energy",
            "NASA": "NASA",
            "EPA": "Environmental Protection Agency",
        }

        for key, value in known_agencies.items():
            if key in content_upper:
                logger.info(f"Found agency in content: {value}")
                return value

        logger.warning(f"Could not extract agency from content for: {source_url}")
        return None

    except Exception as e:
        logger.error(f"Error fetching agency from URL: {e}", exc_info=True)
        return None


def extract_agency_name(opportunity: Dict[str, Any]) -> str:
    """
    Extract agency name from opportunity data using SAM.gov URL.

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Agency name
    """
    # PRIMARY METHOD: Fetch from source_url using Tavily
    source_url = opportunity.get("source_url")
    if source_url:
        agency = fetch_agency_from_sam_url(source_url)
        if agency:
            return agency

    # FALLBACK 1: Try to get from fullParentPathName in raw_api_response
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

    # FALLBACK 2: agency field
    if opportunity.get("agency"):
        return opportunity["agency"]

    # FALLBACK 3: extract from title
    title = opportunity.get("title", "")
    if "VA" in title or "Veterans" in title:
        return "Veterans Affairs"

    return "Unknown Agency"


def fetch_location_from_sam_url(source_url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch location information from SAM.gov URL using Tavily.

    Args:
        source_url: SAM.gov opportunity URL

    Returns:
        Tuple of (city, state)
    """
    try:
        from tavily import TavilyClient
        import os

        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return None, None

        client = TavilyClient(api_key=tavily_key)

        # Fetch the page content directly
        logger.info(f"Fetching location info from: {source_url}")
        results = client.search(source_url, max_results=1, include_raw_content=True)

        if not results.get("results"):
            return None, None

        # Get the content from the result
        result = results["results"][0]
        content = result.get("raw_content", "") or result.get("content", "")

        if not content:
            return None, None

        # Extract location from content
        import re

        # Look for place of performance patterns in SAM.gov pages
        patterns = [
            r"Place of Performance.*?City:\s*([^\n<]+).*?State:\s*([^\n<]+)",
            r"Location:\s*([^,]+),\s*([A-Z]{2})",
            r"([A-Za-z\s]+),\s*([A-Z]{2})\s+\d{5}",  # City, ST 12345 format
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                city = match.group(1).strip()
                state = match.group(2).strip()
                logger.info(f"Extracted location from SAM.gov: {city}, {state}")
                return city, state

        return None, None

    except Exception as e:
        logger.error(f"Error fetching location from URL: {e}", exc_info=True)
        return None, None


def extract_location(opportunity: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Extract city and state from opportunity data using SAM.gov URL.

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Tuple of (city, state)
    """
    # PRIMARY METHOD: Fetch from source_url using Tavily
    source_url = opportunity.get("source_url")
    if source_url:
        city, state = fetch_location_from_sam_url(source_url)
        if city or state:
            return city, state

    # FALLBACK: Try placeOfPerformance in raw_api_response
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
    from src.utils.location_utils import normalize_state, normalize_city

    try:
        # Extract key data
        agency_name = extract_agency_name(opportunity)
        city, state = extract_location(opportunity)

        # Normalize location
        normalized_state = normalize_state(state) if state else None
        normalized_city = normalize_city(city) if city else None

        title = opportunity.get("title", "")
        solicitation_number = opportunity.get("solicitation_number", "")
        source_url = opportunity.get("source_url")
        posted_date = opportunity.get("posted_date")
        response_deadline = opportunity.get("response_deadline")

        # Entity name is just the agency name (no location suffix)
        entity_name_raw = agency_name
        entity_name_canonical = agency_name.upper().replace(" ", "")

        # Build summary with normalized location
        location_str = ""
        if normalized_city and normalized_state:
            location_str = f" in {normalized_city}, {normalized_state}"
        elif normalized_city:
            location_str = f" in {normalized_city}"
        elif normalized_state:
            location_str = f" in {normalized_state}"

        summary = f"{agency_name} is seeking a new lease{location_str}: {title}"

        # Build key facts with normalized location
        key_facts_dict = {}

        if normalized_city:
            key_facts_dict["city"] = normalized_city
        if normalized_state:
            key_facts_dict["state"] = normalized_state
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

        if normalized_city:
            entity_metadata["opportunity_city"] = normalized_city
        if normalized_state:
            entity_metadata["opportunity_state"] = normalized_state

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
