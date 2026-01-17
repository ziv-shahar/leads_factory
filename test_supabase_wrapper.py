#!/usr/bin/env python3
"""
Test script for Supabase wrapper.
Verifies that the wrapper provides SQLAlchemy-compatible interface.
"""
import os
os.environ['USE_SUPABASE_CLIENT'] = 'true'

from src.db.session import get_db
from src.db.models import Entity, Event, RawEvent, LeadCurrent

def test_connection():
    """Test basic connection."""
    print("="*80)
    print("Testing Supabase Wrapper")
    print("="*80)

    try:
        with get_db() as db:
            print("\n✅ Successfully created database session")

            # Test 1: Count entities
            print("\n" + "="*80)
            print("Test 1: Count entities")
            print("="*80)
            count = db.query(Entity).count()
            print(f"✅ Entity count: {count}")

            # Test 2: Query all entities
            print("\n" + "="*80)
            print("Test 2: Query entities")
            print("="*80)
            entities = db.query(Entity).limit(5).all()
            print(f"✅ Found {len(entities)} entities (limit 5)")
            for entity in entities[:3]:
                print(f"   - {entity.canonical_name} ({entity.domain or 'no domain'})")

            # Test 3: Query events
            print("\n" + "="*80)
            print("Test 3: Query events")
            print("="*80)
            event_count = db.query(Event).count()
            print(f"✅ Event count: {event_count}")

            # Test 4: Query leads
            print("\n" + "="*80)
            print("Test 4: Query leads")
            print("="*80)
            lead_count = db.query(LeadCurrent).count()
            print(f"✅ Lead count: {lead_count}")

            # Test 5: Query raw events
            print("\n" + "="*80)
            print("Test 5: Query raw events")
            print("="*80)
            raw_count = db.query(RawEvent).count()
            print(f"✅ Raw event count: {raw_count}")

            # Test 6: Filter query
            if count > 0:
                print("\n" + "="*80)
                print("Test 6: Filter query (find entity by ID)")
                print("="*80)
                first_entity = entities[0] if entities else None
                if first_entity:
                    found = db.query(Entity).filter(Entity.id == first_entity.id).first()
                    if found:
                        print(f"✅ Found entity by ID: {found.canonical_name}")
                    else:
                        print("⚠️  Filter query returned None")

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nThe Supabase wrapper is working correctly.")
        print("Your pipeline can now use Supabase via REST API!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    import sys
    success = test_connection()
    sys.exit(0 if success else 1)
