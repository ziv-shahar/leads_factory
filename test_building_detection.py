"""Quick test to verify building data source detection."""
from src.io.raw_reader import RawFileReader
from src.config import RAW_DATA_BUCKET

def test_data_source_detection():
    """Test that data source type detection works correctly."""
    reader = RawFileReader(str(RAW_DATA_BUCKET))

    print("Testing data source detection...\n")
    print("=" * 80)

    # Get file entries
    entries = reader.list_files_with_merge()

    # Group by data source type
    by_type = {"companies": [], "buildings": [], "government": []}

    for entry in entries:
        data_source_type = entry.get('data_source_type', 'unknown')
        path = entry['path']

        if data_source_type in by_type:
            by_type[data_source_type].append(path)
        else:
            print(f"WARNING: Unknown data source type '{data_source_type}' for {path}")

    # Print results
    for source_type, paths in by_type.items():
        print(f"\n{source_type.upper()} ({len(paths)} entries):")
        print("-" * 80)
        for path in paths[:5]:  # Show first 5
            print(f"  - {path}")
        if len(paths) > 5:
            print(f"  ... and {len(paths) - 5} more")

    print("\n" + "=" * 80)
    print(f"Total entries: {len(entries)}")
    print(f"  Companies: {len(by_type['companies'])}")
    print(f"  Buildings: {len(by_type['buildings'])}")
    print(f"  Government: {len(by_type['government'])}")
    print("=" * 80)

    # Verify buildings were detected
    if len(by_type['buildings']) == 0:
        print("\n❌ ERROR: No building entries detected!")
        return False
    else:
        print(f"\n✅ SUCCESS: {len(by_type['buildings'])} building entries detected")
        return True

if __name__ == "__main__":
    success = test_data_source_detection()
    exit(0 if success else 1)
