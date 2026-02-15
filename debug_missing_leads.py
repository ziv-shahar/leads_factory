#!/usr/bin/env python3
"""
Debug script to identify why leads are missing from the web dashboard
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

print("=" * 80)
print("DEBUGGING MISSING LEADS")
print("=" * 80)

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Count total entities
print("\n[1] TOTAL ENTITIES")
print("-" * 80)
entities_response = supabase.table('entities').select('id', count='exact').execute()
total_entities = entities_response.count
print(f"Total entities in database: {total_entities}")

# 2. Count location_leads
print("\n[2] TOTAL LOCATION LEADS")
print("-" * 80)
location_leads_response = supabase.table('location_leads').select('id', count='exact').execute()
total_location_leads = location_leads_response.count
print(f"Total location_leads in database: {total_location_leads}")

# 3. Status distribution in location_leads
print("\n[3] LOCATION LEADS BY STATUS")
print("-" * 80)
all_leads = supabase.table('location_leads').select('status').execute()
status_counts = {}
for lead in all_leads.data:
    status = lead['status']
    status_counts[status] = status_counts.get(status, 0) + 1

for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {status:20s}: {count:5d} leads")

# 4. Check for entities without location_leads
print("\n[4] ENTITIES WITHOUT LOCATION LEADS")
print("-" * 80)
entities_with_leads = supabase.table('location_leads').select('entity_id').execute()
entity_ids_with_leads = set(lead['entity_id'] for lead in entities_with_leads.data)

all_entity_ids_response = supabase.table('entities').select('id').execute()
all_entity_ids = set(entity['id'] for entity in all_entity_ids_response.data)

orphaned_entities = all_entity_ids - entity_ids_with_leads
print(f"Entities WITHOUT location_leads: {len(orphaned_entities)}")
print(f"Entities WITH location_leads: {len(entity_ids_with_leads)}")

if orphaned_entities:
    print("\nSample orphaned entities (first 5):")
    orphaned_list = list(orphaned_entities)[:5]
    for entity_id in orphaned_list:
        entity = supabase.table('entities').select('id, canonical_name').eq('id', entity_id).execute()
        if entity.data:
            print(f"  - ID {entity_id}: {entity.data[0]['canonical_name']}")

# 5. Check what the API would return with default filters
print("\n[5] WHAT API RETURNS (Default filters: NEW + ACTIVE status)")
print("-" * 80)
api_response = supabase.table('location_leads')\
    .select('id, entity_id, status, score, state', count='exact')\
    .in_('status', ['NEW', 'ACTIVE'])\
    .execute()

print(f"Leads returned by API (NEW + ACTIVE only): {api_response.count}")
print(f"This is what users see in the dashboard by default")

# 6. State distribution
print("\n[6] LOCATION LEADS BY STATE")
print("-" * 80)
all_leads_with_state = supabase.table('location_leads').select('state').execute()
state_counts = {}
for lead in all_leads_with_state.data:
    state = lead['state']
    state_counts[state] = state_counts.get(state, 0) + 1

for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {state:5s}: {count:5d} leads")

# 7. Check for duplicate entities (same entity_id appearing multiple times)
print("\n[7] ENTITIES WITH MULTIPLE LOCATION LEADS (Multi-state operations)")
print("-" * 80)
entity_counts = {}
for lead in entities_with_leads.data:
    entity_id = lead['entity_id']
    entity_counts[entity_id] = entity_counts.get(entity_id, 0) + 1

multi_state_entities = {k: v for k, v in entity_counts.items() if v > 1}
print(f"Entities operating in multiple states: {len(multi_state_entities)}")
print(f"Total location_leads from multi-state entities: {sum(multi_state_entities.values())}")

if multi_state_entities:
    print("\nTop 5 entities with most states:")
    top_5 = sorted(multi_state_entities.items(), key=lambda x: x[1], reverse=True)[:5]
    for entity_id, count in top_5:
        entity = supabase.table('entities').select('canonical_name').eq('id', entity_id).execute()
        name = entity.data[0]['canonical_name'] if entity.data else "Unknown"
        states_response = supabase.table('location_leads').select('state').eq('entity_id', entity_id).execute()
        states = [s['state'] for s in states_response.data]
        print(f"  - {name[:50]:50s} in {count} states: {', '.join(states[:5])}")

# 8. Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total unique entities:              {total_entities}")
print(f"Entities with location_leads:       {len(entity_ids_with_leads)}")
print(f"Entities WITHOUT location_leads:    {len(orphaned_entities)}")
print(f"Total location_leads records:       {total_location_leads}")
print(f"Visible in dashboard (NEW+ACTIVE):  {api_response.count}")
print(f"Hidden by status filter:            {total_location_leads - api_response.count}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if len(orphaned_entities) > 0:
    print(f"⚠️  ISSUE 1: {len(orphaned_entities)} entities have NO location_leads records")
    print("   → These entities are completely invisible in the dashboard")
    print("   → Check if your pipeline is creating location_leads for all entities")

if total_location_leads - api_response.count > 0:
    hidden = total_location_leads - api_response.count
    print(f"\n⚠️  ISSUE 2: {hidden} location_leads are filtered out by status")
    print("   → Default filter only shows NEW + ACTIVE status")
    print("   → Other statuses are hidden:")
    for status, count in status_counts.items():
        if status not in ['NEW', 'ACTIVE']:
            print(f"      - {status}: {count} leads hidden")

if len(multi_state_entities) > 0:
    duplicates = sum(multi_state_entities.values()) - len(multi_state_entities)
    print(f"\n⚠️  ISSUE 3: {len(multi_state_entities)} entities appear multiple times")
    print(f"   → Creates {duplicates} 'duplicate' entries (one per state)")
    print("   → This is by design (location-based tracking)")
    print("   → But may confuse users expecting unique entities")

print("\n" + "=" * 80)
