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
    Extract agency name from opportunity data.

    Tries multiple sources in order:
    1. Top-level agency field (if present and not empty)
    2. raw_api_response.fullParentPathName (if available)
    3. Web enrichment from source_url using Tavily (only if agency is missing)

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Agency name
    """
    # FIRST: Check agency field
    agency = opportunity.get("agency", "").strip()
    if agency:
        # Clean up common suffixes
        agency = agency.replace(", DEPARTMENT OF", "")
        agency = agency.replace(", DEPT OF", "")
        agency = agency.replace("DEPT OF ", "")
        return agency

    # SECOND: Try to get from fullParentPathName in raw_api_response
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

    # THIRD: Last resort - fetch from source_url using Tavily (ONLY if agency is missing)
    source_url = opportunity.get("source_url")
    if source_url:
        logger.info(f"Agency field empty, fetching from URL: {source_url}")
        fetched_agency = fetch_agency_from_sam_url(source_url)
        if fetched_agency:
            return fetched_agency

    # Extract from title as final fallback
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
    Extract city and state from opportunity data.

    Tries multiple sources in order:
    1. Top-level city/state fields (if present)
    2. raw_api_response.placeOfPerformance (if available)
    3. Web enrichment from source_url using Tavily (only if missing)

    Args:
        opportunity: Opportunity dictionary

    Returns:
        Tuple of (city, state)
    """
    # FIRST: Check top-level city/state fields
    city = opportunity.get("city")
    state = opportunity.get("state")

    if city or state:
        return city, state

    # SECOND: Try placeOfPerformance in raw_api_response
    raw_api = opportunity.get("raw_api_response", {})
    place_of_performance = raw_api.get("placeOfPerformance", {})

    city_data = place_of_performance.get("city", {})
    state_data = place_of_performance.get("state", {})

    if isinstance(city_data, dict):
        city = city_data.get("name")
    elif isinstance(city_data, str):
        city = city_data

    if isinstance(state_data, dict):
        state = state_data.get("name")
    elif isinstance(state_data, str):
        state = state_data

    if city or state:
        return city, state

    # THIRD: Last resort - fetch from source_url using Tavily (ONLY if location is missing)
    source_url = opportunity.get("source_url")
    if source_url:
        logger.info(f"Location fields empty, fetching from URL: {source_url}")
        city, state = fetch_location_from_sam_url(source_url)
        if city or state:
            return city, state

    return None, None


def is_office_space_relevant(opportunity: Dict[str, Any]) -> bool:
    """
    Filter out opportunities that are NOT actual office/commercial space leases.

    Returns False for:
    - Event spaces, exhibit booths, graduation ceremonies
    - Non-real-estate NAICS codes
    - Temporary event rentals

    Args:
        opportunity: Opportunity dictionary

    Returns:
        True if this is a relevant office space opportunity, False otherwise
    """
    title = opportunity.get("title", "").lower()
    notice_type = opportunity.get("notice_type", "").lower()
    naics_code = opportunity.get("naics_code", "")

    # FILTER 1: Skip non-office-space titles
    irrelevant_keywords = [
        "event space",
        "exhibit booth",
        "booth space",
        "graduation",
        "ceremony",
        "trade show",
        "conference space",
        "banquet",
        "reception",
    ]

    for keyword in irrelevant_keywords:
        if keyword in title:
            logger.info(f"Skipping non-office opportunity: '{title}' (contains '{keyword}')")
            return False

    # FILTER 2: Only accept NAICS 531120 (Real Estate Leasing) or missing NAICS
    # Missing NAICS is OK (some opportunities don't specify)
    if naics_code and naics_code != "531120":
        logger.info(f"Skipping non-real-estate opportunity: NAICS {naics_code} (need 531120)")
        return False

    return True


def is_opportunity_actionable(opportunity: Dict[str, Any]) -> bool:
    """
    Filter out opportunities that are no longer actionable.

    Returns False for:
    - Already awarded contracts (Award Notice)
    - Expired opportunities (response deadline passed)

    Args:
        opportunity: Opportunity dictionary

    Returns:
        True if opportunity is still actionable, False otherwise
    """
    from datetime import datetime

    # FILTER 1: Skip awarded opportunities
    status = opportunity.get("status", "").lower()
    notice_type = opportunity.get("notice_type", "").lower()

    if status == "awarded":
        title = opportunity.get("title", "unknown")
        logger.info(f"Skipping awarded opportunity: '{title}' (status=awarded)")
        return False

    if "award notice" in notice_type:
        title = opportunity.get("title", "unknown")
        logger.info(f"Skipping awarded opportunity: '{title}' (notice_type=Award Notice)")
        return False

    # FILTER 2: Skip expired opportunities (deadline passed)
    # TEMPORARILY DISABLED FOR TESTING - allows processing expired opportunities
    # TODO: Re-enable this filter after testing
    response_deadline = opportunity.get("response_deadline")

    # if response_deadline:
    #     try:
    #         # Parse deadline - supports multiple formats
    #         # Examples: "2026-03-08T15:00:00", "2026-03-08", "2026-03-08 15:00:00"
    #         deadline_str = response_deadline.replace("T", " ").split("+")[0].strip()
    #
    #         # Try parsing with time
    #         if " " in deadline_str:
    #             deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
    #         else:
    #             # Date only - set to end of day
    #             deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
    #             deadline_dt = deadline_dt.replace(hour=23, minute=59, second=59)
    #
    #         # Check if deadline has passed
    #         now = datetime.now()
    #         if deadline_dt < now:
    #             title = opportunity.get("title", "unknown")
    #             logger.info(f"Skipping expired opportunity: '{title}' (deadline: {response_deadline})")
    #             return False
    #
    #     except ValueError as e:
    #         # If we can't parse the date, log warning but don't filter out
    #         logger.warning(f"Could not parse response_deadline '{response_deadline}': {e}")

    return True


def map_status_to_temporal(status: str) -> str:
    """
    Map SAM.gov status to temporal_status.

    Args:
        status: SAM.gov status (forecasted, active, pre_solicitation, awarded, etc.)

    Returns:
        temporal_status: planned, in_progress, or completed
    """
    status_lower = status.lower() if status else ""

    # Future/planned opportunities
    if status_lower in ["forecasted", "pre_solicitation"]:
        return "planned"

    # Active solicitations (in progress)
    if status_lower in ["active"]:
        return "in_progress"

    # Completed/awarded
    if status_lower in ["awarded", "completed", "closed", "cancelled"]:
        return "completed"

    # Default to planned for unknown statuses
    return "planned"


def create_opportunity_event(
    opportunity: Dict[str, Any],
    file_path: str
) -> Optional[tuple[NormalizedEvent, str]]:
    """
    Create NormalizedEvent from a government opportunity.

    Args:
        opportunity: Opportunity dictionary
        file_path: Path to source file

    Returns:
        Tuple of (NormalizedEvent, opportunity_id) or None if data is insufficient
    """
    from src.utils.location_utils import normalize_state, normalize_city

    try:
        # FILTER 1: Skip non-office-space opportunities
        if not is_office_space_relevant(opportunity):
            return None

        # FILTER 2: Skip non-actionable opportunities (awarded or expired)
        if not is_opportunity_actionable(opportunity):
            return None

        # Extract opportunity_id for upsert
        opportunity_id = opportunity.get("opportunity_id") or opportunity.get("notice_id")
        if not opportunity_id:
            logger.warning("Opportunity missing opportunity_id, skipping")
            return None

        # Extract key data
        agency_name = extract_agency_name(opportunity)

        # PRIORITY 1: Try delineated_area for location (more accurate)
        delineated_area = opportunity.get("delineated_area")
        city, state = None, None

        if delineated_area and delineated_area.strip():
            # Parse delineated_area like "Fayetteville, AR" or "Berks County, PA"
            parts = [p.strip() for p in delineated_area.split(",")]
            if len(parts) >= 2:
                city = parts[0]
                state = parts[1]
                logger.info(f"Using delineated_area for location: {city}, {state}")

        # PRIORITY 2: Fallback to extract_location (city/state fields)
        if not (city and state):
            city, state = extract_location(opportunity)

        # Normalize location
        normalized_state = normalize_state(state) if state else None
        normalized_city = normalize_city(city) if city else None

        # Extract all fields
        title = opportunity.get("title", "")
        solicitation_number = opportunity.get("solicitation_number", "")
        source_url = opportunity.get("source_url")
        posted_date = opportunity.get("posted_date")
        response_deadline = opportunity.get("response_deadline")
        notice_type = opportunity.get("notice_type")
        status = opportunity.get("status")

        # Map status to temporal_status
        temporal_status = map_status_to_temporal(status)

        # Extract office size
        aboa_sf_min = opportunity.get("aboa_sf_min")
        aboa_sf_max = opportunity.get("aboa_sf_max")

        # Extract lease terms
        lease_term_years = opportunity.get("lease_term_years")
        firm_term_years = opportunity.get("firm_term_years")

        # Extract other details
        sub_agency = opportunity.get("sub_agency")
        award_amount = opportunity.get("award_amount")
        awardee_name = opportunity.get("awardee_name")
        parking_spaces = opportunity.get("parking_spaces")
        parking_reserved = opportunity.get("parking_reserved")
        tenant_improvement_allowance = opportunity.get("tenant_improvement_allowance")
        facility_security_level = opportunity.get("facility_security_level")
        is_aaap = opportunity.get("is_aaap", False)

        # Entity name is just the agency name (no location suffix)
        entity_name_raw = agency_name
        entity_name_canonical = agency_name.upper().replace(" ", "")

        # Build summary with normalized location and office size
        location_str = ""
        if normalized_city and normalized_state:
            location_str = f" in {normalized_city}, {normalized_state}"
        elif normalized_city:
            location_str = f" in {normalized_city}"
        elif normalized_state:
            location_str = f" in {normalized_state}"

        size_str = ""
        if aboa_sf_min and aboa_sf_max:
            if aboa_sf_min == aboa_sf_max:
                size_str = f" ({aboa_sf_min:,} sq ft)"
            else:
                size_str = f" ({aboa_sf_min:,}-{aboa_sf_max:,} sq ft)"
        elif aboa_sf_min:
            size_str = f" ({aboa_sf_min:,} sq ft)"

        summary = f"{agency_name} is seeking a new lease{location_str}{size_str}: {title}"

        # Build key facts with all structured data
        key_facts_dict = {}

        if normalized_city:
            key_facts_dict["city"] = normalized_city
        if normalized_state:
            key_facts_dict["state"] = normalized_state

        # Store office size in key_facts
        if aboa_sf_min:
            key_facts_dict["aboa_sf_min"] = aboa_sf_min
        if aboa_sf_max:
            key_facts_dict["aboa_sf_max"] = aboa_sf_max

        # Store award amount if awarded
        if award_amount:
            key_facts_dict["amount"] = f"${award_amount:,.2f}"

        # Store everything else in 'other' dict
        other_facts = {}

        if solicitation_number:
            other_facts["solicitation_number"] = solicitation_number
        if response_deadline:
            other_facts["response_deadline"] = response_deadline
        if notice_type:
            other_facts["notice_type"] = notice_type
        if status:
            other_facts["opportunity_status"] = status
        if delineated_area:
            other_facts["delineated_area"] = delineated_area
        if lease_term_years:
            other_facts["lease_term_years"] = lease_term_years
        if firm_term_years:
            other_facts["firm_term_years"] = firm_term_years
        if sub_agency:
            other_facts["sub_agency"] = sub_agency
        if awardee_name:
            other_facts["awardee_name"] = awardee_name
        if parking_spaces:
            other_facts["parking_spaces"] = parking_spaces
        if parking_reserved:
            other_facts["parking_reserved"] = parking_reserved
        if tenant_improvement_allowance:
            other_facts["tenant_improvement_allowance"] = tenant_improvement_allowance
        if facility_security_level:
            other_facts["facility_security_level"] = facility_security_level
        if is_aaap:
            other_facts["is_aaap"] = is_aaap

        if other_facts:
            key_facts_dict["other"] = other_facts

        # Add NAICS code if available
        naics_code = opportunity.get("naics_code")
        if naics_code and "other" in key_facts_dict:
            key_facts_dict["other"]["naics_code"] = naics_code

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
            temporal_status=temporal_status,  # Mapped from opportunity status
            summary=summary,
            key_facts=KeyFact(**key_facts_dict) if key_facts_dict else None,
            source_url=source_url,
            event_date=posted_date,
            extraction_confidence=1.0,  # Direct from structured data
            missing_fields=[],
            dynamic_signals=dynamic_signals
        )

        logger.info(f"Created event for {entity_name_raw} ({temporal_status}): {title}")
        return (event, opportunity_id)

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
        opportunity_ids = []
        for idx, opportunity_data in enumerate(opportunities, 1):
            logger.info(f"Processing opportunity {idx}/{len(opportunities)}: {opportunity_data.get('opportunity_id', 'unknown')}")

            result = create_opportunity_event(opportunity_data, file_path)
            if result:
                event, opportunity_id = result
                events.append(event)
                opportunity_ids.append(opportunity_id)

        logger.info(
            f"Processed {len(opportunities)} opportunities, "
            f"created {len(events)} events"
        )

        return {
            "status": "completed",
            "opportunities_processed": len(opportunities),
            "events_created": len(events),
            "events": events,
            "opportunity_ids": opportunity_ids  # For upsert logic
        }

    # No structured opportunities found - signal to use LLM extraction
    return {
        "status": "no_structured_data",
        "events": [],
        "opportunity_ids": []
    }
