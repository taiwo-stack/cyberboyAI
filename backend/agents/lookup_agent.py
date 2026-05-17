import os
import asyncio
import socket
import httpx
import tldextract
from urllib.parse import urlparse
from typing import Optional, List, Tuple
from tools.supabase_client import supabase
from tools.async_db import db
from tools import cache
from tools.safe_browsing import check_safe_browsing
from schemas.agent_outputs import LookupAgentResult

class LookupAgent:
    def __init__(self):
        self.abuseipdb_key = os.getenv("ABUSEIPDB_API_KEY")
        self.otx_key = os.getenv("OTX_API_KEY")

    async def phishtank_check(self, url: str) -> bool:
        """Checks if URL exists in the local PhishTank/OpenPhish/URLhaus cache."""
        try:
            response = await db(lambda: supabase.table("phishtank_cache").select("id").eq("url", url).execute())
            return len(response.data) > 0
        except Exception:
            return False

    async def abuseipdb_check(self, url: str) -> int:
        """Checks IP reputation via AbuseIPDB."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return 0
            
            # Resolve IP (blocking call wrapped in executor)
            loop = asyncio.get_event_loop()
            try:
                ip = await loop.run_in_executor(None, socket.gethostbyname, hostname)
            except Exception:
                return 0

            # Check Cache
            cache_key = f"abuseipdb:{ip}"
            cached_score = await cache.get(cache_key)
            if cached_score is not None:
                return cached_score

            # API Call
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {
                    "Key": self.abuseipdb_key,
                    "Accept": "application/json"
                }
                params = {"ipAddress": ip, "maxAgeInDays": 90}
                response = await client.get("https://api.abuseipdb.com/api/v2/check", headers=headers, params=params)
                
                if response.status_code == 200:
                    score = response.json()["data"]["abuseConfidenceScore"]
                    await cache.set(cache_key, score, ttl_seconds=86400) # 24h
                    return score
            return 0
        except Exception:
            return 0

    async def otx_check(self, url: str) -> tuple[bool, int]:
        """
        Checks URL reputation via AlienVault OTX.
        Returns (hit: bool, pulse_count: int).
        pulse_count is used for corroboration weighting — a lone pulse from 3 years
        ago is far less trustworthy than 25 recent pulses from active threat hunters.
        """
        try:
            if not self.otx_key:
                return False, 0

            cache_key = f"otx:{url}"
            cached_res = await cache.get(cache_key)
            if cached_res is not None:
                return cached_res

            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"X-OTX-API-KEY": self.otx_key}
                api_url = f"https://otx.alienvault.com/api/v1/indicators/url/{url}/general"
                response = await client.get(api_url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    pulse_count = data.get("pulse_info", {}).get("count", 0)
                    hit = pulse_count > 0
                    result = (hit, pulse_count)
                    await cache.set(cache_key, result, ttl_seconds=21600)  # 6h
                    return result
            return False, 0
        except Exception:
            return False, 0

    async def community_check(self, url: str) -> bool:
        """Checks if domain is in the confirmed community threats table."""
        try:
            ext = tldextract.extract(url)
            domain = ext.registered_domain
            response = await db(lambda: supabase.table("community_threats").select("id")
                .eq("indicator", domain)
                .eq("confirmed", True).execute())
            return len(response.data) > 0
        except Exception:
            return False

    async def check(self, url: str) -> LookupAgentResult:
        """Runs all lookups in parallel and computes a corroboration-gated db_score."""
        try:
            # Run all 5 lookups in parallel (Google Safe Browsing added)
            phishtank_hit, abuse_score, otx_result, community_hit, gsb_result = await asyncio.gather(
                self.phishtank_check(url),
                self.abuseipdb_check(url),
                self.otx_check(url),
                self.community_check(url),
                check_safe_browsing(url)
            )

            otx_hit, otx_pulse_count = otx_result
            gsb_hit = gsb_result.get("is_malicious", False)
            gsb_threats = gsb_result.get("threat_types", [])

            # ── Multi-Feed Corroboration Gate ─────────────────────────────────
            # OTX alone (especially with low pulse_count) is an unreliable signal.
            # Historical community reports for repurposed domains (e.g. x.com, google.com
            # subdomains) result in stale OTX hits that generate false positives.
            # We require corroboration from at least one other independent feed for
            # OTX to contribute meaningfully to the final db_score.
            #
            # Corroboration sources (independent of OTX):
            confirmed_sources = sum([
                bool(phishtank_hit),
                abuse_score > 50,
                bool(community_hit),
            ])

            otx_solo   = otx_hit and confirmed_sources == 0
            otx_weight = (
                0.05 if otx_solo and otx_pulse_count < 5 else   # Stale/low-confidence OTX
                0.15 if otx_solo else                            # OTX only, but notable pulse count
                0.30                                             # OTX + corroborating evidence
            )

            # ── db_score Formula ──────────────────────────────────────────────
            db_score = 0.0
            sources_flagged = []

            if phishtank_hit:
                db_score += 0.60
                sources_flagged.append("PhishTank/URLhaus")

            if otx_hit:
                db_score += otx_weight
                sources_flagged.append(
                    f"AlienVault OTX ({otx_pulse_count} pulses)"
                    + (" [solo signal — low confidence]" if otx_solo else "")
                )

            if community_hit:
                db_score += 0.40
                sources_flagged.append("Community Threats")

            if abuse_score > 80:
                db_score += 0.50
                sources_flagged.append(f"AbuseIPDB ({abuse_score}%)")
            elif abuse_score > 50:
                db_score += 0.30
                sources_flagged.append(f"AbuseIPDB ({abuse_score}%)")

            if gsb_hit:
                # Google Safe Browsing is highly authoritative — near-definitive signal
                threat_label = ", ".join(gsb_threats) if gsb_threats else "THREAT"
                db_score += 0.70
                sources_flagged.append(f"Google Safe Browsing ({threat_label})")

            db_score = min(1.0, db_score)

            # Generate in-depth forensic finding string
            if db_score > 0.1:
                finding = f"Flagged by {len(sources_flagged)} security feeds: {', '.join(sources_flagged)}."
            else:
                # Descriptive "Clean" finding for deeper visibility
                finding = (
                    "Global Reputation Check: "
                    f"Google Safe Browsing (CLEAN) | "
                    f"PhishTank/OpenPhish (NOT FOUND) | "
                    f"AbuseIPDB Confidence ({abuse_score}%) | "
                    f"OTX Pulses ({otx_pulse_count}) | "
                    f"Community (UNREPORTED)."
                )

            return LookupAgentResult(
                db_score=round(db_score, 2),
                matched=(db_score > 0.10),   # Exclude lone stale OTX hits from "matched"
                sources_flagged=sources_flagged,
                phishtank_hit=phishtank_hit,
                abuseipdb_score=abuse_score,
                otx_hit=otx_hit,
                community_hit=community_hit,
                finding=finding
            )

        except Exception:
            return LookupAgentResult(
                db_score=0.0, matched=False, sources_flagged=[],
                phishtank_hit=False, abuseipdb_score=0, otx_hit=False, community_hit=False
            )
