"""Simple test to verify building data source detection without full imports."""
from pathlib import Path

def detect_data_source_type(file_path: str, bucket_path: Path) -> str:
    """
    Detect data source type from file path structure.
    (Copy of the method from raw_reader.py for testing)
    """
    path = Path(file_path)

    # Get path parts relative to bucket
    try:
        relative_path = path.relative_to(bucket_path)
        path_parts = relative_path.parts
    except ValueError:
        # If not under bucket_path, use full path
        path_parts = path.parts

    # Check for data source type in path parts
    for part in path_parts:
        part_lower = part.lower()
        if part_lower == "buildings":
            return "buildings"
        elif part_lower == "companies":
            return "companies"
        elif part_lower == "government":
            return "government"

    # Default to companies if no type detected
    return "companies"

def test_detection():
    """Test data source detection logic."""
    bucket_path = Path("/home/user/leads_factory/raw_data_bucket/")

    test_cases = [
        ("buildings/miami_permit.json", "buildings"),
        ("buildings/subdir/permit.txt", "buildings"),
        ("companies/news.html", "companies"),
        ("companies/data_source1/merge.txt", "companies"),
        ("government/rfps/bid.pdf", "government"),
        ("legacy_file.txt", "companies"),  # Default
    ]

    print("Testing data source detection logic...\n")
    print("=" * 80)

    all_passed = True
    for file_path, expected in test_cases:
        full_path = bucket_path / file_path
        detected = detect_data_source_type(str(full_path), bucket_path)

        status = "✅" if detected == expected else "❌"
        print(f"{status} {file_path}")
        print(f"   Expected: {expected}, Got: {detected}")

        if detected != expected:
            all_passed = False

    print("=" * 80)

    # Test with actual files
    print("\nTesting with actual files in raw_data_bucket:\n")
    print("=" * 80)

    if bucket_path.exists():
        # Count files by type
        by_type = {"companies": 0, "buildings": 0, "government": 0}

        for item in bucket_path.rglob("*"):
            if item.is_file() and item.suffix in ['.json', '.txt', '.html', '.pdf']:
                detected = detect_data_source_type(str(item), bucket_path)
                by_type[detected] += 1

        print(f"Companies:  {by_type['companies']} files")
        print(f"Buildings:  {by_type['buildings']} files")
        print(f"Government: {by_type['government']} files")
        print("=" * 80)

        if by_type['buildings'] > 0:
            print(f"\n✅ SUCCESS: Found {by_type['buildings']} building files")
            return all_passed
        else:
            print("\n❌ ERROR: No building files found!")
            return False
    else:
        print(f"❌ ERROR: Bucket path not found: {bucket_path}")
        return False

if __name__ == "__main__":
    success = test_detection()
    exit(0 if success else 1)
