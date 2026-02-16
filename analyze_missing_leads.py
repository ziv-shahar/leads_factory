#!/usr/bin/env python3
"""Analyze which entities are missing location_leads and why"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Valid US state codes
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("ANALYZING MISSING LOCATION LEADS")
print("=" * 80)

# Get entities without location_leads
entities_with_leads = supabase.table('location_leads').select('entity_id').execute()
entity_ids_with_leads = {lead['entity_id'] for lead in entities_with_leads.data}

all_entities = supabase.table('entities').select('id, canonical_name, entity_metadata').execute()
entities_without_leads = [e for e in all_entities.data if e['id'] not in entity_ids_with_leads]

print(f"\nTotal entities without location_leads: {len(entities_without_leads)}")

# Categorize
us_entities = []
international_entities = []
no_hq_entities = []

for entity in entities_without_leads:
    metadata = entity.get('entity_metadata', {})
    hq_state = metadata.get('hq_state')

    if not hq_state:
        no_hq_entities.append(entity)
    elif hq_state.upper() in US_STATES:
        us_entities.append(entity)
    else:
        international_entities.append(entity)

print(f"\nBreakdown:")
print(f"  US-based (have US state code):    {len(us_entities)}")
print(f"  International (non-US location):  {len(international_entities)}")
print(f"  No HQ data:                       {len(no_hq_entities)}")

if us_entities:
    print(f"\n✓ US-BASED ENTITIES THAT WILL GET DEFAULT LOCATION_LEADS:")
    for entity in us_entities:
        metadata = entity.get('entity_metadata', {})
        hq_state = metadata.get('hq_state')
        hq_city = metadata.get('hq_city', 'Unknown')
        print(f"  - {entity['canonical_name'][:50]:50s} in {hq_city}, {hq_state}")

if international_entities:
    print(f"\n⊘ INTERNATIONAL ENTITIES (will be skipped):")
    for entity in international_entities[:10]:
        metadata = entity.get('entity_metadata', {})
        hq_state = metadata.get('hq_state')
        print(f"  - {entity['canonical_name'][:50]:50s} in {hq_state}")
    if len(international_entities) > 10:
        print(f"  ... and {len(international_entities) - 10} more")

if no_hq_entities:
    print(f"\n⊘ NO HQ DATA (will be skipped):")
    for entity in no_hq_entities:
        print(f"  - {entity['canonical_name']}")

print("\n" + "=" * 80)
