"""
Debug script to inspect government opportunity data structure.
"""
import os
import json
from supabase import create_client
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    """Debug government leads structure."""
    print("=" * 80)
    print("Government Leads Data Structure Inspector")
    print("=" * 80)

    # Query all leads with entity data
    response = supabase.table("leads_current").select(
        "id, entity_id, score, status, reasons, entities!entity_id(entity_type, canonical_name, entity_metadata)"
    ).execute()

    all_leads = response.data

    # Filter to government agencies only
    gov_leads = [lead for lead in all_leads if lead.get("entities", {}).get("entity_type") == "government_agency"]

    print(f"\nFound {len(gov_leads)} government agency leads")

    if not gov_leads:
        print("No government leads found!")
        return

    # Show first 3 leads in detail
    for idx, lead in enumerate(gov_leads[:3], 1):
        print("\n" + "=" * 80)
        print(f"LEAD #{idx}")
        print("=" * 80)

        entity_data = lead.get("entities", {})
        entity_name = entity_data.get('canonical_name', 'N/A')
        entity_id = lead.get("entity_id")

        print(f"\nEntity Name: {entity_name}")
        print(f"Entity Type: {entity_data.get('entity_type', 'N/A')}")
        print(f"Entity ID: {entity_id}")

        reasons = lead.get("reasons", {})
        print(f"\nReasons structure keys: {list(reasons.keys())}")

        # Check for events for this entity
        print("\n--- Checking Events Table ---")
        events_response = supabase.table("events").select(
            "id, event_type, event_time, strict, dynamic_signals, opportunity_id, expired_at"
        ).eq("entity_id", entity_id).execute()

        events = events_response.data
        print(f"Found {len(events)} events for this entity")

        for event_idx, event in enumerate(events[:3], 1):  # Show first 3 events
            print(f"\n  EVENT #{event_idx}:")
            print(f"    Event Type: {event.get('event_type', 'N/A')}")
            print(f"    Event Time: {event.get('event_time', 'N/A')}")
            print(f"    Opportunity ID: {event.get('opportunity_id', 'N/A')}")
            print(f"    Expired At: {event.get('expired_at', 'N/A')}")

            # Check the strict field for structured data
            strict = event.get("strict", {})
            if strict:
                print(f"\n    Strict field keys: {list(strict.keys())}")
                print(f"\n    Full strict data:")
                print(f"    {json.dumps(strict, indent=6)}")

                # Look for key_facts in strict
                key_facts = strict.get("key_facts", {})
                if key_facts and isinstance(key_facts, dict):
                    print(f"\n    Key Facts keys: {list(key_facts.keys())}")

                    if "other" in key_facts:
                        other_facts = key_facts["other"]
                        if other_facts and isinstance(other_facts, dict):
                            print(f"\n    --- Opportunity Fields in strict.key_facts.other ---")
                            print(f"    opportunity_status: {other_facts.get('opportunity_status', 'NOT FOUND')}")
                            print(f"    notice_type: {other_facts.get('notice_type', 'NOT FOUND')}")
                            print(f"    response_deadline: {other_facts.get('response_deadline', 'NOT FOUND')}")
                            print(f"    solicitation_number: {other_facts.get('solicitation_number', 'NOT FOUND')}")
                        else:
                            print(f"\n    other field is null/empty (not a government opportunity event)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
