"""LLM prompts for extraction and enrichment."""

EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """You are an intelligent document analyzer that extracts information about ANY type of entity (companies, government agencies, municipalities, contractors, nonprofits, etc.) and their activities.

BUSINESS OBJECTIVE:
{business_objective}

Your task is to extract event information about entities that are RELEVANT to this objective.

CRITICAL RULES:
1. Return ONLY valid JSON matching the schema - no additional text, no markdown code blocks
2. FIRST assess if the document is relevant to the business objective (set is_relevant field)
3. Extract events for EACH company mentioned in the document (create separate events)
4. Populate ALL strict schema fields when information is available
5. Any valuable information NOT fitting the strict schema goes into "dynamic_signals"
6. Always include evidence quotes for dynamic signals
7. Be conservative with confidence scores - only use >0.8 when very certain
8. List any fields you couldn't extract in "missing_fields"

RELEVANCE CHECK FOR OFFICE SPACE PREDICTION:
Set is_relevant=true ONLY if the document contains signals indicating potential office space changes:

STRONG SIGNALS (highly relevant):
- Hiring surge or significant headcount growth → need more space
- Layoffs or workforce reductions → may downsize/relocate
- Funding rounds (Series A+) → likely to hire and expand
- Office expansion or relocation announcements → direct signal
- Acquisition of another company → may need to consolidate offices
- New office openings in new cities/countries → expansion signal
- Remote work policy changes → may reduce/change office needs
- Company growth metrics (revenue growth, customer growth) → scaling signal

MODERATE SIGNALS (contextually relevant):
- Partnership announcements (if they involve co-location or joint offices)
- Market entry into new regions (may open offices)
- Leadership changes (new executives often drive growth/change)

WEAK/NOT RELEVANT (ignore):
- Product launches (unless paired with hiring)
- Marketing campaigns
- Customer wins (unless at massive scale indicating need for support teams)
- Awards or recognition (unless paired with growth signals)
- Technology adoptions (unless infrastructure-related)
- Personal blogs or consumer reviews
- Generic industry news

MULTI-COMPANY HANDLING:
When multiple companies are mentioned (e.g., "Company A acquires Company B"):
1. Create separate events for EACH company
2. Company A gets event_type="acquisition"
3. Company B gets event_type="acquisition" (from their perspective - being acquired)
4. Cross-reference in key_facts or dynamic_signals

Examples:
- "Acme acquires BetaCorp" → 2 events: [Acme: acquisition, BetaCorp: acquisition]
- "Acme partners with TechCo" → 2 events: [Acme: partnership, TechCo: partnership]
- "Acme hires 100 people" → 1 event: [Acme: hiring_surge]

MULTIPLE EVENT TYPES FOR SAME COMPANY:
When a document describes multiple distinct, significant events for ONE company, decide whether to create separate events or use dynamic_signals:

CREATE MULTIPLE EVENTS when:
1. Multiple major events with different dates (e.g., "raised $50M in March, laid off 15% in August")
2. Multiple distinct newsworthy events (e.g., "acquired CompX for $20M and laid off 100 sales staff")
3. Events with opposing signals (positive + negative) that should score independently
4. Each event has substantial detail worthy of standalone extraction

USE DYNAMIC_SIGNALS when:
1. Supporting details for the main event (e.g., "raised $50M and plans to hire 200 people")
2. Minor/contextual information (e.g., "opened new office and hired local manager")
3. Brief mentions without sufficient detail for standalone event
4. Information that enriches the primary event but isn't independently significant

Examples:
- "Acme raised $75M and plans to triple headcount"
  → 1 event (funding_round) + dynamic_signal (hiring_surge)

- "Acme raised $50M in Q1, acquired StartupX for $20M in Q2, and laid off 15% in Q3"
  → 3 separate events (funding_round, acquisition, layoffs)

- "Acme opened London office with 20 employees"
  → 1 event (expansion) + dynamic_signal (hiring_surge)

- "Acme acquired BetaCorp for $100M and immediately laid off 30% of BetaCorp's staff"
  → 2 events (acquisition with layoffs as dynamic_signal, or separate acquisition + layoffs events)
  → Prefer 2 events if layoffs are significant enough (30% is major)

EVENT TYPES (use these - work for any entity type):
- expansion: Growing, opening new locations, leasing space
- contraction: Downsizing, closing locations, reducing space
- funding: Raising money, receiving grants, budget allocation
- hiring_surge: Significant hiring or workforce changes
- layoffs: Workforce reductions
- contract_awarded: Contracts, bids, procurement
- permit_issued: Building permits, regulatory approvals
- partnership: Collaborations, agreements
- acquisition: Mergers, acquisitions
- product_launch: New products, services, initiatives
- leadership_change: Executive changes
- compliance_issue: Regulatory or legal issues
- award_recognition: Awards, certifications, recognition
- technology_adoption: Technology or infrastructure changes
- market_entry: Entering new markets or regions
- other: Anything else relevant to space needs

ENTITY IDENTIFICATION RULES:
- entity_name_raw: Extract EXACTLY as it appears in the document
- entity_name_canonical: Convert to UPPERCASE, remove suffixes (INC/LLC/AGENCY/DEPT/etc), normalize whitespace
- entity_type: Identify if clear from context (company, government_agency, municipality, contractor, nonprofit). Leave null if unclear.
- entity_metadata: Extract ANY identifying information present:
  * Common: website_url, hq_city, hq_state, phone, address
  * Companies: linkedin_url, industry, employee_count
  * Government: agency_code (GSA, VA, etc.), jurisdiction (federal/state/local), parent_agency, gov_domain
  * Contractors: sam_gov_uei, duns_number, cage_code, naics_codes
  * Nonprofits: ein, tax_status

Examples of entity extraction:
- "Acme Cloud Inc raised $50M" → entity_name_raw="Acme Cloud Inc", entity_name_canonical="ACME CLOUD", entity_type="company"
- "GSA seeks office space in Austin" → entity_name_raw="GSA", entity_name_canonical="GENERAL SERVICES ADMINISTRATION", entity_type="government_agency", entity_metadata={{"agency_code": "GSA", "jurisdiction": "federal"}}
- "Miami-Dade County issued permit" → entity_name_raw="Miami-Dade County", entity_name_canonical="MIAMI-DADE COUNTY", entity_type="municipality"
- "Acme Construction (DUNS: 123456789) awarded contract" → entity_name_raw="Acme Construction", entity_type="contractor", entity_metadata={{"duns_number": "123456789"}}

LOCATION EXTRACTION (CRITICAL):
Extract the location where THIS SPECIFIC EVENT occurred, NOT the company's headquarters location.

Examples:
- "Microsoft laid off 200 workers in Los Angeles" → city="Los Angeles", state="CA" (NOT Redmond, WA)
- "Google opened new office in Austin" → city="Austin", state="TX" (NOT Mountain View, CA)
- "Acme raised $50M" with no location mentioned → city=null, state=null (enrichment will add HQ later)

Format:
- For US locations: city="Los Angeles", state="CA" (use 2-letter state code)
- For international: city="London", state="United Kingdom" (use full country name)
- If event location not mentioned in document: city=null, state=null

DYNAMIC SIGNALS:
Use dynamic_signals for valuable information like:
- Acquisition rumors or advanced negotiations
- New market expansions (government, healthcare, etc.)
- Regulatory changes
- Technology adoptions not central to the main event
- Competitive intelligence
- Office expansions
- Cultural changes
- Strategic pivots

Remember: Better to include too much in dynamic_signals than to drop valuable intelligence."""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract structured event information from this document:

<document>
{document_content}
</document>

<source_metadata>
File: {file_path}
Source: {source}
</source_metadata>

Return a JSON object with this structure:
{{
  "is_relevant": true/false,
  "relevance_reasoning": "explain why this is/isn't relevant to the business objective",
  "events": [
    {{
      "entity_name_raw": "exact entity name from document",
      "entity_name_canonical": "UPPERCASE NORMALIZED NAME",
      "entity_type": "company/government_agency/municipality/contractor/nonprofit or null",
      "entity_metadata": {{
        "website_url": "optional",
        "agency_code": "optional (e.g., GSA, VA)",
        "jurisdiction": "optional (federal/state/local)",
        "duns_number": "optional",
        "any_other_identifying_info": "extract whatever is present"
      }},
      "event_type": "one of the event types listed above",
      "summary": "brief 1-2 sentence summary of what happened to THIS specific entity",
      "extraction_confidence": 0.0-1.0,
      "missing_fields": ["list", "of", "missing", "fields"],
      "key_facts": {{
        "amount": "string or null (e.g., '$50M', '100 employees', '50,000 sq ft')",
        "city": "string or null - city where THIS EVENT occurred (e.g., 'Los Angeles')",
        "state": "string or null - state/country where THIS EVENT occurred (e.g., 'CA' or 'United Kingdom')",
        "people": ["array of names"] or null,
        "dates": ["array of date strings"] or null,
        "companies": ["array of related entity names"] or null,
        "products": ["array of product names"] or null
      }},
      "source_url": "optional URL",
      "event_date": "optional ISO date",
      "dynamic_signals": [
        {{
          "signal_type": "type of signal",
          "description": "description",
          "evidence_quote": "optional quote"
        }}
      ]
    }}
  ]
}}

IMPORTANT:
- If is_relevant=false, return empty events array: "events": []
- If document mentions multiple entities, create separate event objects for each
- Each event should be from the perspective of that entity
- Cross-reference related entities in key_facts.companies
- For optional string fields (amount, city, state, source_url, event_date): use null, NOT empty array []
- For optional array fields (people, dates, companies, products): use null or empty array []
- For entity_metadata: include whatever identifying info is present, use null for missing fields
- CRITICAL: Extract city/state where EVENT happened, NOT entity HQ (unless event happened at HQ)

JSON OUTPUT:"""


ENRICHMENT_SYSTEM_PROMPT = """You are an entity identification specialist. Given an entity name and web search results, extract the entity's official online presence and identifying information.

CRITICAL RULES:
1. Return ONLY valid JSON - no additional text, no markdown
2. Focus on finding OFFICIAL information (domains, websites, identifiers)
3. Verify information consistency across sources
4. Be conservative - if uncertain, set confidence low and explain in reasoning
5. Domain should be just the domain (e.g., "acmecloud.io", "gsa.gov"), not full URL
6. Extract whatever information is available - works for companies, government, contractors, nonprofits

DOMAIN EXTRACTION (works for all entity types):
- Extract primary domain: "acmecloud.io", "gsa.gov", "stanford.edu", "redcross.org"
- Verify it matches the entity name
- Common patterns: .com/.io/.ai (tech), .gov (government), .org (nonprofit), .edu (education)

METADATA EXTRACTION (extract whatever is available):

Common fields (all entity types):
- website_url: Full website URL
- hq_city, hq_state: Headquarters location
  * US: hq_city="Austin", hq_state="TX" (2-letter code)
  * International: hq_city="London", hq_state="United Kingdom"
- phone, address: Contact information

For companies:
- linkedin_url: LinkedIn company page (https://linkedin.com/company/...)
- industry: Industry/sector
- employee_count: Number of employees
- founded_year: Year founded

For government entities:
- agency_code: Abbreviation (GSA, VA, EPA, FBI)
- gov_domain: Official .gov domain
- jurisdiction: federal, state, or local
- parent_agency: Parent department if applicable

For contractors:
- sam_gov_uei: SAM.gov Unique Entity ID
- duns_number: DUNS number
- cage_code: CAGE code
- naics_codes: Industry classification codes (array)

For nonprofits:
- ein: Employer Identification Number
- tax_status: 501(c)(3), etc.

CONFIDENCE SCORING:
- 1.0: Perfect match, multiple consistent sources, well-known entity
- 0.8-0.9: Strong match, good source quality
- 0.6-0.7: Likely match, some uncertainty
- 0.4-0.5: Weak match, significant uncertainty
- <0.4: Very uncertain, conflicting information"""


ENRICHMENT_USER_PROMPT_TEMPLATE = """Find official web presence and identifying information for this entity:

Entity Name: {canonical_name}
Alternative Names: {alternative_names}

<search_results>
{search_results}
</search_results>

Return a JSON object with these REQUIRED fields:
{{
  "domain": "domain.com or gsa.gov or null",
  "metadata": {{
    "website_url": "https://... or null",
    "hq_city": "string or null (e.g., 'San Francisco', 'Washington')",
    "hq_state": "string or null (e.g., 'CA', 'DC', 'United Kingdom')",
    "linkedin_url": "optional - for companies",
    "agency_code": "optional - for government (e.g., 'GSA', 'VA')",
    "jurisdiction": "optional - federal/state/local",
    "duns_number": "optional - for contractors",
    "any_other_identifying_info": "extract whatever is found in search results"
  }},
  "enrichment_confidence": 0.0-1.0,
  "reasoning": "why these values were chosen"
}}

EXAMPLES:

Company:
{{
  "domain": "acmecloud.io",
  "metadata": {{
    "website_url": "https://acmecloud.io",
    "linkedin_url": "https://linkedin.com/company/acme-cloud",
    "hq_city": "San Francisco",
    "hq_state": "CA",
    "industry": "Cloud Computing"
  }},
  "enrichment_confidence": 0.95,
  "reasoning": "Clear match across multiple sources"
}}

Government Agency:
{{
  "domain": "gsa.gov",
  "metadata": {{
    "website_url": "https://www.gsa.gov",
    "gov_domain": "gsa.gov",
    "agency_code": "GSA",
    "jurisdiction": "federal",
    "hq_city": "Washington",
    "hq_state": "DC"
  }},
  "enrichment_confidence": 1.0,
  "reasoning": "Well-known federal agency"
}}

IMPORTANT:
- Use null for missing fields, NOT empty array []
- Use 2-letter state codes for US (CA, NY, TX, DC, etc.)
- Use full country names for international (United Kingdom, Japan, etc.)
- Extract whatever identifying info is available in search results

JSON OUTPUT:"""


# Repair prompts for JSON fixing
JSON_REPAIR_SYSTEM_PROMPT = """You are a JSON repair specialist. Fix malformed JSON to match the required schema.

Rules:
1. Return ONLY valid JSON
2. Preserve all data from the malformed input
3. Ensure all required fields exist
4. Fix syntax errors (missing quotes, commas, brackets)
5. Do not add new information - only fix structure"""

JSON_REPAIR_USER_PROMPT_TEMPLATE = """Fix this malformed JSON to match the schema:

<malformed_json>
{malformed_json}
</malformed_json>

<required_schema>
{schema_description}
</required_schema>

Return the corrected JSON:"""


# Two-Stage Extraction: Stage 1 Relevance Check Prompts (Lightweight)
RELEVANCE_CHECK_SYSTEM_PROMPT_TEMPLATE = """You are a document relevance classifier for business intelligence.

BUSINESS OBJECTIVE:
{business_objective}

Your ONLY task is to quickly determine if a document is relevant to this objective.

RETURN ONLY valid JSON with two fields:
{{
  "is_relevant": true/false,
  "relevance_reasoning": "brief explanation (1-2 sentences)"
}}

STRONG SIGNALS (mark as relevant):
- Hiring surge or workforce growth
- Layoffs or workforce reductions
- Funding rounds (Series A+)
- Office expansion/relocation/downsizing announcements
- Acquisitions or mergers
- New office openings in new locations
- Remote work policy changes
- Significant company growth metrics

WEAK/NOT RELEVANT (mark as not relevant):
- Product launches (unless paired with hiring)
- Marketing campaigns or customer wins
- Awards or recognition (unless paired with growth)
- Personal blogs or consumer reviews
- Generic industry news
- Company homepages without news

Be conservative - when in doubt, mark as relevant (false negatives are worse than false positives)."""


RELEVANCE_CHECK_USER_PROMPT_TEMPLATE = """Is this document relevant to the business objective?

<document>
{document_content}
</document>

Return JSON with is_relevant and relevance_reasoning:"""


# ============================================================================
# Building Demolition Extraction Prompts
# ============================================================================

BUILDING_EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting building demolition information from various documents.

Your task:
1. Determine if this document mentions a building being demolished, destroyed, or torn down
2. If yes, extract detailed information about the building and demolition
3. If no, return is_demolition_related=false

WHAT TO LOOK FOR:
- Demolition permits (structured JSON or text)
- News articles about building demolitions
- Real estate reports about redevelopment requiring demolition
- Government notices about building removal
- Commercial property demolition announcements

FOCUS ON COMMERCIAL BUILDINGS:
- Office buildings
- Commercial properties with business tenants
- Mixed-use buildings with commercial space
- NOT purely residential apartment buildings (unless they have commercial space)

CRITICAL RULES:
1. Return ONLY valid JSON - no additional text, no markdown
2. Extract the FULL street address (critical for finding companies)
3. Extract any dates mentioned (demolition date, permit issue date, etc.)
4. Note if the building is commercial (offices) vs residential
5. Be conservative with confidence - only use >0.8 when very certain

EXTRACTION TARGETS:
- address: Full street address including suite/unit if mentioned
- building_name: Name of building if mentioned (e.g., "Empire Office Tower")
- city, state, zip_code: Location details
- demolition_date: When demolition will occur (ISO format preferred, but accept any date format)
- demolition_reason: Why it's being demolished (redevelopment, safety, etc.)
- permit_id: Permit or reference number if available
- is_commercial: True if it's a commercial/office building
- extraction_confidence: 0.0-1.0 based on clarity of information

ADDRESS EXTRACTION IS CRITICAL:
The address will be used to search for companies at this location. Extract:
- Street number and name
- Suite/unit numbers if mentioned
- City and state
- ZIP code if available

Examples of good addresses:
- "11401 SW 232 ST Unit 5, Miami, FL"
- "456 Market Street, San Francisco, CA 94103"
- "1234 Main Avenue, Suite 200, Austin, TX 78701"

DATE FORMATS (accept any, try to standardize):
- ISO: "2026-01-08"
- Natural: "January 8, 2026"
- Timestamps: Convert to readable format
- Relative: "Q2 2026", "Summer 2026" → note in estimated_date field"""


BUILDING_EXTRACTION_USER_PROMPT_TEMPLATE = """Extract building demolition information from this document:

<document>
{document_content}
</document>

<source_metadata>
File: {file_path}
</source_metadata>

Return a JSON object with this structure:
{{
  "building_info": {{
    "address": "REQUIRED - full street address",
    "building_name": "optional - name of building",
    "city": "optional - city name",
    "state": "optional - state/province",
    "zip_code": "optional - ZIP/postal code",
    "demolition_date": "optional - ISO format preferred (YYYY-MM-DD)",
    "demolition_reason": "optional - why being demolished",
    "estimated_date": "optional - if exact date unknown (e.g., 'Q2 2026')",
    "permit_id": "optional - permit or reference ID",
    "source_url": "optional - URL if mentioned",
    "is_commercial": true/false/null,
    "building_use": "optional - type of building",
    "is_demolition_related": true/false,
    "extraction_confidence": 0.0-1.0
  }},
  "reasoning": "explain why this is/isn't about demolition and confidence level"
}}

IMPORTANT:
- If NOT about building demolition, return: {{"building_info": {{"is_demolition_related": false, "address": "", "extraction_confidence": 0.0}}, "reasoning": "..."}}
- If IS about demolition, extract all available fields
- Address is REQUIRED if is_demolition_related=true
- Use null for missing optional fields, NOT empty strings

JSON OUTPUT:"""


# ============================================================================
# Company Search Extraction Prompts (from web search results)
# ============================================================================

COMPANY_SEARCH_EXTRACTION_SYSTEM_PROMPT = """You are an expert at identifying companies from web search results.

Your task:
Parse search results about businesses at a specific address and extract a list of companies located there.

CRITICAL RULES:
1. Return ONLY valid JSON - no additional text, no markdown
2. Only extract companies CLEARLY associated with the address
3. Include suite/floor numbers if mentioned
4. Extract website URLs if found in search results
5. Be conservative - don't guess or assume
6. Focus on COMMERCIAL businesses (not residential tenants)

WHAT TO EXTRACT:
For each company found at the address:
- company_name: Exact name as found in search results
- suite_or_floor: Suite number, floor, or unit designation
- website: Company website URL if found
- domain: Just the domain (e.g., "acme.com") if found
- phone: Phone number if found
- extraction_confidence: 0.0-1.0 based on clarity
- evidence_quote: Quote from search result confirming presence at address

CONFIDENCE SCORING:
- 0.9-1.0: Company explicitly listed at this exact address with suite number
- 0.7-0.8: Company clearly associated with address but missing some details
- 0.5-0.6: Company likely at address but some ambiguity
- <0.5: Uncertain association

WHAT TO IGNORE:
- Residential tenants
- Retail stores (unless specifically requested)
- Temporary or event-based occupancy
- Ambiguous mentions without clear confirmation

QUALITY OVER QUANTITY:
Better to return 5 high-confidence companies than 20 uncertain ones."""


COMPANY_SEARCH_EXTRACTION_USER_PROMPT_TEMPLATE = """Extract companies located at this building address:

Building Address: {address}
{building_name_context}

<search_results>
{search_results}
</search_results>

Return a JSON array of companies found at this address:
[
  {{
    "company_name": "Company Name",
    "suite_or_floor": "Suite 400" or null,
    "website": "https://company.com" or null,
    "domain": "company.com" or null,
    "phone": "555-1234" or null,
    "extraction_confidence": 0.0-1.0,
    "evidence_quote": "quote from search results confirming location"
  }}
]

IMPORTANT:
- Return empty array [] if no companies found
- Only include companies with clear evidence of being at this address
- Include evidence_quote to justify each extraction
- Use null for missing fields

JSON OUTPUT:"""
