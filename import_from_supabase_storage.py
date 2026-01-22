"""
Import files from Supabase Storage to local raw_data_bucket for processing.

Usage:
    python import_from_supabase_storage.py

Configuration:
    Set these environment variables or edit them below:
    - SOURCE_SUPABASE_URL: URL of the Supabase project with storage
    - SOURCE_SUPABASE_KEY: Service role key or anon key
    - SOURCE_BUCKET_NAME: Name of the storage bucket
    - SOURCE_FOLDER_PATH: Folder path in the bucket (e.g., "raw_data" or "leads/2024")
"""

import os
from pathlib import Path
from supabase import create_client, Client
from typing import List, Optional
import sys
from dotenv import load_dotenv

# Load .env.storage if it exists
if Path(".env.storage").exists():
    load_dotenv(".env.storage")

# ============================================================================
# Configuration
# ============================================================================

# Option 1: Set via environment variables (recommended)
SOURCE_SUPABASE_URL = os.getenv("SOURCE_SUPABASE_URL", "")
SOURCE_SUPABASE_KEY = os.getenv("SOURCE_SUPABASE_KEY", "")
SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME", "")
SOURCE_FOLDER_PATH = os.getenv("SOURCE_FOLDER_PATH", "")  # e.g., "raw_data" or "" for root

# Option 2: Or set them directly here (less secure for git repos)
# SOURCE_SUPABASE_URL = "https://xxxxx.supabase.co"
# SOURCE_SUPABASE_KEY = "your-service-role-key-here"
# SOURCE_BUCKET_NAME = "your-bucket-name"
# SOURCE_FOLDER_PATH = "raw_data"  # or "" for root

# Local destination
LOCAL_RAW_DATA_BUCKET = Path("/home/user/leads_factory/raw_data_bucket")

# ============================================================================
# Helper Functions
# ============================================================================

def list_files_in_storage(
    supabase: Client,
    bucket_name: str,
    folder_path: str = ""
) -> List[dict]:
    """
    List all files in a Supabase Storage bucket/folder.

    Returns list of file objects with 'name', 'id', 'created_at', etc.
    """
    try:
        # List files in the bucket
        result = supabase.storage.from_(bucket_name).list(folder_path)

        all_files = []
        for item in result:
            # If it's a file (not a folder)
            if item.get('metadata') or not item.get('id'):
                # Build full path
                if folder_path:
                    full_path = f"{folder_path}/{item['name']}"
                else:
                    full_path = item['name']

                all_files.append({
                    'name': item['name'],
                    'path': full_path,
                    'size': item.get('metadata', {}).get('size', 0),
                    'created_at': item.get('created_at'),
                })
            else:
                # It's a folder - recursively list
                subfolder = f"{folder_path}/{item['name']}" if folder_path else item['name']
                subfiles = list_files_in_storage(supabase, bucket_name, subfolder)
                all_files.extend(subfiles)

        return all_files

    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def download_file(
    supabase: Client,
    bucket_name: str,
    file_path: str,
    local_destination: Path
) -> bool:
    """
    Download a single file from Supabase Storage.

    Args:
        supabase: Supabase client
        bucket_name: Name of the storage bucket
        file_path: Path to file in storage (e.g., "companies/doc_01.json")
        local_destination: Local file path to save to

    Returns:
        True if successful, False otherwise
    """
    try:
        # Download file
        data = supabase.storage.from_(bucket_name).download(file_path)

        # Create parent directories if needed
        local_destination.parent.mkdir(parents=True, exist_ok=True)

        # Write to local file
        with open(local_destination, 'wb') as f:
            f.write(data)

        print(f"  ✓ Downloaded: {file_path} → {local_destination}")
        return True

    except Exception as e:
        print(f"  ✗ Error downloading {file_path}: {e}")
        return False


def import_from_storage(
    source_url: str,
    source_key: str,
    bucket_name: str,
    folder_path: str,
    local_destination: Path
) -> dict:
    """
    Import all files from a Supabase Storage bucket to local directory.

    Returns:
        Dictionary with success/failure counts
    """
    # Create Supabase client for source project
    print(f"\n🔗 Connecting to source Supabase project...")
    print(f"   URL: {source_url}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Folder: {folder_path or '(root)'}")

    try:
        supabase = create_client(source_url, source_key)
    except Exception as e:
        print(f"✗ Error connecting to Supabase: {e}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    # List all files
    print(f"\n📂 Listing files in storage...")
    files = list_files_in_storage(supabase, bucket_name, folder_path)

    if not files:
        print("⚠ No files found in storage")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    print(f"   Found {len(files)} files")

    # Download each file
    print(f"\n⬇️  Downloading files to {local_destination}...\n")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for file_info in files:
        file_path = file_info['path']

        # Determine local path (preserve directory structure)
        # Remove the source folder prefix if it exists
        relative_path = file_path
        if folder_path and file_path.startswith(folder_path + "/"):
            relative_path = file_path[len(folder_path) + 1:]
        elif folder_path and file_path.startswith(folder_path):
            relative_path = file_path[len(folder_path):]

        local_file_path = local_destination / relative_path

        # Check if file already exists
        if local_file_path.exists():
            print(f"  ⊘ Skipped (exists): {file_path}")
            skipped_count += 1
            continue

        # Download file
        if download_file(supabase, bucket_name, file_path, local_file_path):
            success_count += 1
        else:
            failed_count += 1

    return {
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count
    }


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 80)
    print("Import Files from Supabase Storage")
    print("=" * 80)

    # Validate configuration
    if not SOURCE_SUPABASE_URL or not SOURCE_SUPABASE_KEY:
        print("\n✗ Error: Missing configuration!")
        print("\nPlease set environment variables:")
        print("  export SOURCE_SUPABASE_URL='https://xxxxx.supabase.co'")
        print("  export SOURCE_SUPABASE_KEY='your-key-here'")
        print("  export SOURCE_BUCKET_NAME='your-bucket-name'")
        print("  export SOURCE_FOLDER_PATH='optional-folder-path'")
        print("\nOr edit the script and set them directly in the Configuration section.")
        sys.exit(1)

    if not SOURCE_BUCKET_NAME:
        print("\n✗ Error: SOURCE_BUCKET_NAME is required!")
        sys.exit(1)

    # Create local destination directory
    LOCAL_RAW_DATA_BUCKET.mkdir(parents=True, exist_ok=True)

    # Import files
    results = import_from_storage(
        source_url=SOURCE_SUPABASE_URL,
        source_key=SOURCE_SUPABASE_KEY,
        bucket_name=SOURCE_BUCKET_NAME,
        folder_path=SOURCE_FOLDER_PATH,
        local_destination=LOCAL_RAW_DATA_BUCKET
    )

    # Summary
    print("\n" + "=" * 80)
    print("Import Complete")
    print("=" * 80)
    print(f"  ✓ Successfully downloaded: {results['success']} files")
    print(f"  ⊘ Skipped (already exist): {results['skipped']} files")
    print(f"  ✗ Failed: {results['failed']} files")
    print("=" * 80)

    if results['success'] > 0:
        print(f"\n✓ Files saved to: {LOCAL_RAW_DATA_BUCKET}")
        print("\nNext steps:")
        print("  1. Run the pipeline: python3 main.py run")
        print("  2. View results in Supabase database")


if __name__ == "__main__":
    main()
