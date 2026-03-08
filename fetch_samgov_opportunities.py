"""
Fetch complete government opportunity data from SAM.gov API and save to raw_data_bucket.

This script fetches real estate lease opportunities from SAM.gov with ALL fields:
- Office size (aboa_sf_min, aboa_sf_max)
- Budget (award_amount)
- Agency, location, status, notice_type
- And 30+ other fields needed for rich lead data
"""
import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

# SAM.gov API configuration
SAM_GOV_API_BASE = "https://api.sam.gov/opportunities/v2/search"
SAM_GOV_API_KEY = os.getenv("SAM_GOV_API_KEY")

# NAICS code for real estate leasing
NAICS_CODE_REAL_ESTATE = "531120"

# Output directory
OUTPUT_DIR = Path("raw_data_bucket/government/permits_and_opportunities/api_data")


def fetch_opportunities(
    posted_from: Optional[str] = None,
    posted_to: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch opportunities from SAM.gov API.

    Args:
        posted_from: Start date (YYYY-MM-DD)
        posted_to: End date (YYYY-MM-DD)
        limit: Number of results per page (max 1000)
        offset: Pagination offset

    Returns:
        API response with opportunities
    """
    if not SAM_GOV_API_KEY:
        raise ValueError(
            "SAM_GOV_API_KEY environment variable not set. "
            "Get your API key from https://sam.gov/data-services/"
        )

    # Build query parameters
    params = {
        "api_key": SAM_GOV_API_KEY,
        "ncode": NAICS_CODE_REAL_ESTATE,  # Real Estate Leasing only
        "limit": limit,
        "offset": offset,
        "ptype": "o,k,r,s",  # Office/lease related types (modify as needed)
    }

    # Add date filters if provided
    if posted_from:
        params["postedFrom"] = posted_from
    if posted_to:
        params["postedTo"] = posted_to

    print(f"Fetching opportunities (offset={offset}, limit={limit})...")
    print(f"  NAICS: {NAICS_CODE_REAL_ESTATE} (Real Estate Leasing)")
    if posted_from and posted_to:
        print(f"  Date Range: {posted_from} to {posted_to}")

    try:
        response = requests.get(SAM_GOV_API_BASE, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from SAM.gov: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        raise


def extract_opportunity_data(opp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format opportunity data from SAM.gov API response.

    Args:
        opp: Raw opportunity object from SAM.gov API

    Returns:
        Formatted opportunity dict with all fields
    """
    # Base fields
    data = {
        "opportunity_id": opp.get("noticeId"),
        "notice_id": opp.get("noticeId"),
        "solicitation_number": opp.get("solicitationNumber", ""),
        "title": opp.get("title", ""),
        "description": opp.get("description", ""),
        "agency": opp.get("fullParentPathName", "").split(".")[0] if opp.get("fullParentPathName") else opp.get("department", ""),
        "sub_agency": opp.get("subTier", ""),
        "naics_code": opp.get("naicsCode", ""),
        "notice_type": opp.get("type", ""),
        "status": map_status(opp.get("active", "")),
        "posted_date": opp.get("postedDate", ""),
        "response_deadline": opp.get("responseDeadLine", ""),
        "award_date": opp.get("awardDate"),
        "source_url": f"https://sam.gov/opp/{opp.get('noticeId')}/view" if opp.get("noticeId") else None,
    }

    # Location - extract from placeOfPerformance
    pop = opp.get("placeOfPerformance", {})
    if pop:
        # City
        city_data = pop.get("city", {})
        if isinstance(city_data, dict):
            data["city"] = city_data.get("name")
        elif isinstance(city_data, str):
            data["city"] = city_data
        else:
            data["city"] = None

        # State
        state_data = pop.get("state", {})
        if isinstance(state_data, dict):
            data["state"] = state_data.get("name") or state_data.get("code")
        elif isinstance(state_data, str):
            data["state"] = state_data
        else:
            data["state"] = None

        # Zip
        data["zip_code"] = pop.get("zip")
    else:
        data["city"] = None
        data["state"] = None
        data["zip_code"] = None

    # Office space details (check multiple possible fields)
    # SAM.gov sometimes puts these in additionalInfo or other nested fields
    additional_info = opp.get("additionalInfoLink", "") or ""

    # Try to extract ABOA (Usable Square Feet) from various fields
    data["aboa_sf_min"] = opp.get("aboaSfMin")
    data["aboa_sf_max"] = opp.get("aboaSfMax")
    data["delineated_area"] = opp.get("officeAddress", {}).get("city") or data.get("city")

    # Lease terms
    data["lease_term_years"] = opp.get("leaseTermYears")
    data["firm_term_years"] = opp.get("firmTermYears")
    data["tenant_improvement_allowance"] = opp.get("tenantImprovementAllowance")
    data["facility_security_level"] = opp.get("facilitySecurityLevel")
    data["parking_spaces"] = opp.get("parkingSpaces")
    data["parking_reserved"] = opp.get("parkingReserved")

    # Award information
    data["award_amount"] = opp.get("award", {}).get("amount") if opp.get("award") else None
    data["awardee_name"] = opp.get("award", {}).get("awardee", {}).get("name") if opp.get("award") else None

    # Contact
    contact = opp.get("pointOfContact", [{}])[0] if opp.get("pointOfContact") else {}
    data["contact_name"] = contact.get("fullName")
    data["contact_email"] = contact.get("email")
    data["contact_phone"] = contact.get("phone")

    # AAAP flag
    data["is_aaap"] = opp.get("isAAA") or False

    # Store raw API response for future reference
    data["raw_api_response"] = opp

    return data


def map_status(active_flag: str) -> str:
    """Map SAM.gov active flag to status string."""
    if not active_flag:
        return "unknown"

    active_lower = str(active_flag).lower()
    if active_lower in ["yes", "true", "active"]:
        return "active"
    elif active_lower in ["forecasted"]:
        return "forecasted"
    elif active_lower in ["awarded"]:
        return "awarded"
    else:
        return "inactive"


def save_opportunities_batch(opportunities: List[Dict[str, Any]], batch_name: str):
    """
    Save batch of opportunities to JSON file.

    Args:
        opportunities: List of opportunity dicts
        batch_name: Name for this batch (e.g., "2026-03-08_batch_1")
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / f"{batch_name}.json"

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_opportunities": len(opportunities),
        "opportunities": opportunities
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(opportunities)} opportunities to {output_file}")


def main():
    """Main function to fetch and save SAM.gov opportunities."""
    print("=" * 80)
    print("SAM.gov Opportunity Data Fetcher")
    print("=" * 80)

    # Date range: last 30 days
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)

    posted_from = from_date.strftime("%Y-%m-%d")
    posted_to = to_date.strftime("%Y-%m-%d")

    print(f"\nFetching opportunities from {posted_from} to {posted_to}")
    print(f"NAICS Code: {NAICS_CODE_REAL_ESTATE} (Real Estate Leasing)")

    all_opportunities = []
    offset = 0
    limit = 100  # SAM.gov allows up to 1000, but 100 is safer

    while True:
        try:
            # Fetch batch
            response = fetch_opportunities(
                posted_from=posted_from,
                posted_to=posted_to,
                limit=limit,
                offset=offset
            )

            # Extract opportunities from response
            opportunities_raw = response.get("opportunitiesData", [])

            if not opportunities_raw:
                print(f"No more opportunities found (offset={offset})")
                break

            # Process each opportunity
            for opp_raw in opportunities_raw:
                opp_data = extract_opportunity_data(opp_raw)
                all_opportunities.append(opp_data)

            print(f"  Fetched {len(opportunities_raw)} opportunities (total so far: {len(all_opportunities)})")

            # Check if there are more pages
            total_records = response.get("totalRecords", 0)
            if offset + len(opportunities_raw) >= total_records:
                print(f"Reached end of results (total: {total_records})")
                break

            # Move to next page
            offset += limit

            # Rate limiting - be nice to SAM.gov API
            time.sleep(1)

        except Exception as e:
            print(f"Error fetching batch at offset {offset}: {e}")
            break

    # Save all opportunities
    if all_opportunities:
        batch_name = f"samgov_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_opportunities_batch(all_opportunities, batch_name)

        print(f"\n✅ Successfully fetched {len(all_opportunities)} opportunities!")
        print(f"   Output: {OUTPUT_DIR}")

        # Print sample
        if len(all_opportunities) > 0:
            sample = all_opportunities[0]
            print(f"\nSample opportunity:")
            print(f"  Title: {sample.get('title')}")
            print(f"  Agency: {sample.get('agency')}")
            print(f"  Location: {sample.get('city')}, {sample.get('state')}")
            print(f"  Size: {sample.get('aboa_sf_min')}-{sample.get('aboa_sf_max')} sq ft")
            print(f"  Status: {sample.get('status')}")
    else:
        print("\n⚠️  No opportunities found")

    print("\n" + "=" * 80)
    print("Next steps:")
    print("1. Run the pipeline to process these opportunities:")
    print("   python main.py")
    print("2. Check the web app to see the leads with complete data!")
    print("=" * 80)


if __name__ == "__main__":
    main()
