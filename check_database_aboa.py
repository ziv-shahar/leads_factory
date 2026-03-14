#!/usr/bin/env python3
"""Query database to check if aboa_sf fields are stored."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.session import get_db
from src.db.models import Event
import json

def check_aboa_in_database():
    """Check if aboa_sf fields are stored in the database."""

    db = next(get_db())

    print("=" * 90)
    print("🔍 CHECKING DATABASE FOR GOVERNMENT OPPORTUNITIES WITH aboa_sf DATA\n")

    # Get all government agency events
    gov_events = db.query(Event).filter(
        Event.entity_type == 'government_agency'
    ).order_by(Event.created_at.desc()).limit(20).all()

    if not gov_events:
        print("❌ NO government agency events found in database!")
        print("\n💡 This means you haven't run the pipeline yet, or it failed.")
        print("   Run: python main.py run")
        return

    print(f"📊 Found {len(gov_events)} government agency events (showing last 20)\n")
    print("=" * 90)

    events_with_aboa = []
    events_without_aboa = []

    for idx, event in enumerate(gov_events, 1):
        strict = event.strict
        key_facts = strict.get('key_facts', {}) if strict else {}

        entity_name = strict.get('entity_name_raw', 'Unknown') if strict else 'Unknown'
        summary = strict.get('summary', 'No summary') if strict else 'No summary'

        # Check for aboa_sf fields
        has_aboa_min = 'aboa_sf_min' in key_facts
        has_aboa_max = 'aboa_sf_max' in key_facts

        if has_aboa_min or has_aboa_max:
            events_with_aboa.append({
                'id': event.id,
                'entity': entity_name,
                'summary': summary[:70],
                'aboa_min': key_facts.get('aboa_sf_min'),
                'aboa_max': key_facts.get('aboa_sf_max'),
                'key_facts': key_facts,
                'opportunity_id': event.opportunity_id,
                'created_at': event.created_at
            })
        else:
            events_without_aboa.append({
                'id': event.id,
                'entity': entity_name,
                'summary': summary[:70],
                'opportunity_id': event.opportunity_id
            })

    # Show events WITH aboa_sf
    if events_with_aboa:
        print(f"\n✅ EVENTS WITH aboa_sf DATA ({len(events_with_aboa)}):\n")
        for evt in events_with_aboa:
            print(f"Event ID: {evt['id']}")
            print(f"Entity: {evt['entity']}")
            print(f"Summary: {evt['summary']}")
            print(f"Opportunity ID: {evt['opportunity_id']}")
            print(f"Created: {evt['created_at']}")
            print(f"\n✨ key_facts structure:")
            print(f"   aboa_sf_min: {evt['aboa_min']} (TOP LEVEL: {evt['aboa_min'] is not None})")
            print(f"   aboa_sf_max: {evt['aboa_max']} (TOP LEVEL: {evt['aboa_max'] is not None})")

            # Show all top-level key_facts
            print(f"\n   All top-level key_facts:")
            for key, val in evt['key_facts'].items():
                if key != 'other':
                    print(f"   • {key}: {val}")

            # Show 'other' dict if exists
            if 'other' in evt['key_facts']:
                print(f"\n   Fields in 'other' dict:")
                for key, val in evt['key_facts']['other'].items():
                    print(f"   • {key}: {val}")

            print("\n" + "-" * 90 + "\n")
    else:
        print(f"\n❌ NO EVENTS WITH aboa_sf DATA FOUND!\n")
        print("This could mean:")
        print("1. The pipeline processed opportunities that don't have aboa_sf (72% have null)")
        print("2. The expiration filter removed opportunities before parsing aboa_sf")
        print("3. The opportunities were filtered out (awarded/event space)")

    # Show events WITHOUT aboa_sf (sample)
    if events_without_aboa:
        print(f"\n📭 EVENTS WITHOUT aboa_sf DATA ({len(events_without_aboa)} total, showing first 5):\n")
        for evt in events_without_aboa[:5]:
            print(f"• Event {evt['id']}: {evt['entity']} - {evt['summary']}")
            print(f"  Opp ID: {evt['opportunity_id']}\n")

    print("\n" + "=" * 90)
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ {len(events_with_aboa)} events WITH aboa_sf_min/max")
    print(f"   📭 {len(events_without_aboa)} events WITHOUT aboa_sf_min/max")
    print(f"   📈 Total government events: {len(gov_events)}")

    if len(events_with_aboa) == 0:
        print(f"\n💡 RECOMMENDATION:")
        print(f"   The 4 opportunities with aboa_sf data may have been:")
        print(f"   1. Filtered out as expired (if expiration filter is enabled)")
        print(f"   2. Not processed yet (if you haven't run pipeline on new file)")
        print(f"   3. In the new file that's in .gitignore (raw_opportunities_20260313.json)")
        print(f"\n   Next step: Run pipeline on the file with aboa_sf data:")
        print(f"   python main.py run")

    db.close()

if __name__ == "__main__":
    try:
        check_aboa_in_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
