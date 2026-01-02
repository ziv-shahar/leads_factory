#!/usr/bin/env python3
"""Main entry point for lead intelligence pipeline."""
import sys
import argparse
from src.db.session import init_db, drop_db
from src.pipeline.runner import PipelineRunner


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lead Intelligence Pipeline")
    parser.add_argument(
        "command",
        choices=["init", "run", "reset"],
        help="Command to execute: init (initialize DB), run (run pipeline), reset (drop and reinit DB)"
    )

    args = parser.parse_args()

    if args.command == "init":
        print("Initializing database...")
        init_db()
        print("✓ Database initialized")

    elif args.command == "reset":
        response = input("⚠ This will DELETE all data. Are you sure? (yes/no): ")
        if response.lower() == "yes":
            print("Resetting database...")
            drop_db()
            init_db()
            print("✓ Database reset complete")
        else:
            print("Cancelled")

    elif args.command == "run":
        print("Running lead intelligence pipeline...")
        runner = PipelineRunner()
        runner.run()
        print("✓ Pipeline execution complete")


if __name__ == "__main__":
    main()
