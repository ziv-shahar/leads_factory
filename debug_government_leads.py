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
        print(f"\nEntity Name: {entity_data.get('canonical_name', 'N/A')}")
        print(f"Entity Type: {entity_data.get('entity_type', 'N/A')}")

        reasons = lead.get("reasons", {})
        print(f"\nReasons structure keys: {list(reasons.keys())}")

        # Print full reasons structure
        print("\nFull reasons data:")
        print(json.dumps(reasons, indent=2))

        # Check for key_facts
        if "key_facts" in reasons:
            key_facts = reasons["key_facts"]
            print(f"\nKey Facts keys: {list(key_facts.keys())}")

            if "other" in key_facts:
                other_facts = key_facts["other"]
                print(f"\nOther Facts keys: {list(other_facts.keys())}")
                print(f"\nOther Facts data:")
                print(json.dumps(other_facts, indent=2))

                # Check for opportunity-specific fields
                print("\n--- Opportunity Fields ---")
                print(f"opportunity_status: {other_facts.get('opportunity_status', 'NOT FOUND')}")
                print(f"notice_type: {other_facts.get('notice_type', 'NOT FOUND')}")
                print(f"response_deadline: {other_facts.get('response_deadline', 'NOT FOUND')}")
                print(f"solicitation_number: {other_facts.get('solicitation_number', 'NOT FOUND')}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
