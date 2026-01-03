"""Entity enrichment using web search and LLM."""
import json
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.llm.normalizer import LLMClient
from src.llm.schemas import EnrichmentResult
from src.llm.prompts import ENRICHMENT_SYSTEM_PROMPT, ENRICHMENT_USER_PROMPT_TEMPLATE
from src.enrich.search_client import SearchClient, format_search_results_for_llm
from src.config import ENRICHMENT_FRESHNESS_DAYS


class Enricher:
    """Enrich entities with web-sourced information."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        search_client: Optional[SearchClient] = None
    ):
        self.llm = llm_client or LLMClient()
        self.search = search_client or SearchClient()

    def should_enrich(
        self,
        entity_domain: Optional[str],
        last_enriched_at: Optional[datetime],
        missing_fields: List[str] = None
    ) -> bool:
        """
        Determine if entity should be enriched.

        Args:
            entity_domain: Current domain value
            last_enriched_at: When entity was last enriched
            missing_fields: List of missing critical fields

        Returns:
            True if enrichment needed
        """
        # No domain = definitely enrich
        if not entity_domain:
            return True

        # Missing critical fields = enrich
        if missing_fields:
            return True

        # Check freshness
        if last_enriched_at:
            freshness_threshold = datetime.utcnow() - timedelta(days=ENRICHMENT_FRESHNESS_DAYS)
            if last_enriched_at < freshness_threshold:
                return True

        return False

    def enrich_entity(
        self,
        canonical_name: str,
        alternative_names: List[str] = None
    ) -> Optional[EnrichmentResult]:
        """
        Enrich entity by searching the web and extracting official presence.

        Args:
            canonical_name: Canonical company name
            alternative_names: List of alternative name variants

        Returns:
            EnrichmentResult or None if enrichment fails
        """
        # Build search queries - one for website, one for HQ location
        website_query = self._build_search_query(canonical_name, query_type="website")
        hq_query = self._build_search_query(canonical_name, query_type="headquarters")

        print(f"  → Searching for: {website_query}")
        print(f"  → Searching for: {hq_query}")

        # Search for both
        website_results = self.search.search(website_query, max_results=5)
        hq_results = self.search.search(hq_query, max_results=3)

        # Combine results (website results first, then HQ results)
        search_results = website_results + hq_results

        if not search_results:
            print(f"  ⚠ No search results found")
            return None

        print(f"  ✓ Found {len(website_results)} website results, {len(hq_results)} HQ results")

        # Format results for LLM
        formatted_results = format_search_results_for_llm(search_results)

        # Build enrichment prompt
        alt_names = alternative_names or []
        user_prompt = ENRICHMENT_USER_PROMPT_TEMPLATE.format(
            canonical_name=canonical_name,
            alternative_names=", ".join(alt_names) if alt_names else "None",
            search_results=formatted_results
        )

        try:
            # Get LLM response
            response = self.llm.complete(ENRICHMENT_SYSTEM_PROMPT, user_prompt)

            # Parse JSON
            # Strip markdown if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            data = json.loads(response)

            # Validate
            enrichment = EnrichmentResult(**data)

            print(f"  ✓ Enrichment complete (confidence: {enrichment.enrichment_confidence:.2f})")
            if enrichment.official_domain:
                print(f"    Domain: {enrichment.official_domain}")

            return enrichment

        except (json.JSONDecodeError, ValidationError) as e:
            print(f"  ✗ Enrichment parsing error: {str(e)}")
            return None
        except Exception as e:
            print(f"  ✗ Enrichment error: {str(e)}")
            return None

    def _build_search_query(self, canonical_name: str, query_type: str = "website") -> str:
        """
        Build effective search query for company.

        Args:
            canonical_name: Company name
            query_type: Type of query - "website" or "headquarters"

        Returns:
            Search query string
        """
        if query_type == "headquarters":
            # Specific query for HQ location
            query = f"{canonical_name} headquarters location address"
        else:
            # General query for company website/info
            query = f"{canonical_name} official website company"

        return query
