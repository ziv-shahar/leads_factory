#!/usr/bin/env python3
"""Apply the location_leads fix to existing database"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def ensure_all_entities_have_location_leads():
    """Create default location_leads for entities that don't have them."""

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get all entities
    all_entities_response = supabase.table('entities').select('id, canonical_name, entity_metadata').execute()
    all_entities = all_entities_response.data

    # Get entities that already have location_leads
    entities_with_leads_response = supabase.table('location_leads').select('entity_id').execute()
    entity_ids_with_leads = {lead['entity_id'] for lead in entities_with_leads_response.data}

    # Find entities without location_leads
    entities_without_leads = [e for e in all_entities if e['id'] not in entity_ids_with_leads]

    print(f"\nFound {len(entities_without_leads)} entities without location_leads")

    created_count = 0
    skipped_count = 0

    for entity in entities_without_leads:
        # Try to get HQ state from entity_metadata
        metadata = entity.get('entity_metadata') or {}
        hq_state = metadata.get('hq_state')
        hq_city = metadata.get('hq_city')
        entity_name = entity.get('canonical_name')

        if not hq_state:
            # No HQ state - skip this entity
            print(f"  ⊘ Skipped {entity_name}: No HQ state in metadata")
            skipped_count += 1
            continue

        # Validate state code (should be 2 letters)
        if len(hq_state) != 2:
            print(f"  ⊘ Skipped {entity_name}: Invalid state code '{hq_state}'")
            skipped_count += 1
            continue

        # Create default location_lead
        location_lead_data = {
            'entity_id': entity['id'],
            'state': hq_state.upper(),  # Normalize to uppercase
            'city': hq_city,
            'score': 0,  # No location-specific events
            'confidence_score': 0.0,
            'status': 'NEW',
            'event_count': 0,
            'reasons': {},
            'last_event_date': None
        }

        result = supabase.table('location_leads').insert(location_lead_data).execute()
        print(f"  ✓ Created default location_lead for {entity_name} in {hq_state}")
        created_count += 1

    print(f"\n✓ Created {created_count} default location_leads")
    print(f"⊘ Skipped {skipped_count} entities (no valid US HQ state)")

    # Verify
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    total_entities_response = supabase.table('entities').select('id', count='exact').execute()
    total_location_leads_response = supabase.table('location_leads').select('id', count='exact').execute()
    entities_with_leads_after_response = supabase.table('location_leads').select('entity_id').execute()
    entities_with_leads_after = len({lead['entity_id'] for lead in entities_with_leads_after_response.data})

    print(f"Total entities: {total_entities_response.count}")
    print(f"Total location_leads: {total_location_leads_response.count}")
    print(f"Entities with location_leads: {entities_with_leads_after}")
    print(f"Entities without location_leads: {total_entities_response.count - entities_with_leads_after}")

if __name__ == "__main__":
    print("=" * 80)
    print("APPLYING LOCATION LEADS FIX")
    print("=" * 80)
    ensure_all_entities_have_location_leads()
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
