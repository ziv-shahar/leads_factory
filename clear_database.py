#!/usr/bin/env python3
"""
Clear all data from Supabase tables.

This script truncates all tables in the correct order to handle
foreign key constraints. Use this to reset the database before
rerunning the pipeline.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

def clear_tables():
    """Clear all tables in Supabase."""
    load_dotenv()

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return False

    print("Connecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Tables to clear (in order - child tables first due to foreign keys)
    tables = [
        'lead_state_history',
        'leads_current',
        'events',
        'entities',
        'raw_events'
    ]

    print("\n🗑️  Clearing tables...")
    print("=" * 60)

    for table_name in tables:
        try:
            # Get count before deletion
            before_result = supabase.table(table_name).select("id", count="exact").execute()
            before_count = before_result.count if before_result.count else 0

            # Delete all records
            if before_count > 0:
                # Supabase requires a filter, so we delete where id is not null
                supabase.table(table_name).delete().neq('id', 'impossible_value_xyz_123').execute()
                print(f"✅ {table_name}: Deleted {before_count} rows")
            else:
                print(f"ℹ️  {table_name}: Already empty")

        except Exception as e:
            print(f"⚠️  {table_name}: Error - {e}")

    print("\n" + "=" * 60)
    print("Verifying tables are empty...")
    print("=" * 60)

    all_empty = True
    for table_name in tables:
        try:
            result = supabase.table(table_name).select("id", count="exact").limit(1).execute()
            count = result.count if result.count else 0

            if count == 0:
                print(f"✅ {table_name}: Empty")
            else:
                print(f"⚠️  {table_name}: Still has {count} rows")
                all_empty = False

        except Exception as e:
            print(f"❌ {table_name}: Error checking - {e}")
            all_empty = False

    print("\n" + "=" * 60)
    if all_empty:
        print("✅ All tables cleared successfully!")
        print("\nYou can now run: python main.py run")
    else:
        print("⚠️  Some tables may not be empty. Check errors above.")
        print("\nAlternative: Use SQL Editor in Supabase Dashboard:")
        print("   TRUNCATE TABLE lead_state_history, leads_current, events, entities, raw_events CASCADE;")

    return all_empty

if __name__ == "__main__":
    import sys

    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          Clear Supabase Database Tables                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

⚠️  WARNING: This will delete ALL data from your database!

This includes:
  - All entities (companies, organizations)
  - All events (funding, hiring, partnerships, etc.)
  - All leads and lead history
  - All raw file tracking

""")

    response = input("Are you sure you want to proceed? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        print("\nProceeding with database clear...\n")
        success = clear_tables()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Operation cancelled. No data was deleted.")
        sys.exit(0)
