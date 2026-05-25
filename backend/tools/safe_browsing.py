"""
safe_browsing.py — Google Safe Browsing API v4 Client

Sends a URL to the Google Safe Browsing API to check it against Google's
constantly updated threat database. Covers malware, phishing, unwanted
software, and potentially harmful applications.

Requirements:
  - Set GOOGLE_SAFE_BROWSING_API_KEY in your .env file
  - Free tier: 10,000 requests/day (no billing required)
  - Get a key: https://console.cloud.google.com → Enable "Safe Browsing API"
"""

import os
import httpx
from typing import Optional

_API_BASE = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

_THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",        # Phishing
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]

_PLATFORM_TYPES = ["ANY_PLATFORM"]
_ENTRY_TYPES = ["URL"]


async def check_safe_browsing(url: str) -> dict:
    """
    Checks a URL against the Google Safe Browsing API.

    Returns:
        {
            "is_malicious": bool,
            "threat_types": list[str],   # e.g. ["SOCIAL_ENGINEERING"]
            "platform_types": list[str],
        }
    """
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    if not api_key:
        # No key configured — skip silently
        return {"is_malicious": False, "threat_types": [], "platform_types": []}

    payload = {
        "client": {
            "clientId": "gaudon-threat-engine",
            "clientVersion": "2.0"
        },
        "threatInfo": {
            "threatTypes": _THREAT_TYPES,
            "platformTypes": _PLATFORM_TYPES,
            "threatEntryTypes": _ENTRY_TYPES,
            "threatEntries": [{"url": url}]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{_API_BASE}?key={api_key}",
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

            matches = data.get("matches", [])
            if not matches:
                return {"is_malicious": False, "threat_types": [], "platform_types": []}

            threat_types = list({m.get("threatType", "") for m in matches})
            platform_types = list({m.get("platformType", "") for m in matches})

            return {
                "is_malicious": True,
                "threat_types": threat_types,
                "platform_types": platform_types,
            }

    except httpx.TimeoutException:
        print(f"[SafeBrowsing] Timeout checking {url}")
        return {"is_malicious": False, "threat_types": [], "platform_types": []}
    except Exception as e:
        print(f"[SafeBrowsing] Error: {e}")
        return {"is_malicious": False, "threat_types": [], "platform_types": []}
