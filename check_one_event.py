#!/usr/bin/env python3
"""Check full structure of a single government event."""

import requests
import json

SUPABASE_URL = "https://qmnsqztyduzvfimnkhtu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFtbnNxenR5ZHV6dmZpbW5raHR1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODYzNTE3NSwiZXhwIjoyMDg0MjExMTc1fQ.gmlz5X6pEu-oRnuFYCpmq7xtMyqhjFWaTrdC6A5CkkU"

url = f"{SUPABASE_URL}/rest/v1/events"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Get the Rutland, VT event that shows sq ft in summary
params = {
    "opportunity_id": "eq.018165584cfd460fa694ab841ed04373",
    "limit": "1"
}

response = requests.get(url, headers=headers, params=params)
events = response.json()

if events:
    event = events[0]
    print("=" * 90)
    print("📋 FULL EVENT STRUCTURE FOR RUTLAND, VT (shows 5,633 sq ft in summary)")
    print("=" * 90)
    print(f"\nEvent ID: {event['id']}")
    print(f"Opportunity ID: {event.get('opportunity_id')}")
    print(f"\n🔍 FULL key_facts structure:\n")
    print(json.dumps(event['strict']['key_facts'], indent=2))

    print("\n" + "=" * 90)
    print("\n🎯 CHECKING FOR aboa_sf:")
    kf = event['strict']['key_facts']

    if 'aboa_sf_min' in kf:
        print(f"✅ aboa_sf_min found at TOP LEVEL: {kf['aboa_sf_min']}")
    else:
        print(f"❌ aboa_sf_min NOT at top level")

    if 'aboa_sf_max' in kf:
        print(f"✅ aboa_sf_max found at TOP LEVEL: {kf['aboa_sf_max']}")
    else:
        print(f"❌ aboa_sf_max NOT at top level")

    # Check if it's in 'other'
    if 'other' in kf:
        print(f"\n🔍 Checking 'other' dict:")
        other = kf['other']
        if 'aboa_sf_min' in other:
            print(f"   ✅ aboa_sf_min found IN OTHER: {other['aboa_sf_min']}")
        if 'aboa_sf_max' in other:
            print(f"   ✅ aboa_sf_max found IN OTHER: {other['aboa_sf_max']}")

        if 'aboa_sf_min' not in other and 'aboa_sf_max' not in other:
            print(f"   ❌ aboa_sf_min/max NOT in 'other' either")
            print(f"\n   'other' dict keys: {list(other.keys())}")
else:
    print("Event not found")
