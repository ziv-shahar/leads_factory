"""
Check which government opportunities have building size data.
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

print("=" * 80)
print("Checking Government Opportunities for Building Size Data")
print("=" * 80)

# Get all government opportunity events
result = supabase.table("events").select(
    "id, opportunity_id, event_type, strict, entities!entity_id(canonical_name)"
).eq("event_type", "expansion").not_.is_("opportunity_id", "null").limit(20).execute()

total = len(result.data)
with_size = 0
without_size = 0

print(f"\nFound {total} government opportunity events\n")

for event in result.data:
    entity_name = event.get("entities", {}).get("canonical_name", "Unknown")
    opportunity_id = event.get("opportunity_id")
    strict = event.get("strict", {})
    key_facts = strict.get("key_facts", {})

    if not isinstance(key_facts, dict):
        print(f"❌ {entity_name}: key_facts is not a dict (type: {type(key_facts)})")
        without_size += 1
        continue

    # Check both locations for size data
    top_min = key_facts.get("aboa_sf_min")
    top_max = key_facts.get("aboa_sf_max")

    other = key_facts.get("other", {})
    other_min = None
    other_max = None
    if isinstance(other, dict):
        other_min = other.get("aboa_sf_min")
        other_max = other.get("aboa_sf_max")

    has_size = bool(top_min or top_max or other_min or other_max)

    if has_size:
        with_size += 1
        print(f"✅ {entity_name}")
        print(f"   Opportunity ID: {opportunity_id}")
        if top_min or top_max:
            print(f"   Top-level: {top_min:,} - {top_max:,} sq ft" if top_min and top_max else f"   Top-level: {top_min or top_max:,} sq ft")
        if other_min or other_max:
            print(f"   Other: {other_min:,} - {other_max:,} sq ft" if other_min and other_max else f"   Other: {other_min or other_max:,} sq ft")
    else:
        without_size += 1
        solicitation = other.get("solicitation_number", "N/A") if isinstance(other, dict) else "N/A"
        print(f"❌ {entity_name} - {solicitation}: NO SIZE DATA")

print("\n" + "=" * 80)
print(f"Summary:")
print(f"  With size data: {with_size}/{total} ({with_size/total*100:.1f}%)")
print(f"  Without size data: {without_size}/{total} ({without_size/total*100:.1f}%)")
print("=" * 80)

if without_size > 0:
    print("\nℹ️  Note: Not all government opportunities have building size data.")
    print("   Only office lease opportunities typically include aboa_sf_min/max.")
    print("   Other types (services, equipment, etc.) won't have this field.")
