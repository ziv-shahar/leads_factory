"""
Migration script: Add entity_type and metadata fields to entities table.

This migrates existing databases from the old Entity model to the new unified model.

Usage:
    python migrate_to_unified_entities.py

What it does:
1. Adds entity_type column (defaults to 'company' for existing entities)
2. Adds metadata JSONB column
3. Migrates existing fields (website_url, linkedin_url, hq_city, hq_state) to metadata
4. Creates index on entity_type
5. Removes old columns (optional - commented out for safety)
"""
import sys
from sqlalchemy import create_engine, text
from src.config import DATABASE_URL

def migrate():
    """Run migration."""
    engine = create_engine(DATABASE_URL)

    print("Starting migration to unified entity model...")

    with engine.begin() as conn:
        # Check if entities table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'entities'
            );
        """))
        if not result.scalar():
            print("✗ Entities table does not exist. Run init_db() first.")
            return False

        # Check if entity_type column already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'entities' AND column_name = 'entity_type'
            );
        """))

        if result.scalar():
            print("✓ Migration already applied (entity_type column exists)")
            return True

        print("Step 1: Adding entity_type column...")
        conn.execute(text("""
            ALTER TABLE entities
            ADD COLUMN entity_type VARCHAR(50);
        """))
        print("  ✓ Added entity_type column")

        print("Step 2: Setting default entity_type to 'company' for existing entities...")
        conn.execute(text("""
            UPDATE entities
            SET entity_type = 'company'
            WHERE entity_type IS NULL;
        """))
        print("  ✓ Set default entity_type")

        print("Step 3: Adding entity_metadata JSONB column...")
        conn.execute(text("""
            ALTER TABLE entities
            ADD COLUMN entity_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
        """))
        print("  ✓ Added entity_metadata column")

        print("Step 4: Migrating existing data to entity_metadata...")
        # Check if old columns exist before migrating
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'entities' AND column_name = 'website_url'
            );
        """))

        if result.scalar():
            conn.execute(text("""
                UPDATE entities
                SET entity_metadata = jsonb_build_object(
                    'website_url', website_url,
                    'linkedin_url', linkedin_url,
                    'hq_city', hq_city,
                    'hq_state', hq_state
                )
                WHERE website_url IS NOT NULL
                   OR linkedin_url IS NOT NULL
                   OR hq_city IS NOT NULL
                   OR hq_state IS NOT NULL;
            """))
            print("  ✓ Migrated existing data to entity_metadata")
        else:
            print("  ✓ No old columns to migrate (fresh database)")

        print("Step 5: Creating index on entity_type...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_entities_entity_type
            ON entities(entity_type);
        """))
        print("  ✓ Created index")

        print("\n⚠ OPTIONAL: Remove old columns (currently commented out for safety)")
        print("If you're confident the migration worked, uncomment the following SQL:")
        print("  ALTER TABLE entities DROP COLUMN IF EXISTS website_url;")
        print("  ALTER TABLE entities DROP COLUMN IF EXISTS linkedin_url;")
        print("  ALTER TABLE entities DROP COLUMN IF EXISTS hq_city;")
        print("  ALTER TABLE entities DROP COLUMN IF EXISTS hq_state;")

        # Uncomment to remove old columns (after verifying migration worked):
        # conn.execute(text("ALTER TABLE entities DROP COLUMN IF EXISTS website_url;"))
        # conn.execute(text("ALTER TABLE entities DROP COLUMN IF EXISTS linkedin_url;"))
        # conn.execute(text("ALTER TABLE entities DROP COLUMN IF EXISTS hq_city;"))
        # conn.execute(text("ALTER TABLE entities DROP COLUMN IF EXISTS hq_state;"))

        print("\n✓ Migration completed successfully!")
        return True

if __name__ == "__main__":
    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        sys.exit(1)
