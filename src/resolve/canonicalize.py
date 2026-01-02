"""Name canonicalization utilities for entity matching."""
import re
from typing import Tuple


def canonicalize_company_name(raw_name: str) -> Tuple[str, str]:
    """
    Canonicalize company name into two forms for matching.

    Args:
        raw_name: Raw company name from source

    Returns:
        Tuple of (canonical_name, normalized_name)
        - canonical_name: UPPERCASE, legal suffixes removed, whitespace normalized
        - normalized_name: All non-alphanumeric removed (for fuzzy matching)
    """
    if not raw_name:
        return "", ""

    # Start with uppercase
    canonical = raw_name.upper().strip()

    # Remove common legal suffixes (must be at end)
    suffixes = [
        r'\s+INC\.?$',
        r'\s+INCORPORATED$',
        r'\s+LLC\.?$',
        r'\s+L\.L\.C\.?$',
        r'\s+LTD\.?$',
        r'\s+LIMITED$',
        r'\s+CORP\.?$',
        r'\s+CORPORATION$',
        r'\s+CO\.?$',
        r'\s+COMPANY$',
        r'\s+LP\.?$',
        r'\s+L\.P\.?$',
        r'\s+LLP\.?$',
        r'\s+L\.L\.P\.?$',
    ]

    for suffix_pattern in suffixes:
        canonical = re.sub(suffix_pattern, '', canonical)

    # Normalize common patterns
    canonical = canonical.replace(' AND ', ' & ')
    canonical = canonical.replace(',', ' ')

    # Normalize whitespace
    canonical = ' '.join(canonical.split())

    # Create normalized version (alphanumeric only)
    normalized = re.sub(r'[^A-Z0-9]', '', canonical)

    return canonical, normalized


def extract_domain_from_url(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Full URL (e.g., "https://www.acmecloud.io/about")

    Returns:
        Domain only (e.g., "acmecloud.io")
    """
    if not url:
        return ""

    # Remove protocol
    domain = url.lower()
    domain = re.sub(r'^https?://', '', domain)

    # Remove www.
    domain = re.sub(r'^www\.', '', domain)

    # Remove path
    domain = domain.split('/')[0]

    # Remove port
    domain = domain.split(':')[0]

    return domain
