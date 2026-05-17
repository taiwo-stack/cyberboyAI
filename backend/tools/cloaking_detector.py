"""
CloakingDetector
================
Detects ASN-based cloaking by requesting the same URL from two different
perspectives and comparing the responses for suspicious divergence.

Attack pattern being caught:
  A phishing site detects that a visitor is coming from a datacenter IP and
  serves a clean "decoy" page. Real victims (coming from residential ISPs)
  see the actual credential-harvesting phishing form.

Detection approach (no residential proxies required):
  1. Fetch the page with our normal Chrome UA (datacenter-looking request)
  2. Fetch the same URL with a mobile UA + Accept-Language suggesting a Nigerian
     residential user
  3. Compare response status codes, content length, and key term presence
  4. If significant divergence is detected, escalate the cloaking_score

Limitations:
  - Cannot prove cloaking, only signal suspicion
  - Sophisticated kits that serve identical clean pages to all automated
    tools regardless of UA will evade this check
  - Server-side IP-based checks (not UA-based) require residential proxies
"""

import asyncio
import re
import httpx

# Desktop datacenter-looking UA
_UA_DATACENTER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Nigerian mobile user simulation
_UA_MOBILE_NG = (
    "Mozilla/5.0 (Linux; Android 13; Tecno Spark 10 Pro) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.6099.144 Mobile Safari/537.36"
)

_HEADERS_DATACENTER = {
    "User-Agent": _UA_DATACENTER,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_HEADERS_MOBILE_NG = {
    "User-Agent": _UA_MOBILE_NG,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-NG,en;q=0.9,yo;q=0.8,ig;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# Credential-harvesting markers that should raise suspicion if only present
# in the "user-facing" response and not the scanner-facing one
_PHISHING_MARKERS = [
    r"password", r"login", r"sign.?in", r"verify", r"account",
    r"otp", r"bvn", r"nin", r"credit.?card", r"atm.?pin",
    r"<input[^>]*type=['\"]password", r"<form[^>]*action",
]


async def _fetch(url: str, headers: dict, timeout: float = 8.0) -> tuple[int, str]:
    """Fetch a URL and return (status_code, body_text)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
            verify=True,
        ) as client:
            resp = await client.get(url)
            return resp.status_code, resp.text[:8000]
    except Exception:
        return 0, ""


def _count_markers(text: str) -> int:
    """Count how many phishing marker patterns appear in the page text."""
    text_lower = text.lower()
    return sum(1 for p in _PHISHING_MARKERS if re.search(p, text_lower))


async def detect_cloaking(url: str, is_trusted: bool = False) -> dict:
    """
    Runs a dual-perspective fetch and scores the likelihood of cloaking.
    If 'is_trusted' is True, we bypass this check to avoid false positives 
    on major platforms (like Amazon/Google) that naturally block crawlers.
    """
    if is_trusted:
        return {
            "cloaking_score": 0.0,
            "is_suspicious": False,
            "evidence": [],
            "datacenter_status": 200,
            "mobile_status": 200,
        }

    evidence = []

    # Run both requests in parallel
    (dc_status, dc_body), (mob_status, mob_body) = await asyncio.gather(
        _fetch(url, _HEADERS_DATACENTER),
        _fetch(url, _HEADERS_MOBILE_NG),
    )

    score = 0.0

    # ── Signal 1: Different HTTP status codes ─────────────────────────────────
    if dc_status != mob_status and dc_status != 0 and mob_status != 0:
        score += 0.4
        evidence.append(
            f"Status divergence: datacenter received HTTP {dc_status}, "
            f"mobile received HTTP {mob_status}"
        )

    # ── Signal 2: Large content length divergence (> 40% difference) ─────────
    if dc_body and mob_body:
        len_ratio = abs(len(dc_body) - len(mob_body)) / max(len(dc_body), len(mob_body))
        if len_ratio > 0.40:
            score += 0.30
            evidence.append(
                f"Content size divergence: {abs(len(dc_body) - len(mob_body))} chars "
                f"({round(len_ratio * 100)}% difference between scanner and mobile view)"
            )

    # ── Signal 3: Credential markers only in mobile/user-facing response ──────
    dc_markers   = _count_markers(dc_body)
    mob_markers  = _count_markers(mob_body)

    if mob_markers > dc_markers + 2:
        score += 0.40
        evidence.append(
            f"Phishing markers visible only to real users (mobile: {mob_markers}, "
            f"scanner: {dc_markers} markers). Likely cloaking."
        )
    elif mob_markers > dc_markers:
        score += 0.15
        evidence.append(
            f"Slightly more phishing-related content in user-facing view "
            f"(mobile: {mob_markers} vs scanner: {dc_markers} markers)"
        )

    # ── Signal 4: Scanner gets redirect, mobile gets full page ────────────────
    if dc_status in (301, 302, 307, 308) and mob_status == 200:
        score += 0.50
        evidence.append(
            "Scanner was redirected away from the page while mobile browser "
            "received the full page — classic cloaking pattern."
        )

    score = min(1.0, round(score, 2))
    is_suspicious = score >= 0.40

    return {
        "cloaking_score": score,
        "is_suspicious": is_suspicious,
        "evidence": evidence,
        "datacenter_status": dc_status,
        "mobile_status": mob_status,
    }
