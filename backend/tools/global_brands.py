"""
global_brands.py — Tranco Top 500 Global Brand Loader

Downloads the globally recognized top 500 website domain labels from the
Tranco list and provides them to the BrandAgent for global brand impersonation
detection. Falls back to a hardcoded emergency list if the download fails.

Refresh cycle: every 24 hours automatically.
"""

import io
import time
import zipfile
import threading
import tldextract
import httpx

# Hardcoded emergency fallback — 60 most-impersonated global brands
_EMERGENCY_FALLBACK = [
    "google", "youtube", "facebook", "twitter", "instagram", "linkedin",
    "apple", "microsoft", "amazon", "netflix", "paypal", "ebay",
    "yahoo", "reddit", "whatsapp", "tiktok", "snapchat", "pinterest",
    "dropbox", "spotify", "adobe", "github", "stackoverflow", "twitch",
    "chase", "bankofamerica", "wellsfargo", "citibank", "hsbc", "barclays",
    "santander", "lloyds", "natwest", "halifax", "monzo", "revolut",
    "stripe", "shopify", "squarespace", "wordpress", "godaddy", "cloudflare",
    "zoom", "slack", "notion", "figma", "canva", "salesforce",
    "dhl", "fedex", "ups", "usps", "royalmail", "emirates",
    "gtbank", "gtb", "accessbank", "zenithbank", "zenith", "uba", "firstbank", "opay", "palmpay", "kuda",
]

_TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"
_TOP_N = 500
_REFRESH_INTERVAL = 86400  # 24 hours in seconds

class GlobalBrandManager:
    def __init__(self):
        self._brands: list[str] = list(_EMERGENCY_FALLBACK)
        self._last_loaded: float = 0.0
        self._lock = threading.Lock()
        self._loaded_ok = False

    def _download_and_parse(self) -> list[str]:
        """Downloads Tranco Top 1M zip and extracts the top N unique domain labels."""
        try:
            resp = httpx.get(_TRANCO_URL, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
                with zf.open(csv_name) as f:
                    lines = f.read().decode("utf-8", errors="ignore").splitlines()

            labels = set(_EMERGENCY_FALLBACK)  # Start with fallback brands
            for line in lines[:_TOP_N * 3]:  # over-fetch to get TOP_N unique labels
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    domain = parts[1].strip().lower()
                    ext = tldextract.extract(domain)
                    if ext.domain:
                        labels.add(ext.domain)
                if len(labels) >= _TOP_N:
                    break

            return list(labels) if labels else list(_EMERGENCY_FALLBACK)
        except Exception as e:
            print(f"[GlobalBrands] Failed to download Tranco list: {e}. Using fallback.")
            return list(_EMERGENCY_FALLBACK)

    def load(self) -> None:
        """Loads (or refreshes) the global brand list. Thread-safe."""
        with self._lock:
            now = time.time()
            if now - self._last_loaded < _REFRESH_INTERVAL and self._loaded_ok:
                return  # Still fresh

            print("[GlobalBrands] Loading Tranco Top 500 global domain labels...")
            brands = self._download_and_parse()
            # Ensure essential delivery brands are always present even if Tranco list omits them
            _CRITICAL_BRANDS = [
                "dhl", "fedex", "ups", "usps", "royalmail", "emirates",
                "gtbank", "gtb", "accessbank", "zenithbank", "zenith", "uba", "firstbank", "opay", "palmpay", "kuda",
            ]
            # Merge while preserving uniqueness (case‑insensitive)
            existing = set(b.lower() for b in brands)
            for b in _CRITICAL_BRANDS:
                if b.lower() not in existing:
                    brands.append(b)
            self._brands = brands
            self._last_loaded = now
            self._loaded_ok = True
            print(f"[GlobalBrands] Loaded {len(brands)} global brand labels (incl. critical delivery/finance).")

    def get_brands(self) -> list[str]:
        """Returns the current list of global brand labels."""
        # Auto-refresh if stale
        if time.time() - self._last_loaded > _REFRESH_INTERVAL:
            threading.Thread(target=self.load, daemon=True).start()
        return self._brands


# Module-level singleton — imported by BrandAgent
global_brand_manager = GlobalBrandManager()
