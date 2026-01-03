#!/usr/bin/env python3
"""Reset database - drop all tables and recreate with new schema."""
from src.db.session import init_db
from src.db.models import Base
from src.db.session import engine

print("Resetting database...")
print("⚠ WARNING: This will DELETE ALL DATA!")

# Drop all tables
print("→ Dropping all tables...")
Base.metadata.drop_all(engine)
print("✓ Dropped all tables")

# Recreate tables with new schema
print("→ Recreating tables with new schema...")
init_db()
print("✓ Created tables")

print("\n✓ Database reset complete!")
print("You can now run: python main.py run")
