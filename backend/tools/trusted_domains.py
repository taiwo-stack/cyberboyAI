"""
TrustedDomainManager
====================
Singleton that loads the global trusted domain whitelist from Supabase
(`trusted_domains` table) and keeps it in memory. Refreshed every 12 hours
or on demand.

Table schema (run once in Supabase SQL editor):
-----------------------------------------------
create table trusted_domains (
    id          bigint generated always as identity primary key,
    domain      text not null unique,          -- e.g. "google.com"
    label       text,                           -- e.g. "Google Search"
    added_by    text default 'system',
    created_at  timestamptz default now()
);

Row-Level Security: allow SELECT for the service role key only.
"""

import asyncio
import logging
import time
from typing import Set
from tools.supabase_client import supabase
from tools.async_db import db

logger = logging.getLogger("gaudon.trusted_domains")


# ---------------------------------------------------------------------------
# Default seed list — loaded into Supabase the very first time.
# Add/remove rows in Supabase; no code changes required after that.
# ---------------------------------------------------------------------------
_SEED_DOMAINS = [
    ("x.com",           "Twitter / X"),
    ("twitter.com",     "Twitter"),
    ("google.com",      "Google"),
    ("youtube.com",     "YouTube"),
    ("facebook.com",    "Facebook"),
    ("instagram.com",   "Instagram"),
    ("linkedin.com",    "LinkedIn"),
    ("microsoft.com",   "Microsoft"),
    ("apple.com",       "Apple"),
    ("amazon.com",      "Amazon"),
    ("github.com",      "GitHub"),
    ("wikipedia.org",   "Wikipedia"),
    ("reddit.com",      "Reddit"),
    ("netflix.com",     "Netflix"),
    ("whatsapp.com",    "WhatsApp"),
    ("tiktok.com",      "TikTok"),
    ("telegram.org",    "Telegram"),
    ("zoom.us",         "Zoom"),
    ("dropbox.com",     "Dropbox"),
    ("cloudflare.com",  "Cloudflare"),
    ("stripe.com",      "Stripe"),
    ("paypal.com",      "PayPal"),
    ("binance.com",     "Binance"),
    ("coinbase.com",    "Coinbase"),
    # Developer & Data Science platforms
    ("kaggle.com",      "Kaggle"),
    ("huggingface.co",  "HuggingFace"),
    # Nigerian / African platforms
    ("opay.io",         "OPay"),
    ("paystack.com",    "Paystack"),
    ("flutterwave.com", "Flutterwave"),
    ("kuda.com",       "Kuda Bank"),
    ("piggyvest.com",  "PiggyVest"),
    ("cowrywise.com",  "Cowrywise"),
    # URL Shorteners (Legitimate infrastructure)
    ("bit.ly",          "Bitly"),
    ("t.co",            "X/Twitter Shortener"),
    ("tinyurl.com",     "TinyURL"),
    ("ow.ly",           "Hootsuite Shortener"),
    ("rebrandly.com",   "Rebrandly"),
    ("cutt.ly",         "Cuttly"),
]


class TrustedDomainManager:
    """
    Singleton-style in-memory cache for the trusted_domains Supabase table.
    Re-fetches every 12 hours automatically.
    """

    _REFRESH_INTERVAL = 12 * 3600   # 12 hours in seconds

    def __init__(self):
        self._domains: Set[str] = set()
        self._last_loaded: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    async def load(self, force: bool = False) -> None:
        """Load or refresh from Supabase. Call once during app startup."""
        # Proactively ensure new seeds are in the database
        await self._seed()

        if not force and (time.time() - self._last_loaded) < self._REFRESH_INTERVAL:
            return

        try:
            res = await db(lambda: supabase.table("trusted_domains").select("domain").execute())
            if res.data:
                self._domains = {row["domain"].lower() for row in res.data}
                self._last_loaded = time.time()
                logger.info("[TrustedDomains] Loaded %d trusted domains from Supabase.", len(self._domains))
        except Exception as exc:
            logger.warning("[TrustedDomains] Could not load from Supabase: %s. Using local fallback.", exc)
            self._domains = {d for d, _ in _SEED_DOMAINS}

    def is_trusted(self, domain: str) -> bool:
        """Returns True if the registered domain is in the whitelist."""
        return domain.lower() in self._domains

    async def add(self, domain: str, label: str = "", added_by: str = "admin") -> bool:
        """Add a new trusted domain to Supabase and refresh the in-memory set."""
        try:
            await db(lambda: supabase.table("trusted_domains").upsert(
                {"domain": domain.lower(), "label": label, "added_by": added_by},
                on_conflict="domain"
            ).execute())
            self._domains.add(domain.lower())
            return True
        except Exception as exc:
            logger.exception("[TrustedDomains] Failed to add domain '%s'", domain)
            return False

    async def remove(self, domain: str) -> bool:
        """Remove a domain from the whitelist."""
        try:
            await db(lambda: supabase.table("trusted_domains").delete().eq("domain", domain.lower()).execute())
            self._domains.discard(domain.lower())
            return True
        except Exception as exc:
            logger.exception("[TrustedDomains] Failed to remove domain '%s'", domain)
            return False

    @property
    def domains(self) -> Set[str]:
        return frozenset(self._domains)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _seed(self) -> None:
        """Upsert the built-in default list into the Supabase table."""
        rows = [{"domain": d, "label": l, "added_by": "system"} for d, l in _SEED_DOMAINS]
        try:
            # Using upsert ensures we don't create duplicates but DO add new seeds
            await db(lambda: supabase.table("trusted_domains").upsert(rows, on_conflict="domain").execute())
            logger.info("[TrustedDomains] Synced %d global seeds to Supabase.", len(rows))
        except Exception as exc:
            logger.warning("[TrustedDomains] Seed sync failed: %s. Using local fallback.", exc)
            self._domains = {d for d, _ in _SEED_DOMAINS}


# Module-level singleton — import and use this everywhere
trusted_domain_manager = TrustedDomainManager()
