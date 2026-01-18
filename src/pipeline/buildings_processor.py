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


def create_company_events(
    companies: List[CompanyAtBuilding],
    building_info: BuildingInfo,
    raw_file_path: str
) -> List[NormalizedEvent]:
    """
    Create NormalizedEvent for each company found at the building.

    Each company gets an event indicating they need to relocate due to demolition.

    Args:
        companies: List of companies at the building
        building_info: Building information
        raw_file_path: Path to source file

    Returns:
        List of NormalizedEvent objects
    """
    events = []

    for company in companies:
        try:
            # Build summary
            summary_parts = [
                f"{company.company_name} needs to relocate due to building demolition"
            ]
            if building_info.demolition_date:
                summary_parts.append(f"scheduled for {building_info.demolition_date}")

            summary = " ".join(summary_parts)

            # Build key facts
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

            if building_info.city:
                key_facts_dict["city"] = building_info.city

            if building_info.state:
                key_facts_dict["state"] = building_info.state

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

            # Create normalized event
            event = NormalizedEvent(
                entity_name_raw=company.company_name,
                entity_name_canonical=company.company_name.upper().strip(),
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


def process_building_document(
    content: str,
    file_path: str,
    llm_client: Any,
    search_client: SearchClient
) -> Dict[str, Any]:
    """
    Complete building document processing pipeline.

    Steps:
    1. Extract building info (LLM)
    2. Search for companies at address (Web Search)
    3. Extract company list (LLM)
    4. Create events for each company

    Args:
        content: Document content
        file_path: Path to source file
        llm_client: LLM client
        search_client: Search client

    Returns:
        Dict with processing results and list of events
    """
    result = {
        "status": "completed",
        "building_address": None,
        "companies_found": 0,
        "events_created": 0,
        "events": []
    }

    # Step 1: Extract building info
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
