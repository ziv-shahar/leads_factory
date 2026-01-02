"""LLM prompts for extraction and enrichment."""

EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """You are a professional business intelligence analyst extracting structured information from documents.

BUSINESS OBJECTIVE:
{business_objective}

Your task is to extract event information about companies/organizations that are RELEVANT to this objective.

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

EVENT TYPES (use these exactly):
- funding_round
- partnership
- expansion
- product_launch
- acquisition
- hiring_surge
- layoffs
- leadership_change
- compliance_issue
- award_recognition
- technology_adoption
- market_entry
- other

COMPANY NAME RULES:
- company_name_raw: Extract EXACTLY as it appears in the document
- company_name_canonical: Convert to UPPERCASE, remove legal suffixes (INC/LLC/LTD/CORP/CO), normalize whitespace

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
      "company_name_raw": "exact company name from document",
      "company_name_canonical": "UPPERCASE NORMALIZED NAME",
      "event_type": "one of the event types listed above",
      "summary": "brief 1-2 sentence summary of what happened to THIS specific company",
      "extraction_confidence": 0.0-1.0,
      "missing_fields": ["list", "of", "missing", "fields"],
      "key_facts": {{
        "amount": "optional",
        "location": "optional",
        "people": ["optional"],
        "dates": ["optional"],
        "companies": ["other companies involved"],
        "products": ["optional"]
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
- If document mentions multiple companies, create separate event objects for each
- Each event should be from the perspective of that company
- Cross-reference related companies in key_facts.companies

JSON OUTPUT:"""


ENRICHMENT_SYSTEM_PROMPT = """You are a company identification specialist. Given a company name and web search results, extract the company's official online presence.

CRITICAL RULES:
1. Return ONLY valid JSON - no additional text, no markdown
2. Focus on finding the OFFICIAL domain/website
3. Verify information consistency across sources
4. Be conservative - if uncertain, set confidence low and explain in reasoning
5. Domain should be just the domain (e.g., "acmecloud.io"), not full URL

DOMAIN EXTRACTION:
- Extract the primary domain (e.g., "acmecloud.io" not "www.acmecloud.io")
- Verify it matches the company name
- Prefer .com, .io, .ai for tech companies; .org for nonprofits; country TLDs for local companies

LINKEDIN:
- Extract the full company page URL (e.g., "https://www.linkedin.com/company/acme-cloud")
- Must be /company/ page, not personal profiles

CONFIDENCE SCORING:
- 1.0: Perfect match, multiple consistent sources
- 0.8-0.9: Strong match, good source quality
- 0.6-0.7: Likely match, some uncertainty
- 0.4-0.5: Weak match, significant uncertainty
- <0.4: Very uncertain, conflicting information"""


ENRICHMENT_USER_PROMPT_TEMPLATE = """Find official web presence for this company:

Company Name: {canonical_name}
Alternative Names: {alternative_names}

<search_results>
{search_results}
</search_results>

Return a JSON object with these REQUIRED fields:
{{
  "official_domain": "domain.com or null",
  "website_url": "https://... or null",
  "linkedin_url": "https://linkedin.com/company/... or null",
  "hq_location": "City, State/Country or null",
  "enrichment_confidence": 0.0-1.0,
  "reasoning": "why these values were chosen"
}}

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
