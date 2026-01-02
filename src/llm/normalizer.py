"""LLM-based document normalization and extraction."""
import json
import hashlib
from typing import Optional, Dict, Any
from pydantic import ValidationError

from src.config import LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY, BUSINESS_OBJECTIVE
from src.llm.schemas import NormalizedEvent, DocumentExtraction, get_normalized_name
from src.llm.prompts import (
    EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
    EXTRACTION_USER_PROMPT_TEMPLATE,
    JSON_REPAIR_SYSTEM_PROMPT,
    JSON_REPAIR_USER_PROMPT_TEMPLATE
)


class LLMClient:
    """Abstraction for LLM providers."""

    def __init__(self, provider: str = None):
        self.provider = provider or LLM_PROVIDER

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Get completion from LLM."""
        if self.provider == "openai":
            return self._openai_complete(system_prompt, user_prompt, temperature)
        elif self.provider == "anthropic":
            return self._anthropic_complete(system_prompt, user_prompt, temperature)
        elif self.provider == "mock":
            return self._mock_complete(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _openai_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """OpenAI completion."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def _anthropic_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Anthropic completion."""
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

    def _mock_complete(self, system_prompt: str, user_prompt: str) -> str:
        """Mock completion for testing without API keys."""
        # Generate deterministic mock response based on input
        # For enrichment prompts (different structure)
        if "Find official web presence" in user_prompt or "Extract the official domain" in user_prompt:
            return json.dumps({
                "official_domain": "acmecloud.io",
                "website_url": "https://www.acmecloud.io",
                "linkedin_url": "https://www.linkedin.com/company/acme-cloud",
                "hq_location": "San Francisco, California",
                "enrichment_confidence": 0.95,
                "reasoning": "Multiple consistent sources confirm acmecloud.io as official domain"
            })

        # Check if this is a DocumentExtraction request (has business objective in system prompt)
        if "BUSINESS OBJECTIVE" in system_prompt:
            # Return DocumentExtraction format with is_relevant, relevance_reasoning, and events array

            # Test case 1: Highly relevant - funding + hiring + expansion
            if "dataflow systems" in user_prompt.lower() or "75m series c" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": True,
                    "relevance_reasoning": "Funding round ($75M) paired with plans to triple headcount and secure larger office space - strong office expansion signals",
                    "events": [{
                        "company_name_raw": "DataFlow Systems",
                        "company_name_canonical": "DATAFLOW SYSTEMS",
                        "event_type": "funding_round",
                        "summary": "DataFlow Systems raised $75M Series C and plans to triple headcount from 85 to 250 employees, requiring larger office space.",
                        "key_facts": {
                            "amount": "$75M Series C",
                            "location": "Austin, Texas",
                            "people": ["Jessica Martinez"],
                            "dates": ["November 10, 2025"],
                            "companies": ["Sequoia Capital", "Andreessen Horowitz"]
                        },
                        "source_url": None,
                        "event_date": "2025-11-10",
                        "extraction_confidence": 0.95,
                        "missing_fields": [],
                        "dynamic_signals": [
                            {
                                "signal_type": "hiring_surge",
                                "description": "Plans to triple headcount from 85 to 250 employees",
                                "evidence_quote": "plans to triple its headcount from 85 to 250 employees"
                            },
                            {
                                "signal_type": "office_expansion",
                                "description": "Currently searching for larger office space",
                                "evidence_quote": "The company is actively searching for a larger office space"
                            }
                        ]
                    }]
                })

            # Test case 2: Not relevant - personal blog
            elif "my top 10 productivity hacks" in user_prompt.lower() or "wake up at 5am" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": False,
                    "relevance_reasoning": "Personal blog post about productivity tips - not about a company or organization",
                    "events": []
                })

            # Test case 3: Not relevant - company homepage
            elif "cloudnova" in user_prompt.lower() and "empower your team" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": False,
                    "relevance_reasoning": "Company marketing homepage with no news or events - no office space signals",
                    "events": []
                })

            # Test case 4: Company but not relevant - product launch
            elif "mobilefirst games" in user_prompt.lower() or "galaxy raiders" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": False,
                    "relevance_reasoning": "Product launch announcement with no hiring, funding, or office expansion signals",
                    "events": []
                })

            # Test case 5: Company but not relevant - award
            elif "greentech solutions" in user_prompt.lower() and "sustainability award" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": False,
                    "relevance_reasoning": "Company award/recognition with no growth signals or office space implications",
                    "events": []
                })

            # Test case 6: Highly relevant - multi-company acquisition
            elif "techcorp" in user_prompt.lower() and "visionlabs" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": True,
                    "relevance_reasoning": "Acquisition with employee relocation and office integration - strong office space signals for both companies",
                    "events": [
                        {
                            "company_name_raw": "TechCorp",
                            "company_name_canonical": "TECHCORP",
                            "event_type": "acquisition",
                            "summary": "TechCorp acquired VisionLabs for $150M, relocating 85 employees to SF headquarters.",
                            "key_facts": {
                                "amount": "$150M",
                                "location": "San Francisco, CA",
                                "people": ["Tom Richardson"],
                                "dates": ["December 1, 2025"],
                                "companies": ["VisionLabs"]
                            },
                            "source_url": None,
                            "event_date": "2025-12-01",
                            "extraction_confidence": 0.92,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "office_integration",
                                    "description": "Integrating 85 VisionLabs employees into SF headquarters",
                                    "evidence_quote": "relocating VisionLabs' 85 employees from Boston to TechCorp's San Francisco headquarters"
                                },
                                {
                                    "signal_type": "office_expansion",
                                    "description": "SF office at full capacity, considering expansion",
                                    "evidence_quote": "TechCorp's SF office is currently at full capacity, and the company is considering leasing additional floors"
                                }
                            ]
                        },
                        {
                            "company_name_raw": "VisionLabs",
                            "company_name_canonical": "VISIONLABS",
                            "event_type": "acquisition",
                            "summary": "VisionLabs acquired by TechCorp for $150M, employees relocating to San Francisco.",
                            "key_facts": {
                                "amount": "$150M",
                                "location": "Boston, MA → San Francisco, CA",
                                "people": None,
                                "dates": ["December 1, 2025"],
                                "companies": ["TechCorp"]
                            },
                            "source_url": None,
                            "event_date": "2025-12-01",
                            "extraction_confidence": 0.92,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "office_closure",
                                    "description": "Boston office closing, team moving to SF",
                                    "evidence_quote": "VisionLabs' Boston office will be closed"
                                },
                                {
                                    "signal_type": "employee_relocation",
                                    "description": "85 employees relocating from Boston to San Francisco",
                                    "evidence_quote": "relocating VisionLabs' 85 employees from Boston to TechCorp's San Francisco headquarters"
                                }
                            ]
                        }
                    ]
                })

            # Test case 7: Highly relevant - layoffs + downsizing
            elif "streamtech" in user_prompt.lower() and "layoffs" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": True,
                    "relevance_reasoning": "Layoffs (30% workforce) with explicit office downsizing from 85k to 40k sq ft - clear office space reduction signal",
                    "events": [{
                        "company_name_raw": "StreamTech",
                        "company_name_canonical": "STREAMTECH",
                        "event_type": "layoffs",
                        "summary": "StreamTech laid off 30% of workforce and downsizing office from 85,000 to 40,000 sq ft.",
                        "key_facts": {
                            "amount": "120 employees (30% of workforce)",
                            "location": "Seattle, WA",
                            "people": ["Robert Kim"],
                            "dates": ["November 28, 2025"],
                            "companies": None
                        },
                        "source_url": None,
                        "event_date": "2025-11-28",
                        "extraction_confidence": 0.94,
                        "missing_fields": [],
                        "dynamic_signals": [
                            {
                                "signal_type": "office_downsizing",
                                "description": "Downsizing from 85,000 sq ft to 40,000 sq ft office",
                                "evidence_quote": "The company is downsizing its Seattle office from 85,000 square feet to 40,000 square feet"
                            },
                            {
                                "signal_type": "remote_work_transition",
                                "description": "Shifting to remote-first model",
                                "evidence_quote": "StreamTech is shifting to a remote-first work model"
                            }
                        ]
                    }]
                })

            # Test case 8: Company but not relevant - partnership without office impact
            elif "shopeasy" in user_prompt.lower() and "paymentpro" in user_prompt.lower():
                return json.dumps({
                    "is_relevant": False,
                    "relevance_reasoning": "Marketing partnership announcement with no hiring, expansion, or office space implications",
                    "events": []
                })

            # Test case 9: Highly relevant - international expansion with new offices
            elif "cybershield" in user_prompt.lower() or ("london" in user_prompt.lower() and "singapore" in user_prompt.lower() and "toronto" in user_prompt.lower()):
                return json.dumps({
                    "is_relevant": True,
                    "relevance_reasoning": "Opening 3 new international offices with plans to hire 200 employees - direct office expansion signals",
                    "events": [{
                        "company_name_raw": "CyberShield",
                        "company_name_canonical": "CYBERSHIELD",
                        "event_type": "expansion",
                        "summary": "CyberShield opening offices in London, Singapore, and Toronto, hiring 200 employees across three locations.",
                        "key_facts": {
                            "amount": "200 new employees across 3 offices",
                            "location": "London, UK; Singapore; Toronto, Canada",
                            "people": ["Jennifer Lee", "Mark Peterson"],
                            "dates": ["Q1 2026"],
                            "companies": None
                        },
                        "source_url": None,
                        "event_date": "2026-01-15",
                        "extraction_confidence": 0.96,
                        "missing_fields": [],
                        "dynamic_signals": [
                            {
                                "signal_type": "office_expansion",
                                "description": "Opening 3 new international offices (London, Singapore, Toronto)",
                                "evidence_quote": "opening in Q1 2026 to support surging global demand"
                            },
                            {
                                "signal_type": "hiring_surge",
                                "description": "Hiring 200 employees across new locations",
                                "evidence_quote": "plans to hire approximately 200 employees across the three locations"
                            },
                            {
                                "signal_type": "hq_expansion",
                                "description": "Austin HQ expanding by 30,000 sq ft",
                                "evidence_quote": "CyberShield signing a lease for an additional 30,000 square feet adjacent to its current 50,000 square foot office"
                            }
                        ]
                    }]
                })

            # Test case 10: Multiple event types for same company (timeline)
            elif "techflow" in user_prompt.lower() and ("120 million series d" in user_prompt.lower() or "datapipe solutions" in user_prompt.lower()):
                return json.dumps({
                    "is_relevant": True,
                    "relevance_reasoning": "Multiple major events (funding, acquisition, layoffs, office consolidation) with clear office space implications over 6-month timeline",
                    "events": [
                        {
                            "company_name_raw": "TechFlow Inc.",
                            "company_name_canonical": "TECHFLOW",
                            "event_type": "funding_round",
                            "summary": "TechFlow Inc. raised $120M Series D led by Tiger Global and Sequoia Capital for product roadmap and international expansion.",
                            "key_facts": {
                                "amount": "$120M Series D",
                                "location": None,
                                "people": ["Maria Rodriguez"],
                                "dates": ["March 15, 2025"],
                                "companies": ["Tiger Global Management", "Sequoia Capital"]
                            },
                            "source_url": None,
                            "event_date": "2025-03-15",
                            "extraction_confidence": 0.95,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "international_expansion",
                                    "description": "Capital designated for international expansion",
                                    "evidence_quote": "This capital will accelerate our product roadmap and international expansion"
                                }
                            ]
                        },
                        {
                            "company_name_raw": "TechFlow Inc.",
                            "company_name_canonical": "TECHFLOW",
                            "event_type": "acquisition",
                            "summary": "TechFlow Inc. acquired DataPipe Solutions for $45M, integrating 35 employees and Toronto office.",
                            "key_facts": {
                                "amount": "$45M",
                                "location": "Toronto, Canada",
                                "people": ["Maria Rodriguez"],
                                "dates": ["June 8, 2025"],
                                "companies": ["DataPipe Solutions"]
                            },
                            "source_url": None,
                            "event_date": "2025-06-08",
                            "extraction_confidence": 0.94,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "office_integration",
                                    "description": "Toronto office to be integrated by Q4 2025",
                                    "evidence_quote": "The DataPipe Toronto office will be integrated into TechFlow's operations by Q4 2025"
                                },
                                {
                                    "signal_type": "employee_growth",
                                    "description": "35 DataPipe employees joining engineering team",
                                    "evidence_quote": "The deal brings 35 DataPipe employees into TechFlow's engineering team"
                                }
                            ]
                        },
                        {
                            "company_name_raw": "TechFlow Inc.",
                            "company_name_canonical": "TECHFLOW",
                            "event_type": "layoffs",
                            "summary": "TechFlow Inc. laid off 18% of workforce (150 employees) and consolidating offices from 3 to 2 hubs.",
                            "key_facts": {
                                "amount": "150 employees (18% of workforce)",
                                "location": "Multiple offices",
                                "people": ["James Mitchell"],
                                "dates": ["August 22, 2025"],
                                "companies": None
                            },
                            "source_url": None,
                            "event_date": "2025-08-22",
                            "extraction_confidence": 0.96,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "office_consolidation",
                                    "description": "Consolidating 3 regional offices into 2 larger hubs",
                                    "evidence_quote": "the company is consolidating three regional offices into two larger hubs to optimize operations and reduce overhead costs"
                                },
                                {
                                    "signal_type": "office_expansion",
                                    "description": "New 65,000 sq ft Austin office (replacing 40k + closing 35k Dallas)",
                                    "evidence_quote": "TechFlow has signed a new lease for 65,000 square feet in downtown Austin, Texas, consolidating employees from its existing 40,000 sq ft Austin office and the soon-to-close 35,000 sq ft Dallas office"
                                },
                                {
                                    "signal_type": "employee_relocation",
                                    "description": "85 Dallas employees relocating to Austin or going remote",
                                    "evidence_quote": "Approximately 85 Dallas-based employees will either relocate to Austin or transition to remote work"
                                }
                            ]
                        }
                    ]
                })

            if "acme" in user_prompt.lower():
                # Check which document based on content
                if "series b" in user_prompt.lower() or "50m" in user_prompt.lower():
                    return json.dumps({
                        "is_relevant": True,
                        "relevance_reasoning": "Funding round paired with expansion plans indicates strong office space needs",
                        "events": [{
                            "company_name_raw": "Acme Cloud Inc.",
                            "company_name_canonical": "ACME CLOUD",
                            "event_type": "funding_round",
                            "summary": "Acme Cloud Inc. raised $50M in Series B funding led by Venture Capital Partners.",
                            "key_facts": {
                                "amount": "$50M",
                                "location": "San Francisco, CA",
                                "people": ["Sarah Chen"],
                                "dates": ["December 15, 2025"],
                                "companies": ["Venture Capital Partners", "TechFund", "Innovation Capital"]
                            },
                            "source_url": "https://technews.example.com/acme-cloud-funding-2025",
                            "event_date": "2025-12-15",
                            "extraction_confidence": 0.95,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "acquisition_negotiation",
                                    "description": "Company in advanced negotiations to acquire StreamOps Technologies",
                                    "evidence_quote": "sources close to the company revealed that Acme Cloud is in advanced negotiations to acquire a smaller competitor, StreamOps Technologies"
                                },
                                {
                                    "signal_type": "market_expansion",
                                    "description": "Plans to expand into European market",
                                    "evidence_quote": "The company plans to use the funds to accelerate product development and expand into the European market"
                                },
                                {
                                    "signal_type": "customer_growth",
                                    "description": "Tripled customer base to over 500 enterprise clients",
                                    "evidence_quote": "tripling its customer base to over 500 enterprise clients"
                                }
                            ]
                        }]
                    })
                elif "partnership" in user_prompt.lower() or "globaltech" in user_prompt.lower():
                    return json.dumps({
                        "is_relevant": True,
                        "relevance_reasoning": "Strategic partnership with leadership additions suggests company growth and potential office expansion",
                        "events": [{
                            "company_name_raw": "acme cloud llc",
                            "company_name_canonical": "ACME CLOUD",
                            "event_type": "partnership",
                            "summary": "acme cloud llc announced strategic partnership with GlobalTech Enterprises worth $15M over 3 years.",
                            "key_facts": {
                                "amount": "$15M over 3 years",
                                "location": "San Francisco (implied)",
                                "people": ["Sarah Chen", "Michael Torres", "Dr. Lisa Wang"],
                                "dates": ["December 18, 2025"],
                                "companies": ["GlobalTech Enterprises"]
                            },
                            "source_url": None,
                            "event_date": "2025-12-18",
                            "extraction_confidence": 0.88,
                            "missing_fields": ["source_url"],
                            "dynamic_signals": [
                                {
                                    "signal_type": "leadership_addition",
                                    "description": "Hired new CRO Michael Torres and VP Engineering Dr. Lisa Wang",
                                    "evidence_quote": "Appointed new Chief Revenue Officer: Michael Torres (former VP Sales at CloudScale); Hired VP of Engineering: Dr. Lisa Wang (previously at Google Cloud)"
                                },
                                {
                                    "signal_type": "government_expansion",
                                    "description": "Job postings suggest entry into federal/government sector",
                                    "evidence_quote": "Company recently posted job openings for 'Federal Sales Specialist' and 'GovCloud Compliance Manager'"
                                },
                                {
                                    "signal_type": "new_product_line",
                                    "description": "Trademark filing for 'Acme SecureCloud' indicates new security-focused product",
                                    "evidence_quote": "Trademark filing for 'Acme SecureCloud' detected (suggests new product line)"
                                },
                                {
                                    "signal_type": "technology_adoption",
                                    "description": "Migrated to Kubernetes and implemented AI/ML capabilities",
                                    "evidence_quote": "Company has migrated entire infrastructure to Kubernetes-based architecture; Implemented advanced AI/ML capabilities"
                                },
                                {
                                    "signal_type": "patent_filing",
                                    "description": "Filed 3 new patents for cloud cost optimization",
                                    "evidence_quote": "Filed 3 new patents related to cloud cost optimization (USPTO filing Dec 2025)"
                                }
                            ]
                        }]
                    })
                elif "job" in user_prompt.lower() or "hiring" in user_prompt.lower():
                    return json.dumps({
                        "is_relevant": True,
                        "relevance_reasoning": "Hiring surge with international expansion strongly indicates office space needs",
                        "events": [{
                            "company_name_raw": "ACME CLOUD",
                            "company_name_canonical": "ACME CLOUD",
                            "event_type": "hiring_surge",
                            "summary": "ACME CLOUD is rapidly hiring with 47 active job postings, including significant EMEA expansion roles.",
                            "key_facts": {
                                "amount": "47 active postings, 35 new in last 30 days",
                                "location": "San Francisco, CA; London, UK; Amsterdam, NL; Austin, TX",
                                "people": None,
                                "dates": ["December 2025"],
                                "companies": None
                            },
                            "source_url": "https://www.acmecloud.io",
                            "event_date": "2025-12-20",
                            "extraction_confidence": 0.9,
                            "missing_fields": [],
                            "dynamic_signals": [
                                {
                                    "signal_type": "international_expansion",
                                    "description": "Multiple EMEA-focused sales roles suggest European market entry",
                                    "evidence_quote": "Multiple EMEA-focused sales and customer success roles suggest European market entry"
                                },
                                {
                                    "signal_type": "office_expansion",
                                    "description": "New Austin, TX office location appearing in job postings",
                                    "evidence_quote": "New Austin, TX office location appearing in recent job postings"
                                },
                                {
                                    "signal_type": "employee_growth",
                                    "description": "35.7% headcount growth from 210 to 285 employees",
                                    "evidence_quote": "current_employee_count_estimate: 285, previous_quarter_estimate: 210, growth_rate: 35.7%"
                                }
                            ]
                        }]
                    })

            # Generic fallback - not relevant
            return json.dumps({
                "is_relevant": False,
                "relevance_reasoning": "Document does not contain relevant signals for office space prediction",
                "events": []
            })

        # Legacy format for old prompts (shouldn't happen but keeping for safety)
        return json.dumps({
            "company_name_raw": "Unknown Company",
            "company_name_canonical": "UNKNOWN COMPANY",
            "event_type": "other",
            "summary": "Unable to extract event information",
            "extraction_confidence": 0.3,
            "missing_fields": ["all"],
            "dynamic_signals": []
        })


class Normalizer:
    """Document normalization and event extraction."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def normalize_document(
        self,
        content: str,
        file_path: str,
        source: str = "unknown"
    ) -> Optional[DocumentExtraction]:
        """
        Normalize a document into structured events (may extract multiple companies).

        Args:
            content: Raw document content
            file_path: Path to the document
            source: Source identifier

        Returns:
            DocumentExtraction (contains relevance + list of events) or None if extraction fails
        """
        # Build system prompt with business objective
        system_prompt = EXTRACTION_SYSTEM_PROMPT_TEMPLATE.format(
            business_objective=BUSINESS_OBJECTIVE
        )

        # Build user prompt
        user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            document_content=content,
            file_path=file_path,
            source=source
        )

        try:
            # Get LLM response
            response = self.llm.complete(system_prompt, user_prompt)

            # Parse JSON
            try:
                data = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"⚠ JSON decode error, attempting repair: {str(e)}")
                data = self._repair_json(response)

            # Validate with Pydantic
            extraction = DocumentExtraction(**data)

            return extraction

        except ValidationError as e:
            print(f"✗ Validation error for {file_path}: {str(e)}")
            return None
        except Exception as e:
            print(f"✗ Normalization error for {file_path}: {str(e)}")
            return None

    def _repair_json(self, malformed_json: str) -> Dict[str, Any]:
        """Attempt to repair malformed JSON."""
        schema_desc = NormalizedEvent.model_json_schema()

        repair_prompt = JSON_REPAIR_USER_PROMPT_TEMPLATE.format(
            malformed_json=malformed_json,
            schema_description=json.dumps(schema_desc, indent=2)
        )

        response = self.llm.complete(JSON_REPAIR_SYSTEM_PROMPT, repair_prompt)

        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])  # Remove first and last line

        return json.loads(response)


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
