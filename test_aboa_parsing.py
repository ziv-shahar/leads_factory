#!/usr/bin/env python3
"""Test script to verify aboa_sf parsing from government opportunities."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.government_opportunities_processor import (
    parse_opportunities_from_json,
    create_opportunity_event
)

def test_aboa_parsing():
    """Test that aboa_sf fields are correctly extracted and stored."""

    # Load the test file
    test_file = Path("raw_data_bucket/government/permits_and_opportunities/raw_opportunities_20260313.json")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    with open(test_file) as f:
        content = f.read()

    # Parse opportunities
    opportunities = parse_opportunities_from_json(content)
    print(f"📊 Found {len(opportunities)} opportunities\n")

    # Track which ones have aboa_sf data
    with_size = []
    without_size = []
    filtered_out = []

    for opp in opportunities:
        sol_num = opp.get('solicitation_number', 'N/A')
        aboa_min = opp.get('aboa_sf_min')
        aboa_max = opp.get('aboa_sf_max')

        # Try to create event
        result = create_opportunity_event(opp, str(test_file))

        if result is None:
            # Filtered out
            filtered_out.append((sol_num, opp.get('title', 'N/A')[:40]))
        elif aboa_min or aboa_max:
            # Has size data
            event, opp_id = result
            with_size.append({
                'sol_num': sol_num,
                'title': opp.get('title', 'N/A')[:50],
                'aboa_min': aboa_min,
                'aboa_max': aboa_max,
                'key_facts': event.key_facts.model_dump() if event.key_facts else {}
            })
        else:
            # No size data
            without_size.append(sol_num)

    # Report results
    print("=" * 80)
    print(f"\n✅ OPPORTUNITIES WITH aboa_sf DATA THAT PASSED FILTERS:")
    print(f"   Count: {len(with_size)}\n")

    for item in with_size:
        print(f"📋 {item['sol_num']}")
        print(f"   Title: {item['title']}")
        print(f"   Raw data: aboa_sf_min={item['aboa_min']}, aboa_sf_max={item['aboa_max']}")
        print(f"\n   ✨ key_facts stored in database:")

        key_facts = item['key_facts']

        # Check if aboa_sf is at top level
        if 'aboa_sf_min' in key_facts:
            print(f"      ✅ aboa_sf_min: {key_facts['aboa_sf_min']} (TOP LEVEL)")
        else:
            print(f"      ❌ aboa_sf_min: NOT FOUND IN KEY_FACTS!")

        if 'aboa_sf_max' in key_facts:
            print(f"      ✅ aboa_sf_max: {key_facts['aboa_sf_max']} (TOP LEVEL)")
        else:
            print(f"      ❌ aboa_sf_max: NOT FOUND IN KEY_FACTS!")

        # Show other top-level fields
        print(f"\n      Other top-level fields:")
        for key, val in key_facts.items():
            if key not in ['aboa_sf_min', 'aboa_sf_max', 'other']:
                print(f"      • {key}: {val}")

        # Show other dict
        if 'other' in key_facts:
            print(f"\n      Fields in 'other' dict:")
            for key, val in key_facts['other'].items():
                print(f"      • {key}: {val}")

        print()

    print("\n" + "=" * 80)
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ {len(with_size)} opportunities with aboa_sf (passed filters)")
    print(f"   📭 {len(without_size)} opportunities without aboa_sf (passed filters)")
    print(f"   ❌ {len(filtered_out)} filtered out")

    if filtered_out:
        print(f"\n   Filtered out:")
        for sol, title in filtered_out[:5]:
            print(f"   • {sol}: {title}")


if __name__ == "__main__":
    test_aboa_parsing()
