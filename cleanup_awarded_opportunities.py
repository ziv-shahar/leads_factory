"""
Clean up awarded and expired government opportunities from database.

This script removes leads that are no longer actionable:
- Already awarded contracts (Award Notice)
- Expired opportunities (deadline passed)
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

    # Query all government leads
    response = supabase.table("leads_current").select("*").eq("entity_type", "government_agency").execute()

    all_leads = response.data
    print(f"\nFound {len(all_leads)} government agency leads")

    # Track what we'll delete
    to_delete = []

    for lead in all_leads:
        lead_id = lead.get("id")
        entity_name = lead.get("entity_name_raw", "Unknown")
        key_facts = lead.get("key_facts", {})
        other_facts = key_facts.get("other", {}) if key_facts else {}

        # Check if awarded
        opportunity_status = other_facts.get("opportunity_status", "").lower()
        notice_type = other_facts.get("notice_type", "").lower()

        is_awarded = (
            opportunity_status == "awarded" or
            "award notice" in notice_type
        )

        if is_awarded:
            solicitation = other_facts.get("solicitation_number", "N/A")
            to_delete.append({
                "id": lead_id,
                "entity": entity_name,
                "solicitation": solicitation,
                "status": opportunity_status,
                "notice_type": notice_type
            })

    if not to_delete:
        print("\n✅ No awarded opportunities found - database is clean!")
        return

    # Show what will be deleted
    print(f"\n⚠️  Found {len(to_delete)} awarded opportunities to remove:")
    print()
    for idx, item in enumerate(to_delete[:10], 1):  # Show first 10
        print(f"  {idx}. {item['entity']} - {item['solicitation']}")
        print(f"     Status: {item['status']}, Notice Type: {item['notice_type']}")

    if len(to_delete) > 10:
        print(f"  ... and {len(to_delete) - 10} more")

    # Confirm deletion
    print()
    confirm = input(f"Delete {len(to_delete)} awarded opportunities? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Cancelled - no changes made")
        return

    # Delete awarded opportunities
    deleted_count = 0
    for item in to_delete:
        try:
            supabase.table("leads_current").delete().eq("id", item["id"]).execute()
            deleted_count += 1
        except Exception as e:
            print(f"  ⚠️  Error deleting {item['solicitation']}: {e}")

    print(f"\n✅ Successfully deleted {deleted_count}/{len(to_delete)} awarded opportunities")


def clean_expired_opportunities():
    """Remove expired government opportunities (deadline passed)."""
    print("\n" + "=" * 80)
    print("Cleaning up expired government opportunities...")
    print("=" * 80)

    # Query all government leads
    response = supabase.table("leads_current").select("*").eq("entity_type", "government_agency").execute()

    all_leads = response.data
    print(f"\nFound {len(all_leads)} government agency leads")

    # Track what we'll delete
    to_delete = []
    now = datetime.now()

    for lead in all_leads:
        lead_id = lead.get("id")
        entity_name = lead.get("entity_name_raw", "Unknown")
        key_facts = lead.get("key_facts", {})
        other_facts = key_facts.get("other", {}) if key_facts else {}

        response_deadline = other_facts.get("response_deadline")

        if response_deadline:
            try:
                # Parse deadline
                deadline_str = response_deadline.replace("T", " ").split("+")[0].strip()

                if " " in deadline_str:
                    deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
                else:
                    deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
                    deadline_dt = deadline_dt.replace(hour=23, minute=59, second=59)

                # Check if expired
                if deadline_dt < now:
                    solicitation = other_facts.get("solicitation_number", "N/A")
                    to_delete.append({
                        "id": lead_id,
                        "entity": entity_name,
                        "solicitation": solicitation,
                        "deadline": response_deadline
                    })
            except ValueError:
                # Skip if can't parse date
                pass

    if not to_delete:
        print("\n✅ No expired opportunities found - database is clean!")
        return

    # Show what will be deleted
    print(f"\n⚠️  Found {len(to_delete)} expired opportunities to remove:")
    print()
    for idx, item in enumerate(to_delete[:10], 1):  # Show first 10
        print(f"  {idx}. {item['entity']} - {item['solicitation']}")
        print(f"     Deadline: {item['deadline']}")

    if len(to_delete) > 10:
        print(f"  ... and {len(to_delete) - 10} more")

    # Confirm deletion
    print()
    confirm = input(f"Delete {len(to_delete)} expired opportunities? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Cancelled - no changes made")
        return

    # Delete expired opportunities
    deleted_count = 0
    for item in to_delete:
        try:
            supabase.table("leads_current").delete().eq("id", item["id"]).execute()
            deleted_count += 1
        except Exception as e:
            print(f"  ⚠️  Error deleting {item['solicitation']}: {e}")

    print(f"\n✅ Successfully deleted {deleted_count}/{len(to_delete)} expired opportunities")


def main():
    """Main cleanup function."""
    print("\n🧹 Government Opportunity Cleanup Script\n")
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
