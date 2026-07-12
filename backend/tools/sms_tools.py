import re
import tldextract
from typing import Optional, Tuple, List

# Phase 1 — Explicit URL pattern: finds anything starting with http/https/www
# Intentionally has NO TLD length restriction — that validation is delegated to tldextract
_EXPLICIT_URL_RE = re.compile(
    r'(?:https?://|www\.)[^\s<>"\']+',
    re.IGNORECASE
)

# Phase 2 — Bare domain pattern: catches domains without http/www prefix
# e.g. "visit paypa1-secure.com/verify to proceed"
_BARE_DOMAIN_RE = re.compile(
    r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'  # domain label
    r'(?:\.[a-zA-Z0-9\-]+)+'                                # .tld (any length, any count)
    r'(?:/[^\s<>"\']*)?'                                    # optional path
    r'\b',
    re.IGNORECASE
)


def _is_real_domain(candidate: str) -> bool:
    """
    Delegates TLD validation to tldextract — the authoritative source for
    valid public suffixes. No hardcoded length limits or TLD whitelists.
    """
    try:
        candidate = candidate.rstrip(".,;:!?)'\"")
        ext = tldextract.extract(candidate)
        return bool(ext.domain and ext.suffix)
    except Exception:
        return False


# Dynamic urgency detection is now handled by OpenAI.
def extract_url_from_message(message: str) -> Optional[str]:
    """
    Extracts the first valid URL found in a raw text message.

    Two-phase dynamic approach:
      Phase 1 — Catch explicit http/https/www patterns (no TLD length restriction)
      Phase 2 — Catch bare domains without protocol prefix
      Validation — tldextract confirms each candidate is a real registered domain

    This is fully future-proof: new ICANN TLDs are supported automatically
    without any code changes.
    """
    # Phase 1: Explicit protocol/www prefix — highest confidence, check first
    for match in _EXPLICIT_URL_RE.finditer(message):
        candidate = match.group(0).rstrip(".,;:!?)'\"")
        if _is_real_domain(candidate):
            return candidate

    # Phase 2: Bare domain patterns — lower confidence, validate strictly
    for match in _BARE_DOMAIN_RE.finditer(message):
        candidate = match.group(0).rstrip(".,;:!?)'\"")
        if len(candidate) < 6:
            continue
        if _is_real_domain(candidate):
            return candidate

    return None


def extract_urls_from_message(message: str) -> List[str]:
    """
    Extracts all unique valid URLs found in a raw text message.
    Preserves the order of their appearance.
    """
    urls = []
    # Phase 1: Explicit protocol/www prefix
    for match in _EXPLICIT_URL_RE.finditer(message):
        candidate = match.group(0).rstrip(".,;:!?)'\"")
        if _is_real_domain(candidate):
            urls.append(candidate)

    # Phase 2: Bare domain patterns
    for match in _BARE_DOMAIN_RE.finditer(message):
        candidate = match.group(0).rstrip(".,;:!?)'\"")
        if len(candidate) < 6:
            continue
        # Avoid matching a bare domain that is already captured inside a Phase 1 URL (e.g. google.com inside http://google.com)
        if any(candidate in existing for existing in urls):
            continue
        if _is_real_domain(candidate):
            urls.append(candidate)

    # Return unique urls preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        u_lower = u.lower()
        if u_lower not in seen:
            seen.add(u_lower)
            unique_urls.append(u)
    return unique_urls


async def openai_extract_url(message: str) -> Optional[str]:
    """
    Fallback URL extractor powered by OpenAI.

    Called ONLY when the regex+tldextract approach finds nothing.
    Handles cases regex cannot catch:
      - Defanged URLs:  hxxp://paypal[.]com  or  paypal(.)com
      - Spelled-out:    "visit apple dash id dot support slash unlock"
      - Obfuscated:     URLs with zero-width spaces or Unicode lookalikes
      - Split across lines or with inserted spaces

    Returns the reconstructed, normalized URL string or None.
    """
    import os
    import json
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=100,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a URL extraction assistant. "
                        "Extract ANY URL or web address from the message below, including: "
                        "defanged URLs (hxxp, [.], (dot)), spelled-out domains, obfuscated links. "
                        "Reconstruct the actual URL in proper format (https://domain.tld/path). "
                        "Respond ONLY with a JSON object: {\"url\": \"<extracted url or null>\"}. "
                        "If no URL exists, return {\"url\": null}."
                    )
                },
                {"role": "user", "content": f"Message: {message}"}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        extracted = data.get("url")
        if extracted and _is_real_domain(extracted):
            return extracted
    except Exception:
        pass

    return None


async def openai_extract_urls(message: str) -> List[str]:
    """
    Fallback URL list extractor powered by OpenAI.
    Called when regex+tldextract finds nothing, or to detect highly obfuscated URLs.
    """
    import os
    import json
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a URL extraction assistant. "
                        "Extract ALL URLs or web addresses from the message below, including: "
                        "defanged URLs (hxxp, [.], (dot)), spelled-out domains, obfuscated links. "
                        "Reconstruct each actual URL in proper format (https://domain.tld/path). "
                        "Respond ONLY with a JSON object containing a list of URLs: {\"urls\": [\"<extracted url 1>\", \"<extracted url 2>\", ...]}. "
                        "If no URLs exist, return {\"urls\": []}."
                    )
                },
                {"role": "user", "content": f"Message: {message}"}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        extracted = data.get("urls", [])
        
        validated = []
        for url in extracted:
            if url and _is_real_domain(url):
                validated.append(url)
        return validated
    except Exception:
        pass

    return []



async def analyze_sms_urgency(message: str) -> Tuple[bool, str]:
    """
    Checks if the SMS text contains social engineering urgency tactics dynamically via AI.
    Returns (is_urgent, red_flag_message).
    """
    import os
    import json
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False, ""

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=100,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze the provided text message for social engineering manipulation tactics. "
                        "Does it use psychological urgency, fear, account suspension threats, or fake prize rewards? "
                        "Respond ONLY with JSON: {\"is_urgent\": <bool>, \"reason\": \"<string explaining the tactic, max 10 words>\"}."
                    )
                },
                {"role": "user", "content": f"Message: {message}"}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        is_urgent = bool(data.get("is_urgent", False))
        reason = data.get("reason", "Suspicious psychological tactics detected.")
        if is_urgent:
            return True, f"AI detected social engineering: {reason}"
    except Exception:
        pass

    return False, ""
