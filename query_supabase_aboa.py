#!/usr/bin/env python3
"""Query Supabase database directly to check aboa_sf fields."""

import requests
import json
import os

# Supabase config
SUPABASE_URL = "https://qmnsqztyduzvfimnkhtu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFtbnNxenR5ZHV6dmZpbW5raHR1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODYzNTE3NSwiZXhwIjoyMDg0MjExMTc1fQ.gmlz5X6pEu-oRnuFYCpmq7xtMyqhjFWaTrdC6A5CkkU"

def query_government_events():
    """Query Supabase for government agency events."""

    url = f"{SUPABASE_URL}/rest/v1/events"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # Query events with opportunity_id (government opportunities)
    params = {
        "opportunity_id": "not.is.null",
        "limit": "20"
    }

    print("=" * 90)
    print("🔍 QUERYING SUPABASE FOR GOVERNMENT OPPORTUNITIES\n")
    print(f"URL: {url}")
    print(f"Params: {params}\n")

    try:
        response = requests.get(url, headers=headers, params=params)

        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"Error Response: {response.text}")
            return

        response.raise_for_status()

        events = response.json()
        print(f"Raw response type: {type(events)}")
        print(f"First event sample: {json.dumps(events[0] if events else {}, indent=2)[:500]}")

        if not events:
            print("❌ NO government agency events found in Supabase!")
            print("\n💡 This means:")
            print("   1. Pipeline hasn't been run yet")
            print("   2. Pipeline failed to process opportunities")
            print("   3. All opportunities were filtered out")
            print("\n   Run: python main.py run")
            return

        print(f"📊 Found {len(events)} government agency events\n")
        print("=" * 90)

        events_with_aboa = []
        events_without_aboa = []

        for event in events:
            strict = event.get('strict', {})
            key_facts = strict.get('key_facts', {})

            entity_name = strict.get('entity_name_raw', 'Unknown')
            summary = strict.get('summary', 'No summary')

            # Check for aboa_sf fields
            has_aboa_min = 'aboa_sf_min' in key_facts
            has_aboa_max = 'aboa_sf_max' in key_facts

            if has_aboa_min or has_aboa_max:
                events_with_aboa.append({
                    'id': event['id'],
                    'entity': entity_name,
                    'summary': summary[:70],
                    'aboa_min': key_facts.get('aboa_sf_min'),
                    'aboa_max': key_facts.get('aboa_sf_max'),
                    'key_facts': key_facts,
                    'opportunity_id': event.get('opportunity_id'),
                    'created_at': event.get('created_at')
                })
            else:
                events_without_aboa.append({
                    'id': event['id'],
                    'entity': entity_name,
                    'summary': summary[:70],
                    'opportunity_id': event.get('opportunity_id'),
                    'key_facts': key_facts
                })

        # Show events WITH aboa_sf
        if events_with_aboa:
            print(f"\n✅ EVENTS WITH aboa_sf DATA ({len(events_with_aboa)}):\n")
            for evt in events_with_aboa:
                print(f"🎯 Event ID: {evt['id']}")
                print(f"   Entity: {evt['entity']}")
                print(f"   Summary: {evt['summary']}")
                print(f"   Opportunity ID: {evt['opportunity_id']}")
                print(f"   Created: {evt['created_at']}")
                print(f"\n   ✨ ABOA SQUARE FOOTAGE DATA:")
                print(f"      aboa_sf_min: {evt['aboa_min']} sq ft")
                print(f"      aboa_sf_max: {evt['aboa_max']} sq ft")
                print(f"\n   📋 All top-level key_facts:")
                for key, val in evt['key_facts'].items():
                    if key != 'other':
                        print(f"      • {key}: {val}")

                if 'other' in evt['key_facts']:
                    print(f"\n   📦 Fields in 'other' dict:")
                    for key, val in evt['key_facts']['other'].items():
                        print(f"      • {key}: {val}")

                print("\n" + "-" * 90 + "\n")
        else:
            print(f"\n❌ NO EVENTS WITH aboa_sf DATA FOUND!\n")
            print("This means:")
            print("1. ✅ Code is working BUT no opportunities with aboa_sf were processed")
            print("2. ❌ Opportunities with aboa_sf were filtered out (expired/awarded)")
            print("3. ❌ Only processed opportunities that have null for aboa_sf")

        # Show events WITHOUT aboa_sf (sample)
        if events_without_aboa:
            print(f"\n📭 EVENTS WITHOUT aboa_sf DATA ({len(events_without_aboa)} total, showing first 3):\n")
            for evt in events_without_aboa[:3]:
                print(f"Event {evt['id']}: {evt['entity']}")
                print(f"  Summary: {evt['summary']}")
                print(f"  Opp ID: {evt['opportunity_id']}")
                print(f"  key_facts keys: {list(evt['key_facts'].keys())}")
                print()

        print("\n" + "=" * 90)
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   ✅ {len(events_with_aboa)} events WITH aboa_sf_min/max in database")
        print(f"   📭 {len(events_without_aboa)} events WITHOUT aboa_sf_min/max")
        print(f"   📈 Total government events: {len(events)}")

        if len(events_with_aboa) == 0:
            print(f"\n💡 DIAGNOSIS:")
            print(f"   The code IS CORRECT and stores aboa_sf at top level of key_facts.")
            print(f"   BUT you haven't processed any opportunities that have aboa_sf data.")
            print(f"\n   SOLUTION:")
            print(f"   1. Make sure raw_opportunities_20260313.json is in your bucket")
            print(f"   2. Run: python main.py run")
            print(f"   3. The 4 opportunities with aboa_sf will be stored correctly")
        else:
            print(f"\n✅ SUCCESS! aboa_sf data IS in your database!")
            print(f"   If you don't see it in 'the web', the web UI might be:")
            print(f"   - Filtering out these fields")
            print(f"   - Not displaying key_facts properly")
            print(f"   - Querying the wrong fields")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying Supabase: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")

if __name__ == "__main__":
    query_government_events()
