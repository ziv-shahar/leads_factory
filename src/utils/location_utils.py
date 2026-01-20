"""Location utilities for normalizing and extracting location data."""
from typing import Optional


# Comprehensive state name to code mapping
STATE_NORMALIZATION_MAP = {
    # Full state names (lowercase for case-insensitive matching)
    'alabama': 'AL',
    'alaska': 'AK',
    'arizona': 'AZ',
    'arkansas': 'AR',
    'california': 'CA',
    'colorado': 'CO',
    'connecticut': 'CT',
    'delaware': 'DE',
    'florida': 'FL',
    'georgia': 'GA',
    'hawaii': 'HI',
    'idaho': 'ID',
    'illinois': 'IL',
    'indiana': 'IN',
    'iowa': 'IA',
    'kansas': 'KS',
    'kentucky': 'KY',
    'louisiana': 'LA',
    'maine': 'ME',
    'maryland': 'MD',
    'massachusetts': 'MA',
    'michigan': 'MI',
    'minnesota': 'MN',
    'mississippi': 'MS',
    'missouri': 'MO',
    'montana': 'MT',
    'nebraska': 'NE',
    'nevada': 'NV',
    'new hampshire': 'NH',
    'new jersey': 'NJ',
    'new mexico': 'NM',
    'new york': 'NY',
    'north carolina': 'NC',
    'north dakota': 'ND',
    'ohio': 'OH',
    'oklahoma': 'OK',
    'oregon': 'OR',
    'pennsylvania': 'PA',
    'rhode island': 'RI',
    'south carolina': 'SC',
    'south dakota': 'SD',
    'tennessee': 'TN',
    'texas': 'TX',
    'utah': 'UT',
    'vermont': 'VT',
    'virginia': 'VA',
    'washington': 'WA',
    'west virginia': 'WV',
    'wisconsin': 'WI',
    'wyoming': 'WY',

    # Territories
    'district of columbia': 'DC',
    'puerto rico': 'PR',
    'virgin islands': 'VI',
    'guam': 'GU',
    'american samoa': 'AS',
    'northern mariana islands': 'MP',

    # Abbreviations (both cases)
    'al': 'AL', 'ak': 'AK', 'az': 'AZ', 'ar': 'AR', 'ca': 'CA',
    'co': 'CO', 'ct': 'CT', 'de': 'DE', 'fl': 'FL', 'ga': 'GA',
    'hi': 'HI', 'id': 'ID', 'il': 'IL', 'in': 'IN', 'ia': 'IA',
    'ks': 'KS', 'ky': 'KY', 'la': 'LA', 'me': 'ME', 'md': 'MD',
    'ma': 'MA', 'mi': 'MI', 'mn': 'MN', 'ms': 'MS', 'mo': 'MO',
    'mt': 'MT', 'ne': 'NE', 'nv': 'NV', 'nh': 'NH', 'nj': 'NJ',
    'nm': 'NM', 'ny': 'NY', 'nc': 'NC', 'nd': 'ND', 'oh': 'OH',
    'ok': 'OK', 'or': 'OR', 'pa': 'PA', 'ri': 'RI', 'sc': 'SC',
    'sd': 'SD', 'tn': 'TN', 'tx': 'TX', 'ut': 'UT', 'vt': 'VT',
    'va': 'VA', 'wa': 'WA', 'wv': 'WV', 'wi': 'WI', 'wy': 'WY',
    'dc': 'DC', 'pr': 'PR', 'vi': 'VI', 'gu': 'GU', 'as': 'AS', 'mp': 'MP',
}

# Valid 2-letter state codes (for validation)
VALID_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
}


def normalize_state(state: Optional[str]) -> Optional[str]:
    """
    Normalize any state format to standard 2-letter code.

    Handles:
    - Full names: "Florida" → "FL"
    - Mixed case: "florida", "FLORIDA", "Florida" → "FL"
    - Already normalized: "FL" → "FL"
    - Lowercase codes: "fl" → "FL"

    Args:
        state: State name or code in any format

    Returns:
        Normalized 2-letter state code or None if invalid/not found

    Examples:
        >>> normalize_state("Florida")
        'FL'
        >>> normalize_state("florida")
        'FL'
        >>> normalize_state("FL")
        'FL'
        >>> normalize_state("fl")
        'FL'
        >>> normalize_state("Puerto Rico")
        'PR'
        >>> normalize_state("Invalid")
        None
    """
    if not state:
        return None

    state_clean = state.strip()
    if not state_clean:
        return None

    # Check if already a valid 2-letter code (case-insensitive)
    state_upper = state_clean.upper()
    if state_upper in VALID_STATE_CODES:
        return state_upper

    # Try to find in normalization map (case-insensitive)
    state_lower = state_clean.lower()
    normalized = STATE_NORMALIZATION_MAP.get(state_lower)

    return normalized


def is_valid_state_code(state: Optional[str]) -> bool:
    """
    Check if a string is a valid 2-letter state code.

    Args:
        state: State code to validate

    Returns:
        True if valid state code, False otherwise

    Examples:
        >>> is_valid_state_code("FL")
        True
        >>> is_valid_state_code("fl")
        True
        >>> is_valid_state_code("ZZ")
        False
        >>> is_valid_state_code("Florida")
        False
    """
    if not state:
        return False
    return state.upper() in VALID_STATE_CODES


def normalize_city(city: Optional[str]) -> Optional[str]:
    """
    Normalize city name to title case.

    Args:
        city: City name in any format

    Returns:
        Normalized city name or None if invalid

    Examples:
        >>> normalize_city("miami")
        'Miami'
        >>> normalize_city("NEW YORK")
        'New York'
        >>> normalize_city("San Francisco")
        'San Francisco'
    """
    if not city:
        return None

    city_clean = city.strip()
    if not city_clean:
        return None

    # Convert to title case
    return city_clean.title()
