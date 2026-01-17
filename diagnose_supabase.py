#!/usr/bin/env python3
"""
Diagnostic script to test different Supabase connection methods.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection(connection_string, name):
    """Test a specific connection string."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}")

    try:
        import psycopg2

        # Mask password in display
        display_str = connection_string
        if '@' in display_str:
            parts = display_str.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                if len(user_pass) >= 3:
                    display_str = f"{user_pass[0]}:{user_pass[1]}:****@{parts[1]}"

        print(f"Connection string: {display_str}")
        print("Attempting connection...")

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        print(f"✅ SUCCESS!")
        print(f"PostgreSQL version: {version[:80]}...")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          Supabase Connection Diagnostics                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Get base connection info
    project_ref = "qmnsqztyduzvfimnkhtu"
    password = "Wk2sQvM2fFjPlgLM"
    database = "postgres"

    # Test different connection methods
    connections = [
        {
            "name": "Session Pooler (IPv4 - Current)",
            "url": f"postgresql://postgres.{project_ref}:{password}@aws-1-us-west-1.pooler.supabase.com:5432/{database}?sslmode=require"
        },
        {
            "name": "Transaction Pooler (Port 6543)",
            "url": f"postgresql://postgres.{project_ref}:{password}@aws-1-us-west-1.pooler.supabase.com:6543/{database}?sslmode=require"
        },
        {
            "name": "Direct Connection (IPv6)",
            "url": f"postgresql://postgres.{project_ref}:{password}@db.{project_ref}.supabase.co:5432/{database}?sslmode=require"
        },
        {
            "name": "Session Pooler with sslmode=prefer",
            "url": f"postgresql://postgres.{project_ref}:{password}@aws-1-us-west-1.pooler.supabase.com:5432/{database}?sslmode=prefer"
        },
        {
            "name": "Session Pooler with sslmode=disable",
            "url": f"postgresql://postgres.{project_ref}:{password}@aws-1-us-west-1.pooler.supabase.com:5432/{database}?sslmode=disable"
        },
    ]

    results = []
    for conn_config in connections:
        success = test_connection(conn_config["url"], conn_config["name"])
        results.append((conn_config["name"], success))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successes = [name for name, success in results if success]
    failures = [name for name, success in results if not success]

    if successes:
        print("\n✅ Successful connections:")
        for name in successes:
            print(f"   - {name}")
        print("\n💡 Update your .env to use one of the successful connection strings above!")
    else:
        print("\n❌ All connection attempts failed!")
        print("\n🔍 This suggests:")
        print("   1. IP restrictions in Supabase project settings")
        print("   2. Database paused or pooler disabled")
        print("   3. Network/firewall blocking Supabase")
        print("\n📋 Next steps:")
        print("   1. Go to https://app.supabase.com/project/qmnsqztyduzvfimnkhtu/settings/database")
        print("   2. Check if 'Connection Pooling' is enabled")
        print("   3. Check 'Restrictions' section for IP allowlist")
        print("   4. Check 'General' section - is database paused?")
        print("   5. Try accessing from a different network (mobile hotspot)")

    if failures:
        print(f"\n⚠️  Failed connections ({len(failures)}):")
        for name in failures:
            print(f"   - {name}")

if __name__ == "__main__":
    main()
