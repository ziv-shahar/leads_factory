#!/usr/bin/env python3
"""Test script to verify location_leads fix"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("TESTING LOCATION LEADS FIX")
print("=" * 80)

# Count before
print("\nBEFORE FIX:")
entities_response = supabase.table('entities').select('id', count='exact').execute()
location_leads_response = supabase.table('location_leads').select('id', count='exact').execute()
print(f"  Total entities: {entities_response.count}")
print(f"  Total location_leads: {location_leads_response.count}")

# Get entities without location_leads
entities_with_leads = supabase.table('location_leads').select('entity_id').execute()
entity_ids_with_leads = {lead['entity_id'] for lead in entities_with_leads.data}

all_entities = supabase.table('entities').select('id, canonical_name, entity_metadata').execute()
entities_without_leads = [e for e in all_entities.data if e['id'] not in entity_ids_with_leads]

print(f"  Entities without location_leads: {len(entities_without_leads)}")

if entities_without_leads:
    print("\n  Sample entities without location_leads (first 10):")
    for entity in entities_without_leads[:10]:
        metadata = entity.get('entity_metadata', {})
        hq_state = metadata.get('hq_state', 'NO HQ STATE')
        print(f"    - {entity['canonical_name'][:50]:50s} (HQ: {hq_state})")

print("\n" + "=" * 80)
print("Run the pipeline to create default location_leads:")
print("  python3 main.py run")
print("=" * 80)
