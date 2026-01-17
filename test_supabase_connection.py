"""Test Supabase connection and verify tables exist."""
from src.db.session import get_db
from sqlalchemy import text
import sys

def test_connection():
    """Test Supabase connection and check table structure."""
    print("🔍 Testing Supabase connection...")
    print("=" * 80)

    try:
        with get_db() as db:
            # Test basic connection
            result = db.execute(text('SELECT version()')).scalar()
            print(f"✅ Connected to PostgreSQL: {result[:50]}...")

            # Check tables
            tables_query = text("""
                SELECT table_name,
                       (SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_name = t.table_name AND table_schema = 'public') as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = db.execute(tables_query).fetchall()

            if not tables:
                print("\n❌ No tables found!")
                print("\n📝 Next steps:")
                print("1. Go to Supabase Dashboard → SQL Editor")
                print("2. Run the migration script: supabase_migration.sql")
                print("3. Run this test again")
                return False

            print(f"\n📊 Found {len(tables)} table(s):")
            print("-" * 80)

            expected_tables = {
                'raw_events': 7,
                'entities': 8,
                'events': 10,
                'leads_current': 7,
                'lead_state_history': 6
            }

            missing_tables = []
            for table_name, expected_cols in expected_tables.items():
                found = False
                for table in tables:
                    if table[0] == table_name:
                        found = True
                        status = "✅" if table[1] >= expected_cols else "⚠️"
                        print(f"{status} {table[0]:<25} ({table[1]} columns)")
                        break

                if not found:
                    missing_tables.append(table_name)
                    print(f"❌ {table_name:<25} (MISSING)")

            # Check views
            views_query = text("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            views = db.execute(views_query).fetchall()

            if views:
                print(f"\n👀 Found {len(views)} view(s):")
                print("-" * 80)
                for view in views:
                    print(f"✅ {view[0]}")

            # Summary
            print("\n" + "=" * 80)
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
                print("\n📝 Run the migration script in Supabase SQL Editor")
                return False
            else:
                print("✅ All tables present and ready!")
                print("\n🚀 You can now run: python main.py")
                return True

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n📝 Check your .env file:")
        print("   - DATABASE_URL should point to your Supabase database")
        print("   - Make sure your password is correct")
        print("   - Verify your Supabase project is active")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
