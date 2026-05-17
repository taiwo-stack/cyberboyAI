import whois
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import lru_cache

# Shared executor — limited to avoid resource exhaustion
_whois_executor = ThreadPoolExecutor(max_workers=3)


def _whois_lookup(domain: str) -> int:
    """Runs the blocking whois call inside a thread."""
    w = whois.whois(domain)
    creation_date = w.creation_date
    if isinstance(creation_date, list):
        creation_date = creation_date[0]
    if not creation_date or not isinstance(creation_date, datetime):
        return -1   # WHOIS returned no useful data — treat as unknown
    age = datetime.now() - creation_date
    return max(0, age.days)


@lru_cache(maxsize=2048)
def _cached_whois(domain: str) -> int:
    """
    In-memory LRU cache for WHOIS results.
    Avoids re-querying WHOIS for the same domain on repeated scans.
    """
    try:
        future = _whois_executor.submit(_whois_lookup, domain)
        return future.result(timeout=5)
    except (FuturesTimeoutError, Exception):
        return -1   # Unknown, not zero — prevents false high-risk bias


def get_domain_age_days(domain: str) -> int:
    """
    Returns the age of a domain in days.

    Returns:
        int >= 0  → known age in days
        -1         → age unknown (WHOIS timeout, blocked, or private registration)

    Callers should treat -1 as missing data, NOT as a brand-new (high-risk) domain.
    The ML model receives this value directly; -1 is handled by the feature vector.
    """
    return _cached_whois(domain)


