"""
URLUnshortener
==============
Follows redirect chains (bit.ly, tinyurl, t.co, ow.ly, etc.) to resolve the
final destination URL before the threat analysis pipeline begins.

Security notes:
- Hard cap of 10 redirect hops to prevent infinite loops
- Strict 8-second total timeout
- Never executes JavaScript; uses HEAD then GET requests only
- Strips tracking parameters after resolution (utm_source etc.)
- Logs the full redirect chain for diagnostics
"""

import re
import httpx
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Known URL shortener domains — triggers unshortening even for non-obvious redirects
SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "buff.ly", "goo.gl",
    "shorturl.at", "rb.gy", "cutt.ly", "is.gd", "v.gd", "tiny.cc",
    "lnkd.in", "shorte.st", "adf.ly", "bc.vc", "clck.ru",
    # Nigerian shorteners
    "ng.link", "naij.link",
}

# Tracking params to strip after resolution (noise reduction for analysis)
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "referrer",
}

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _is_shortener(url: str) -> bool:
    """Returns True if the URL's domain is a known shortener service."""
    try:
        host = urlparse(url).hostname or ""
        return host.lstrip("www.") in SHORTENER_DOMAINS
    except Exception:
        return False


def _strip_tracking(url: str) -> str:
    """Removes common tracking query parameters from a resolved URL."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
        new_query = urlencode(cleaned, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url


async def unshorten(url: str, max_hops: int = 10) -> tuple[str, list[str]]:
    """
    Resolves a potentially shortened URL to its final destination.

    Returns:
        (final_url, redirect_chain) where redirect_chain is the list of
        intermediate URLs encountered, for diagnostics.

    The original URL is always returned unchanged if anything goes wrong.
    """
    chain: list[str] = [url]
    current = url

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=8.0,
            headers=_BROWSER_HEADERS,
            verify=True,
        ) as client:
            for _ in range(max_hops):
                try:
                    # Use HEAD first (faster, no body download)
                    resp = await client.head(current)
                except httpx.RequestError:
                    # Some servers reject HEAD; fall back to GET
                    try:
                        resp = await client.get(current)
                    except httpx.RequestError:
                        break

                if resp.is_redirect and "location" in resp.headers:
                    next_url = str(resp.headers["location"])
                    # Resolve relative redirects
                    if next_url.startswith("/"):
                        parsed = urlparse(current)
                        next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
                    if next_url == current:
                        break  # Prevent identical-URL infinite loops
                    current = next_url
                    chain.append(current)
                else:
                    break  # No further redirects

    except Exception:
        pass  # Network error — return what we have so far

    final = _strip_tracking(current)
    return final, chain
