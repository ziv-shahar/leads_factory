"""
Import existing SAM.gov opportunity JSON data into the pipeline.

Use this script if you already have SAM.gov JSON data downloaded.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Output directory
OUTPUT_DIR = Path("raw_data_bucket/government/permits_and_opportunities/api_data")


def import_opportunity_json(input_file: str):
    """
    Import opportunity JSON file and save to pipeline directory.

    Args:
        input_file: Path to JSON file with opportunities data
    """
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        return

    print(f"Reading opportunities from: {input_file}")

    # Read input JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle different JSON structures
    if isinstance(data, dict) and "opportunities" in data:
        opportunities = data["opportunities"]
        print(f"Found {len(opportunities)} opportunities in file")
    elif isinstance(data, list):
        opportunities = data
        print(f"Found {len(opportunities)} opportunities in file")
    else:
        print(f"❌ Error: Unexpected JSON structure")
        print(f"Expected: {{'opportunities': [...]}} or [...]")
        return

    if not opportunities:
        print("⚠️  No opportunities found in file")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = OUTPUT_DIR / f"imported_{timestamp}.json"

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "source_file": str(input_path),
        "total_opportunities": len(opportunities),
        "opportunities": opportunities
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(opportunities)} opportunities to: {output_file}")

    # Print stats
    print("\nOpportunity Statistics:")
    print(f"  Total: {len(opportunities)}")

    # Count by status
    statuses = {}
    has_size = 0
    has_budget = 0

    for opp in opportunities:
        status = opp.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1

        if opp.get("aboa_sf_min") or opp.get("aboa_sf_max"):
            has_size += 1
        if opp.get("award_amount"):
            has_budget += 1

    print(f"\n  By Status:")
    for status, count in sorted(statuses.items()):
        print(f"    {status}: {count}")

    print(f"\n  With Data:")
    print(f"    Has Size: {has_size}/{len(opportunities)} ({has_size/len(opportunities)*100:.1f}%)")
    print(f"    Has Budget: {has_budget}/{len(opportunities)} ({has_budget/len(opportunities)*100:.1f}%)")

    # Sample opportunity
    if opportunities:
        sample = opportunities[0]
        print(f"\n  Sample Opportunity:")
        print(f"    Title: {sample.get('title', 'N/A')}")
        print(f"    Agency: {sample.get('agency', 'N/A')}")
        print(f"    Location: {sample.get('city', 'N/A')}, {sample.get('state', 'N/A')}")
        print(f"    Size: {sample.get('aboa_sf_min', 'N/A')}-{sample.get('aboa_sf_max', 'N/A')} sq ft")
        print(f"    Status: {sample.get('status', 'N/A')}")
        print(f"    Notice Type: {sample.get('notice_type', 'N/A')}")

    print("\n" + "=" * 80)
    print("Next steps:")
    print("1. Run the pipeline to process these opportunities:")
    print("   python main.py")
    print("2. The opportunities will be ingested with complete data!")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_opportunity_json.py <path_to_json_file>")
        print("\nExample:")
        print("  python import_opportunity_json.py opportunities.json")
        sys.exit(1)

    import_opportunity_json(sys.argv[1])
