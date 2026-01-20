"""Building demolition processor - finds companies at addresses and creates events."""
import logging
from typing import List, Optional, Dict, Any
import json

from src.llm.schemas import (
    BuildingInfo,
    BuildingExtractionResult,
    CompanyAtBuilding,
    NormalizedEvent,
    DynamicSignal,
    KeyFact
)
from src.llm.prompts import (
    BUILDING_EXTRACTION_SYSTEM_PROMPT,
    BUILDING_EXTRACTION_USER_PROMPT_TEMPLATE,
    COMPANY_SEARCH_EXTRACTION_SYSTEM_PROMPT,
    COMPANY_SEARCH_EXTRACTION_USER_PROMPT_TEMPLATE
)
from src.enrich.search_client import SearchClient, SearchResult
from src.config import (
    BUILDING_PROCESSING_ENABLED,
    BUILDING_COMPANY_SEARCH_MAX_RESULTS,
    BUILDING_EVENT_TYPE,
    LLM_MODEL_EXPENSIVE
)

logger = logging.getLogger(__name__)


def extract_building_info(
    content: str,
    file_path: str,
    llm_client: Any
) -> Optional[BuildingInfo]:
    """
    Extract building demolition information from document using LLM.

    Handles any format: JSON permits, HTML news, text articles, PDFs.

    Args:
        content: Document content
        file_path: Path to source file
        llm_client: LLM client for extraction

    Returns:
        BuildingInfo if demolition-related, None otherwise
    """
    if not BUILDING_PROCESSING_ENABLED:
        logger.info("Building processing is disabled")
        return None

    try:
        # Prepare prompts
        user_prompt = BUILDING_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            document_content=content[:20000],  # Limit content size
            file_path=file_path
        )

        # Call LLM
        logger.info(f"Extracting building info from {file_path}")
        response_text = llm_client.complete(
            system_prompt=BUILDING_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            model=LLM_MODEL_EXPENSIVE
        ).strip()

        # Handle markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON
        result_data = json.loads(response_text)
        result = BuildingExtractionResult(**result_data)

        # Check if demolition-related
        if not result.building_info or not result.building_info.is_demolition_related:
            logger.info(f"Document not demolition-related: {result.reasoning}")
            return None

        # Validate critical fields
        if not result.building_info.address or len(result.building_info.address.strip()) < 5:
            logger.warning(f"Building extraction missing address: {file_path}")
            return None

        logger.info(
            f"Extracted building: {result.building_info.address} "
            f"(confidence: {result.building_info.extraction_confidence:.2f})"
        )

        return result.building_info

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse building extraction JSON: {e}")
        logger.debug(f"Response was: {response_text[:500]}")
        return None
    except Exception as e:
        logger.error(f"Error extracting building info: {e}", exc_info=True)
        return None


def search_companies_at_address(
    building_info: BuildingInfo,
    search_client: SearchClient
) -> List[SearchResult]:
    """
    Search for companies at building address using web search.

    Uses multiple query strategies to maximize company discovery.

    Args:
        building_info: Building information with address
        search_client: Search client (Tavily/Exa/SerpAPI)

    Returns:
        List of search results about companies at the address
    """
    try:
        # Build multiple search queries
        queries = []

        # Base address search
        address = building_info.address.strip()
        queries.append(f"companies at {address}")
        queries.append(f"businesses located {address}")
        queries.append(f"{address} office directory")

        # Add building name if available
        if building_info.building_name:
            queries.append(f"{building_info.building_name} tenants")
            queries.append(f"{building_info.building_name} occupants")
            queries.append(f"companies in {building_info.building_name}")

        # Add city context if available
        if building_info.city:
            city_context = f"{building_info.city}"
            if building_info.state:
                city_context += f" {building_info.state}"
            queries.append(f"businesses {address} {city_context}")

        # Execute searches
        all_results = []
        max_results_per_query = max(3, BUILDING_COMPANY_SEARCH_MAX_RESULTS // len(queries))

        for query in queries:
            try:
                logger.info(f"Searching: {query}")
                results = search_client.search(query, max_results=max_results_per_query)
                all_results.extend(results)

                # Stop if we have enough results
                if len(all_results) >= BUILDING_COMPANY_SEARCH_MAX_RESULTS:
                    break

            except Exception as e:
                logger.warning(f"Search query failed '{query}': {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        logger.info(
            f"Found {len(unique_results)} unique search results for {building_info.address}"
        )

        return unique_results[:BUILDING_COMPANY_SEARCH_MAX_RESULTS]

    except Exception as e:
        logger.error(f"Error searching for companies: {e}", exc_info=True)
        return []


def extract_companies_from_search(
    search_results: List[SearchResult],
    building_info: BuildingInfo,
    llm_client: Any
) -> List[CompanyAtBuilding]:
    """
    Extract company list from search results using LLM.

    Args:
        search_results: Web search results
        building_info: Building information
        llm_client: LLM client for extraction

    Returns:
        List of companies found at the address
    """
    if not search_results:
        logger.warning("No search results to extract companies from")
        return []

    try:
        # Format search results for LLM
        formatted_results = []
        for i, result in enumerate(search_results, 1):
            formatted_results.append(
                f"[{i}] {result.title}\n"
                f"URL: {result.url}\n"
                f"Snippet: {result.snippet}\n"
            )
        search_results_text = "\n".join(formatted_results)

        # Prepare building name context
        building_name_context = ""
        if building_info.building_name:
            building_name_context = f"Building Name: {building_info.building_name}"

        # Prepare prompts
        user_prompt = COMPANY_SEARCH_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            address=building_info.address,
            building_name_context=building_name_context,
            search_results=search_results_text[:15000]  # Limit size
        )

        # Call LLM
        logger.info(f"Extracting companies from search results for {building_info.address}")
        logger.warning(f"[DEBUG] Sending {len(search_results)} search results to GPT-4o for company extraction")
        response_text = llm_client.complete(
            system_prompt=COMPANY_SEARCH_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            model=LLM_MODEL_EXPENSIVE
        ).strip()
        logger.warning(f"[DEBUG] Received GPT-4o response ({len(response_text)} chars)")

        # Handle markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON - handle both array and object formats
        try:
            parsed_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response (first 1000 chars): {response_text[:1000]}")
            return []

        # Log what we received for debugging (use WARNING so it shows in console)
        logger.warning(f"[DEBUG] GPT-4o response type: {type(parsed_data)}")
        logger.warning(f"[DEBUG] GPT-4o response preview: {str(parsed_data)[:500]}")

        # Handle different response formats
        if isinstance(parsed_data, dict):
            # If response is wrapped in an object, extract the array
            if "companies" in parsed_data:
                companies_data = parsed_data["companies"]
            elif "results" in parsed_data:
                companies_data = parsed_data["results"]
            else:
                # Single company object
                companies_data = [parsed_data]
        elif isinstance(parsed_data, list):
            companies_data = parsed_data
        else:
            logger.error(f"Unexpected response format: {type(parsed_data)}")
            logger.error(f"Response was: {str(parsed_data)[:500]}")
            return []

        # Log the companies data we're about to process
        logger.warning(f"[DEBUG] Companies data is a {type(companies_data).__name__} with length: {len(companies_data) if isinstance(companies_data, list) else 'N/A'}")

        # Validate and convert to CompanyAtBuilding objects
        companies = []
        for idx, company_dict in enumerate(companies_data):
            try:
                # Ensure we have a dictionary
                if not isinstance(company_dict, dict):
                    logger.warning(
                        f"Skipping non-dict company entry at index {idx}: "
                        f"type={type(company_dict)}, value={str(company_dict)[:200]}"
                    )
                    continue

                # Check for required fields
                if "company_name" not in company_dict:
                    logger.warning(
                        f"Skipping company entry at index {idx}: missing required field 'company_name'. "
                        f"Data: {str(company_dict)[:200]}"
                    )
                    continue

                if "extraction_confidence" not in company_dict:
                    # Default to 0.5 if missing
                    logger.debug(f"Setting default extraction_confidence for {company_dict.get('company_name')}")
                    company_dict["extraction_confidence"] = 0.5

                company = CompanyAtBuilding(**company_dict)

                # Filter by confidence threshold
                if company.extraction_confidence >= 0.5:
                    companies.append(company)
                else:
                    logger.debug(
                        f"Skipping low-confidence company: {company.company_name} "
                        f"(confidence: {company.extraction_confidence:.2f})"
                    )
            except Exception as e:
                logger.warning(f"Failed to parse company object: {e}")
                logger.debug(f"Company data was: {company_dict}")
                continue

        logger.info(f"Extracted {len(companies)} companies at {building_info.address}")

        return companies

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse company extraction JSON: {e}")
        logger.debug(f"Response was: {response_text[:500]}")
        return []
    except Exception as e:
        logger.error(f"Error extracting companies from search: {e}", exc_info=True)
        return []


def extract_location_from_permit_source(source: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract city and state from permit source field.

    Args:
        source: Source identifier (e.g., "miami_dade", "broward", "palm_beach")

    Returns:
        Tuple of (city, state)
    """
    source_lower = source.lower()

    # Known county/city mappings in Florida
    florida_sources = {
        'miami_dade': ('Miami', 'FL'),
        'miami-dade': ('Miami', 'FL'),
        'miamidade': ('Miami', 'FL'),
        'broward': ('Fort Lauderdale', 'FL'),
        'palm_beach': ('West Palm Beach', 'FL'),
        'orange': ('Orlando', 'FL'),
        'hillsborough': ('Tampa', 'FL'),
        'pinellas': ('St. Petersburg', 'FL'),
        'duval': ('Jacksonville', 'FL'),
    }

    for key, (city, state) in florida_sources.items():
        if key in source_lower:
            return city, state

    return None, None


def extract_state_from_address(address: str, city: Optional[str] = None) -> Optional[str]:
    """
    Extract state from address string.

    Args:
        address: Full address string
        city: City name if available

    Returns:
        State abbreviation or name
    """
    import re

    # Exclude street direction abbreviations
    excluded_codes = {'NW', 'NE', 'SW', 'SE', 'ST', 'RD', 'DR', 'AV', 'CT', 'LN', 'PL', 'WY'}

    # Pattern: Look for 2-letter state code followed by optional ZIP
    # Must not be preceded by numbers (to avoid "88 ST")
    state_pattern = r'(?<!\d)\b([A-Z]{2})\b(?:\s+\d{5})?'
    matches = re.findall(state_pattern, address)

    # Filter out excluded codes and return first valid state
    for match in matches:
        if match not in excluded_codes:
            # Verify it's a valid state code
            valid_states = {
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
                'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
            }
            if match in valid_states:
                return match

    # Full state names as fallback
    states = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'puerto rico': 'PR'
    }

    address_lower = address.lower()
    for state_name, state_code in states.items():
        if state_name in address_lower:
            return state_code

    return None


def create_company_events(
    companies: List[CompanyAtBuilding],
    building_info: BuildingInfo,
    raw_file_path: str
) -> List[NormalizedEvent]:
    """
    Create NormalizedEvent for each company found at the building.

    Each company gets an event indicating they need to relocate due to demolition.
    Entity names are just company names (no location suffix).
    Location is stored in key_facts and used for LocationLead aggregation.

    Args:
        companies: List of companies at the building
        building_info: Building information
        raw_file_path: Path to source file

    Returns:
        List of NormalizedEvent objects
    """
    from src.utils.location_utils import normalize_state, normalize_city

    events = []

    # Normalize location data
    normalized_state = normalize_state(building_info.state)
    normalized_city = normalize_city(building_info.city)

    for company in companies:
        try:
            # Entity name is just the company name (no location suffix)
            entity_name_raw = company.company_name
            entity_name_canonical = company.company_name.upper().strip()

            # Build summary
            summary_parts = [
                f"{company.company_name} needs to relocate due to building demolition"
            ]
            if building_info.demolition_date:
                summary_parts.append(f"scheduled for {building_info.demolition_date}")

            summary = " ".join(summary_parts)

            # Build key facts - include normalized location
            key_facts_dict = {
                "current_address": building_info.address,
            }

            if company.suite_or_floor:
                key_facts_dict["suite"] = company.suite_or_floor

            if building_info.demolition_date:
                key_facts_dict["demolition_date"] = building_info.demolition_date
            elif building_info.estimated_date:
                key_facts_dict["estimated_demolition"] = building_info.estimated_date

            if building_info.demolition_reason:
                key_facts_dict["demolition_reason"] = building_info.demolition_reason

            if building_info.permit_id:
                key_facts_dict["permit_id"] = building_info.permit_id

            # Add normalized location to key_facts
            if normalized_city:
                key_facts_dict["city"] = normalized_city
            if normalized_state:
                key_facts_dict["state"] = normalized_state

            # Create dynamic signal for office relocation urgency
            dynamic_signals = [
                DynamicSignal(
                    signal_type="office_relocation_urgent",
                    description=f"Building demolition forcing relocation from {building_info.address}",
                    evidence_quote=company.evidence_quote or f"Located at {building_info.address}"
                )
            ]

            # Add building name signal if available
            if building_info.building_name:
                dynamic_signals.append(
                    DynamicSignal(
                        signal_type="building_name",
                        description=f"Located in {building_info.building_name}",
                        evidence_quote=None
                    )
                )

            # Prepare entity metadata
            entity_metadata = {}
            if company.website:
                entity_metadata["website_url"] = company.website
            if company.domain:
                entity_metadata["potential_domain"] = company.domain
            if company.phone:
                entity_metadata["phone"] = company.phone
            if building_info.source_url:
                entity_metadata["demolition_source_url"] = building_info.source_url

            # Create normalized event with location-based entity name
            event = NormalizedEvent(
                entity_name_raw=entity_name_raw,
                entity_name_canonical=entity_name_canonical,
                entity_type="company",
                entity_metadata=entity_metadata if entity_metadata else None,
                event_type=BUILDING_EVENT_TYPE,
                summary=summary,
                key_facts=KeyFact(**key_facts_dict),
                source_url=building_info.source_url,
                event_date=building_info.demolition_date or building_info.estimated_date,
                extraction_confidence=company.extraction_confidence,
                missing_fields=[],
                dynamic_signals=dynamic_signals
            )

            events.append(event)

            logger.debug(
                f"Created event for {company.company_name} at {building_info.address}"
            )

        except Exception as e:
            logger.error(
                f"Error creating event for company {company.company_name}: {e}",
                exc_info=True
            )
            continue

    logger.info(f"Created {len(events)} events for companies at {building_info.address}")

    return events


def parse_permits_from_json(content: str) -> List[Dict[str, Any]]:
    """
    Parse permits from JSON file.

    Handles both:
    - Structured format: {"permits": [...]}
    - Single permit: {...}
    - Plain text/HTML (returns empty list to fall back to LLM)

    Args:
        content: File content

    Returns:
        List of permit dictionaries
    """
    try:
        data = json.loads(content)

        # Check for permits array
        if isinstance(data, dict) and "permits" in data:
            permits = data["permits"]
            if isinstance(permits, list):
                logger.info(f"Found {len(permits)} permits in structured JSON")
                return permits

        # Single permit object
        if isinstance(data, dict):
            # Check if it looks like a permit (has address or permit-related fields)
            if any(key in data for key in ["address", "permit_type", "id", "folio"]):
                logger.info("Found single permit in JSON")
                return [data]

        logger.info("JSON doesn't contain permit structure, will use LLM extraction")
        return []

    except json.JSONDecodeError:
        # Not JSON - could be HTML, text, PDF, etc.
        logger.info("Content is not JSON, will use LLM extraction")
        return []


def process_single_permit(
    permit_data: Dict[str, Any],
    permit_index: int,
    total_permits: int,
    llm_client: Any,
    search_client: SearchClient,
    file_path: str
) -> Dict[str, Any]:
    """
    Process a single permit to find companies at the building.

    Args:
        permit_data: Permit dictionary with address, id, etc.
        permit_index: Index of this permit (for logging)
        total_permits: Total number of permits being processed
        llm_client: LLM client
        search_client: Search client
        file_path: Source file path

    Returns:
        Dict with processing results
    """
    from src.utils.location_utils import normalize_state

    logger.info(f"Processing permit {permit_index}/{total_permits}: {permit_data.get('id', 'unknown')}")

    # Extract key fields from permit
    address = permit_data.get("address", "").strip()
    permit_id = permit_data.get("id")
    issue_date = permit_data.get("issue_date")
    description = permit_data.get("description", "").strip()
    source = permit_data.get("source", "")

    if not address or len(address) < 5:
        logger.warning(f"Permit {permit_id} has invalid address: {address}")
        return {
            "status": "skipped",
            "reason": "invalid_address",
            "permit_id": permit_id,
            "events": []
        }

    # Extract location from source field (e.g., "miami_dade" → Miami, FL)
    city_from_source, state_from_source = extract_location_from_permit_source(source)

    # Normalize state
    normalized_state = normalize_state(state_from_source) if state_from_source else None

    # Use city from permit data or fallback to source
    city = permit_data.get("city") or city_from_source

    # Create BuildingInfo from permit data with normalized location
    building_info = BuildingInfo(
        address=address,
        building_name=None,
        city=city,
        state=normalized_state,  # Normalized state code
        is_demolition_related=True,
        demolition_date=issue_date,
        demolition_reason=description,
        permit_id=permit_id,
        source_url=None,
        extraction_confidence=1.0  # Direct from permit data
    )

    # Search for companies at this address
    search_results = search_companies_at_address(building_info, search_client)

    if not search_results:
        logger.warning(f"No search results for {address}")
        return {
            "status": "completed",
            "reason": "no_search_results",
            "permit_id": permit_id,
            "address": address,
            "events": []
        }

    # Extract companies from search results
    companies = extract_companies_from_search(search_results, building_info, llm_client)

    if not companies:
        logger.warning(f"No companies found at {address}")
        return {
            "status": "completed",
            "reason": "no_companies_found",
            "permit_id": permit_id,
            "address": address,
            "events": []
        }

    # Create events for each company
    events = create_company_events(companies, building_info, file_path)

    logger.info(f"Permit {permit_id}: Found {len(companies)} companies, created {len(events)} events")

    return {
        "status": "completed",
        "permit_id": permit_id,
        "address": address,
        "companies_found": len(companies),
        "events_created": len(events),
        "events": events
    }


def process_building_document(
    content: str,
    file_path: str,
    llm_client: Any,
    search_client: SearchClient
) -> Dict[str, Any]:
    """
    Complete building document processing pipeline.

    Handles two modes:
    1. Structured JSON with permits array - processes each permit separately
    2. Unstructured text/HTML - uses LLM to extract building info

    Args:
        content: Document content
        file_path: Path to source file
        llm_client: LLM client
        search_client: Search client

    Returns:
        Dict with processing results and list of events
    """
    # Try to parse as structured permits JSON first
    permits = parse_permits_from_json(content)

    if permits:
        # Process all permits in the file
        logger.info(f"Processing {len(permits)} permits from structured JSON")

        all_events = []
        total_companies = 0
        permits_with_companies = 0

        for idx, permit_data in enumerate(permits, 1):
            result = process_single_permit(
                permit_data=permit_data,
                permit_index=idx,
                total_permits=len(permits),
                llm_client=llm_client,
                search_client=search_client,
                file_path=file_path
            )

            if result.get("events"):
                all_events.extend(result["events"])
                total_companies += result.get("companies_found", 0)
                permits_with_companies += 1

        logger.info(
            f"Processed {len(permits)} permits: "
            f"{permits_with_companies} had companies, "
            f"{total_companies} total companies, "
            f"{len(all_events)} events created"
        )

        return {
            "status": "completed",
            "permits_processed": len(permits),
            "permits_with_companies": permits_with_companies,
            "companies_found": total_companies,
            "events_created": len(all_events),
            "events": all_events
        }

    # Fallback: Use LLM to extract building info from unstructured content
    logger.info("No structured permits found, using LLM extraction")

    result = {
        "status": "completed",
        "building_address": None,
        "companies_found": 0,
        "events_created": 0,
        "events": []
    }

    # Step 1: Extract building info with LLM
    building_info = extract_building_info(content, file_path, llm_client)

    if not building_info:
        result["status"] = "skipped"
        result["reason"] = "not_demolition_related"
        return result

    result["building_address"] = building_info.address

    # Step 2: Search for companies at address
    search_results = search_companies_at_address(building_info, search_client)

    if not search_results:
        logger.warning(f"No search results found for {building_info.address}")
        result["status"] = "completed"
        result["reason"] = "no_search_results"
        return result

    # Step 3: Extract companies from search results
    companies = extract_companies_from_search(search_results, building_info, llm_client)

    if not companies:
        logger.warning(f"No companies extracted from search for {building_info.address}")
        result["status"] = "completed"
        result["reason"] = "no_companies_found"
        return result

    result["companies_found"] = len(companies)

    # Step 4: Create events for each company
    events = create_company_events(companies, building_info, file_path)

    result["events_created"] = len(events)
    result["events"] = events

    logger.info(
        f"Building processing complete: {building_info.address} -> "
        f"{len(companies)} companies, {len(events)} events"
    )

    return result
