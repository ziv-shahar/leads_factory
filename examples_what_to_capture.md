# Examples: What to Capture vs What to Ignore

This document clarifies which events should be extracted for office space prediction and which should be ignored.

## ❌ PARTNERSHIPS - What NOT to Capture

### Technology Integrations (IGNORE)
These are pure software/product partnerships with **zero** office space implications:

1. **Walmart partners with Google for AI shopping in Gemini app**
   - ❌ IGNORE
   - Reason: Tech integration, no physical presence, no hiring
   - Impact: None - users access features digitally

2. **Nike partners with Apple for fitness tracking**
   - ❌ IGNORE
   - Reason: Software/hardware integration, no office needs
   - Impact: None - just API/data integration

3. **Starbucks partners with Spotify for in-store music**
   - ❌ IGNORE
   - Reason: Service partnership, no new employees or offices
   - Impact: None - existing staff use existing systems

4. **Bank integrates with fintech for payment processing**
   - ❌ IGNORE
   - Reason: Backend software integration
   - Impact: None - no physical infrastructure

5. **Retailer announces partnership with delivery service**
   - ❌ IGNORE (unless it mentions opening distribution centers)
   - Reason: Outsourced service, no company facilities
   - Impact: None - delivery company handles logistics

### Marketing Collaborations (IGNORE)
6. **Brands collaborate on limited edition product**
   - ❌ IGNORE
   - Reason: Product collaboration, manufactured elsewhere
   - Impact: None - no new offices or staff

7. **Company partners for co-marketing campaign**
   - ❌ IGNORE
   - Reason: Marketing agreement, no physical presence
   - Impact: None - digital/advertising only

### Data/Content Partnerships (IGNORE)
8. **Media company partners with news aggregator**
   - ❌ IGNORE
   - Reason: Content licensing, no office space needed
   - Impact: None - digital content sharing

9. **Research partnership to share datasets**
   - ❌ IGNORE
   - Reason: Data exchange, no co-location
   - Impact: None - researchers work from existing offices

## ✅ PARTNERSHIPS - What TO Capture

### Physical Co-location (EXTRACT)
These partnerships require actual physical space:

1. **Acme and BetaCo announce joint innovation lab in Austin with 300 researchers**
   - ✅ EXTRACT
   - Reason: New physical facility + 300 employees
   - Impact: HIGH - new office space needed
   - temporal_status: "planned"

2. **Companies form joint venture requiring shared R&D facility**
   - ✅ EXTRACT
   - Reason: Physical shared space required
   - Impact: MEDIUM - office co-location

3. **Partnership to open 5 new distribution centers in Southeast**
   - ✅ EXTRACT
   - Reason: Physical warehouses/facilities
   - Impact: HIGH - multiple new buildings

### Manufacturing/Production (EXTRACT)
4. **Automaker partners to build EV battery factory in Michigan**
   - ✅ EXTRACT
   - Reason: New manufacturing plant
   - Impact: HIGH - large industrial facility

5. **Partnership to establish semiconductor fab in Arizona**
   - ✅ EXTRACT
   - Reason: Major production facility
   - Impact: VERY HIGH - massive industrial complex

### Regional Expansion (EXTRACT if staffing mentioned)
6. **Partnership to expand into APAC region with local offices in 3 countries**
   - ✅ EXTRACT
   - Reason: Multiple new offices
   - Impact: HIGH - international expansion

7. **Regional partnership requiring 200 local sales staff**
   - ✅ EXTRACT
   - Reason: Hiring 200 people → office space needed
   - Impact: MEDIUM - new regional office

## ❌ PRODUCT LAUNCHES - What NOT to Capture

### Software/Digital Products (IGNORE)
1. **Company launches new mobile app**
   - ❌ IGNORE
   - Reason: Digital product, existing team built it
   - Impact: None - no new office space

2. **SaaS company announces new feature set**
   - ❌ IGNORE
   - Reason: Software update, no expansion
   - Impact: None

3. **New subscription tier launched**
   - ❌ IGNORE
   - Reason: Pricing change, not expansion
   - Impact: None

### Consumer Products (IGNORE unless massive scale)
4. **Brand launches new product line**
   - ❌ IGNORE (unless mentions hiring 100+ people)
   - Reason: Product expansion doesn't always mean office expansion
   - Impact: Minimal - usually existing staff

## ✅ PRODUCT LAUNCHES - What TO Capture

### Launches Paired with Hiring (EXTRACT)
1. **Company launches autonomous vehicle division, hiring 500 engineers**
   - ✅ EXTRACT
   - Reason: New division + 500 hires = office space needed
   - Impact: HIGH
   - event_type: "hiring_surge"

2. **New product line requiring 200 manufacturing workers**
   - ✅ EXTRACT
   - Reason: Significant hiring
   - Impact: MEDIUM
   - event_type: "expansion"

### New Facilities (EXTRACT)
3. **Product launch requires new production facility in Texas**
   - ✅ EXTRACT
   - Reason: New physical facility
   - Impact: HIGH
   - event_type: "expansion"

## ❌ LEADERSHIP CHANGES - Usually Ignore

### Standard Executive Changes (IGNORE)
1. **Company appoints new CFO**
   - ❌ IGNORE
   - Reason: Single hire, no office expansion
   - Impact: None

2. **CEO steps down, COO promoted**
   - ❌ IGNORE
   - Reason: Internal promotion, no growth signal
   - Impact: None

3. **New VP of Marketing hired**
   - ❌ IGNORE
   - Reason: Single executive, not predictive
   - Impact: None

## ✅ LEADERSHIP CHANGES - When to Capture

### Paired with Growth Plans (EXTRACT)
1. **New CEO hired to drive international expansion**
   - ✅ EXTRACT (only if expansion details provided)
   - Reason: Explicit expansion mandate
   - Impact: MEDIUM
   - temporal_status: "planned"

2. **Company hires Chief Growth Officer and plans to triple headcount**
   - ✅ EXTRACT
   - Reason: Explicit hiring plan
   - Impact: HIGH
   - event_type: "hiring_surge"

## ❌ AWARDS/RECOGNITION - Almost Always Ignore

1. **Company named "Best Place to Work"**
   - ❌ IGNORE
   - Reason: Recognition, not growth
   - Impact: None

2. **Product wins industry award**
   - ❌ IGNORE
   - Reason: Recognition, not expansion
   - Impact: None

3. **Executive wins leadership award**
   - ❌ IGNORE
   - Reason: Personal recognition
   - Impact: None

## ❌ TECHNOLOGY ADOPTION - Almost Always Ignore

1. **Company migrates to cloud infrastructure**
   - ❌ IGNORE
   - Reason: Infrastructure change, reduces physical servers
   - Impact: None (may even reduce data center needs)

2. **Enterprise adopts new CRM system**
   - ❌ IGNORE
   - Reason: Software adoption, no physical impact
   - Impact: None

3. **Company implements AI for customer service**
   - ❌ IGNORE
   - Reason: Technology upgrade, existing staff
   - Impact: None

## ✅ TECHNOLOGY ADOPTION - Rare Cases to Capture

1. **Company builds private AI data center in Nevada**
   - ✅ EXTRACT
   - Reason: New physical facility
   - Impact: HIGH
   - event_type: "expansion"

2. **Enterprise builds network operations center with 50 staff**
   - ✅ EXTRACT
   - Reason: New facility + staff
   - Impact: MEDIUM
   - event_type: "expansion"

## Summary Rules

### Always IGNORE:
- ❌ Tech partnerships (APIs, software, platforms)
- ❌ Marketing partnerships
- ❌ Product collaborations without physical presence
- ❌ Software/app launches
- ❌ Awards and recognition
- ❌ Single executive hires
- ❌ Technology migrations
- ❌ Generic industry news

### Always EXTRACT:
- ✅ Seeking office space (RFPs, lease searches)
- ✅ Hiring 50+ people
- ✅ Opening new offices/facilities
- ✅ Raising $10M+ in funding
- ✅ Acquisitions
- ✅ Layoffs 20%+ or 100+ people
- ✅ Partnerships with physical co-location
- ✅ Manufacturing/warehouse expansion

### Extract ONLY if Paired with Growth:
- ⚠️ Product launches (only if mentions 100+ new hires)
- ⚠️ Leadership changes (only if explicit expansion plans)
- ⚠️ Partnerships (only if physical office implications)
- ⚠️ Market entry (only if mentions local offices/hiring)

## The Core Question

**For every event, ask:**
> "Does this directly indicate a change in PHYSICAL office space needs in the next 12 months?"

If the answer is **NO** → ❌ **IGNORE**
If the answer is **YES** → ✅ **EXTRACT**
