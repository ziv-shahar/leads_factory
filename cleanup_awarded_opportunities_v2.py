"""
Clean up awarded and expired government opportunities from database.

This script removes leads/events that are no longer actionable:
- Already awarded contracts (opportunity_status=awarded or notice_type=Award Notice)
- Expired opportunities (events.expired_at is set)
"""
import os
from datetime import datetime
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


def clean_awarded_opportunities():
    """Remove awarded government opportunities from database."""
    print("=" * 80)
    print("Cleaning up awarded government opportunities...")
    print("=" * 80)

    # Query all government opportunity events (expansion events with opportunity_id)
    events_response = supabase.table("events").select(
        "id, entity_id, event_type, opportunity_id, strict, entities!entity_id(canonical_name, entity_type)"
    ).eq("event_type", "expansion").not_.is_("opportunity_id", "null").execute()

    all_events = events_response.data

    # Filter to government agencies only
    gov_events = [e for e in all_events if e.get("entities", {}).get("entity_type") == "government_agency"]

    print(f"\nFound {len(gov_events)} government opportunity events (out of {len(all_events)} expansion events)")

    # Track what we'll delete
    to_delete_events = []
    to_delete_leads = set()  # Use set to avoid duplicates

    for event in gov_events:
        event_id = event.get("id")
        entity_id = event.get("entity_id")
        entity_name = event.get("entities", {}).get("canonical_name", "Unknown")
        opportunity_id = event.get("opportunity_id")
        strict = event.get("strict", {})

        # Extract opportunity details from strict.key_facts.other
        key_facts = strict.get("key_facts", {})
        other_facts = key_facts.get("other", {}) if key_facts else {}

        if not other_facts or not isinstance(other_facts, dict):
            continue  # Skip non-opportunity events

        # Check if awarded
        opportunity_status = other_facts.get("opportunity_status", "").lower()
        notice_type = other_facts.get("notice_type", "").lower()
        solicitation = other_facts.get("solicitation_number", "N/A")

        is_awarded = (
            opportunity_status == "awarded" or
            "award notice" in notice_type
        )

        if is_awarded:
            to_delete_events.append({
                "event_id": event_id,
                "entity_id": entity_id,
                "entity": entity_name,
                "solicitation": solicitation,
                "opportunity_id": opportunity_id,
                "status": opportunity_status,
                "notice_type": notice_type
            })
            to_delete_leads.add(entity_id)  # Mark lead for potential deletion

    if not to_delete_events:
        print("\n✅ No awarded opportunities found - database is clean!")
        return

    # Show what will be deleted
    print(f"\n⚠️  Found {len(to_delete_events)} awarded opportunities to remove:")
    print()
    for idx, item in enumerate(to_delete_events[:10], 1):  # Show first 10
        print(f"  {idx}. {item['entity']} - {item['solicitation']}")
        print(f"     Status: {item['status']}, Notice Type: {item.get('notice_type', 'N/A')}")

    if len(to_delete_events) > 10:
        print(f"  ... and {len(to_delete_events) - 10} more")

    # Confirm deletion
    print()
    confirm = input(f"Delete {len(to_delete_events)} awarded opportunity events? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Cancelled - no changes made")
        return

    # Delete events
    deleted_events = 0
    for item in to_delete_events:
        try:
            supabase.table("events").delete().eq("id", item["event_id"]).execute()
            deleted_events += 1
        except Exception as e:
            print(f"  ⚠️  Error deleting event {item['solicitation']}: {e}")

    print(f"\n✅ Successfully deleted {deleted_events}/{len(to_delete_events)} awarded opportunity events")

    # Check if we should delete leads (only if entity has no remaining events)
    print(f"\n🔍 Checking if {len(to_delete_leads)} leads should be deleted...")
    deleted_leads = 0

    for entity_id in to_delete_leads:
        # Check if entity still has any events
        remaining_events = supabase.table("events").select("id").eq("entity_id", entity_id).execute()

        if not remaining_events.data or len(remaining_events.data) == 0:
            # No events left - delete the lead
            try:
                supabase.table("leads_current").delete().eq("entity_id", entity_id).execute()
                deleted_leads += 1
            except Exception as e:
                print(f"  ⚠️  Error deleting lead for entity {entity_id}: {e}")

    if deleted_leads > 0:
        print(f"✅ Deleted {deleted_leads} leads with no remaining events")
    else:
        print(f"ℹ️  No leads deleted (entities still have other events)")


def clean_expired_opportunities():
    """Remove expired government opportunities (events with expired_at set)."""
    print("\n" + "=" * 80)
    print("Cleaning up expired government opportunities...")
    print("=" * 80)

    # Query events with expired_at set
    events_response = supabase.table("events").select(
        "id, entity_id, opportunity_id, expired_at, strict, entities!entity_id(canonical_name, entity_type)"
    ).not_.is_("expired_at", "null").execute()

    all_expired = events_response.data

    # Filter to government agencies only
    gov_expired = [e for e in all_expired if e.get("entities", {}).get("entity_type") == "government_agency"]

    print(f"\nFound {len(gov_expired)} expired government opportunity events")

    if not gov_expired:
        print("\n✅ No expired opportunities found - database is clean!")
        return

    # Prepare deletion list
    to_delete_events = []
    to_delete_leads = set()

    for event in gov_expired:
        event_id = event.get("id")
        entity_id = event.get("entity_id")
        entity_name = event.get("entities", {}).get("canonical_name", "Unknown")
        opportunity_id = event.get("opportunity_id", "N/A")
        expired_at = event.get("expired_at")

        strict = event.get("strict", {})
        key_facts = strict.get("key_facts", {})
        other_facts = key_facts.get("other", {}) if key_facts else {}
        solicitation = other_facts.get("solicitation_number", "N/A") if other_facts else "N/A"

        to_delete_events.append({
            "event_id": event_id,
            "entity_id": entity_id,
            "entity": entity_name,
            "solicitation": solicitation,
            "opportunity_id": opportunity_id,
            "expired_at": expired_at
        })
        to_delete_leads.add(entity_id)

    # Show what will be deleted
    print(f"\n⚠️  Found {len(to_delete_events)} expired opportunities to remove:")
    print()
    for idx, item in enumerate(to_delete_events[:10], 1):  # Show first 10
        print(f"  {idx}. {item['entity']} - {item['solicitation']}")
        print(f"     Expired: {item['expired_at']}")

    if len(to_delete_events) > 10:
        print(f"  ... and {len(to_delete_events) - 10} more")

    # Confirm deletion
    print()
    confirm = input(f"Delete {len(to_delete_events)} expired opportunity events? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Cancelled - no changes made")
        return

    # Delete events
    deleted_events = 0
    for item in to_delete_events:
        try:
            supabase.table("events").delete().eq("id", item["event_id"]).execute()
            deleted_events += 1
        except Exception as e:
            print(f"  ⚠️  Error deleting event {item['solicitation']}: {e}")

    print(f"\n✅ Successfully deleted {deleted_events}/{len(to_delete_events)} expired opportunity events")

    # Check if we should delete leads
    print(f"\n🔍 Checking if {len(to_delete_leads)} leads should be deleted...")
    deleted_leads = 0

    for entity_id in to_delete_leads:
        # Check if entity still has any events
        remaining_events = supabase.table("events").select("id").eq("entity_id", entity_id).execute()

        if not remaining_events.data or len(remaining_events.data) == 0:
            try:
                supabase.table("leads_current").delete().eq("entity_id", entity_id).execute()
                deleted_leads += 1
            except Exception as e:
                print(f"  ⚠️  Error deleting lead for entity {entity_id}: {e}")

    if deleted_leads > 0:
        print(f"✅ Deleted {deleted_leads} leads with no remaining events")
    else:
        print(f"ℹ️  No leads deleted (entities still have other events)")


def main():
    """Main cleanup function."""
    print("\n🧹 Government Opportunity Cleanup Script (V2)\n")
    print(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Clean awarded
    clean_awarded_opportunities()

    # Clean expired
    clean_expired_opportunities()

    print("\n" + "=" * 80)
    print("✅ Cleanup complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Refresh your web app to see the cleaned leads")
    print("2. Future data processing will automatically filter these out")
    print("=" * 80)


if __name__ == "__main__":
    main()
