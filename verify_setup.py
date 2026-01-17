#!/usr/bin/env python3
"""
Comprehensive setup verification script for Leads Factory pipeline.
Run this on your local machine to verify everything is ready.
"""
import sys
import os
from pathlib import Path

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def check_env_file():
    """Check .env file configuration."""
    print_section("1. Checking .env Configuration")

    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Copy .env.example to .env and configure it.")
        return False

    print("✅ .env file exists")

    # Load and check key variables
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = {
        "DATABASE_URL": "Supabase connection string",
        "LLM_PROVIDER": "LLM provider (openai/anthropic/mock)",
        "SEARCH_PROVIDER": "Search provider (tavily/exa/serpapi/mock)",
        "BUSINESS_OBJECTIVE": "Business objective",
    }

    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            missing.append(f"   - {var}: {description}")
            print(f"⚠️  {var}: Not configured")
        else:
            # Mask sensitive values
            if "KEY" in var or "URL" in var:
                masked = value[:20] + "..." if len(value) > 20 else value
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")

    if missing:
        print("\n⚠️  Some variables need configuration:")
        for m in missing:
            print(m)
        print("\n   For testing, you can use mock providers (no API keys needed)")

    return True

def check_database_connection():
    """Test database connection."""
    print_section("2. Testing Database Connection")

    try:
        from src.db.session import get_db
        from sqlalchemy import text

        print("🔍 Connecting to Supabase...")
        with get_db() as db:
            result = db.execute(text('SELECT version()')).scalar()
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {result[:50]}...")

            # Check tables
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = db.execute(tables_query).fetchall()

            if not tables:
                print("\n❌ No tables found!")
                print("   You need to run the migration SQL in Supabase Dashboard")
                print("   See SUPABASE_SETUP.md for instructions")
                return False

            print(f"\n📊 Found {len(tables)} table(s):")
            expected = ['entities', 'events', 'lead_state_history', 'leads_current', 'raw_events']
            for table in tables:
                table_name = table[0]
                status = "✅" if table_name in expected else "ℹ️"
                print(f"   {status} {table_name}")

            missing = set(expected) - {t[0] for t in tables}
            if missing:
                print(f"\n❌ Missing required tables: {', '.join(missing)}")
                print("   Run the migration SQL in Supabase Dashboard")
                return False

            return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n📝 Troubleshooting:")
        print("   1. Check your DATABASE_URL in .env file")
        print("   2. Verify Supabase project is active")
        print("   3. Confirm password is correct")
        print("   4. Check network connectivity")
        return False

def check_directory_structure():
    """Verify directory structure."""
    print_section("3. Checking Directory Structure")

    raw_bucket = Path("raw_data_bucket")
    if not raw_bucket.exists():
        print("❌ raw_data_bucket/ directory not found!")
        return False

    print("✅ raw_data_bucket/ exists")

    # Check subdirectories
    subdirs = {
        "companies": "Company news, funding, hiring announcements",
        "buildings": "Building demolition permits, construction data",
        "government": "Government contracts, bids, awards"
    }

    for subdir, description in subdirs.items():
        path = raw_bucket / subdir
        if path.exists():
            file_count = len(list(path.rglob("*.*")))
            print(f"✅ {subdir}/ ({file_count} files)")
        else:
            print(f"ℹ️  {subdir}/ (not created yet - {description})")

    return True

def check_dependencies():
    """Check Python dependencies."""
    print_section("4. Checking Dependencies")

    required = [
        ("sqlalchemy", "Database ORM"),
        ("psycopg2", "PostgreSQL driver"),
        ("dotenv", "Environment variables"),
        ("pydantic", "Data validation"),
    ]

    optional = [
        ("openai", "OpenAI API client"),
        ("anthropic", "Anthropic API client"),
    ]

    all_ok = True

    for package, description in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}: {description}")
        except ImportError:
            print(f"❌ {package}: {description} - MISSING!")
            all_ok = False

    print("\nOptional dependencies:")
    for package, description in optional:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}: {description}")
        except ImportError:
            print(f"ℹ️  {package}: {description} - Not installed (OK if using mock)")

    return all_ok

def show_next_steps(all_checks_passed):
    """Show next steps."""
    print_section("Summary & Next Steps")

    if all_checks_passed:
        print("✅ All checks passed! Your pipeline is ready to run.")
        print("\n🚀 To run the pipeline:")
        print("   python main.py")
        print("\n📊 To view results in Supabase:")
        print("   1. Go to https://app.supabase.com")
        print("   2. Navigate to Table Editor")
        print("   3. Browse: leads_current, entities, events")
        print("\n🔍 To query active leads:")
        print("   SELECT * FROM active_leads_view")
        print("   WHERE score >= 50")
        print("   ORDER BY score DESC;")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\n📚 For help, see:")
        print("   - SUPABASE_SETUP.md: Database setup guide")
        print("   - .env.example: Configuration template")
        print("   - README.md: Full documentation")

def main():
    """Run all verification checks."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          Leads Factory - Setup Verification                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    checks = [
        ("Environment Configuration", check_env_file),
        ("Database Connection", check_database_connection),
        ("Directory Structure", check_directory_structure),
        ("Python Dependencies", check_dependencies),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append(False)

    all_passed = all(results)
    show_next_steps(all_passed)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
