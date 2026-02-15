#!/usr/bin/env python3
"""
Check the SOURCE Supabase database for data
"""
from supabase import create_client

# Source project credentials from the storage config
SOURCE_SUPABASE_URL = "https://ycrpfnqtqdnsfaduwooa.supabase.co"
SOURCE_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InljcnBmbnF0cWRuc2ZhZHV3b29hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODg0NTEwMCwiZXhwIjoyMDg0NDIxMTAwfQ.bym-5KZqp85RxxaezigkwxjHmduolh1eDAQaSrQtyQo"

print("=" * 80)
print("CHECKING SOURCE SUPABASE PROJECT")
print("=" * 80)
print(f"URL: {SOURCE_SUPABASE_URL}")

try:
    supabase = create_client(SOURCE_SUPABASE_URL, SOURCE_SUPABASE_KEY)

    # Check entities
    print("\n[1] ENTITIES IN SOURCE DATABASE")
    print("-" * 80)
    entities = supabase.table('entities').select('id', count='exact').execute()
    print(f"Total entities: {entities.count}")

    if entities.count > 0:
        # Get sample
        sample = supabase.table('entities').select('id, canonical_name').limit(5).execute()
        print("\nSample entities:")
        for entity in sample.data:
            print(f"  - {entity['id']}: {entity['canonical_name']}")

    # Check location_leads
    print("\n[2] LOCATION LEADS IN SOURCE DATABASE")
    print("-" * 80)
    location_leads = supabase.table('location_leads').select('id', count='exact').execute()
    print(f"Total location_leads: {location_leads.count}")

    if location_leads.count > 0:
        # Status breakdown
        all_leads = supabase.table('location_leads').select('status, state, score').execute()
        status_counts = {}
        state_counts = {}
        for lead in all_leads.data:
            status_counts[lead['status']] = status_counts.get(lead['status'], 0) + 1
            state_counts[lead['state']] = state_counts.get(lead['state'], 0) + 1

        print("\nBy status:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {status}: {count}")

        print("\nBy state (top 10):")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {state}: {count}")

    # Check events
    print("\n[3] EVENTS IN SOURCE DATABASE")
    print("-" * 80)
    events = supabase.table('events').select('id', count='exact').execute()
    print(f"Total events: {events.count}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    if entities.count > 0 or location_leads.count > 0:
        print("✅ SOURCE database HAS data!")
        print("\n⚠️  You have TWO Supabase projects:")
        print(f"   - SOURCE (has data):  {SOURCE_SUPABASE_URL}")
        print(f"   - CURRENT (empty):    https://qmnsqztyduzvfimnkhtu.supabase.co")
        print("\n💡 SOLUTION: You need to either:")
        print("   1. Update .env to use the SOURCE database URL/key, OR")
        print("   2. Run your pipeline to populate the CURRENT database")
    else:
        print("❌ SOURCE database is also empty")
        print("   You need to run your pipeline to generate leads")

except Exception as e:
    print(f"\n❌ ERROR connecting to source database:")
    print(f"   {str(e)}")
    print("\n   The source database might:")
    print("   - Not exist")
    print("   - Have different table names")
    print("   - Require different credentials")

print("=" * 80)
