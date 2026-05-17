import tldextract
from datetime import datetime, timezone
from tools.supabase_client import supabase
from tools.async_db import db


class CommunityAgent:
    """
    Background agent that reviews user submissions and aggregates them into the 'community_threats'
    table to make the system smarter over time.
    All Supabase calls use async_db so they don't block the event loop.
    """

    async def get_pending_reports(self) -> list[dict]:
        """
        Retrieves recent unreviewed submissions marked as DANGEROUS or SUSPICIOUS.
        """
        try:
            res = await db(lambda: supabase.table("threat_submissions")
                .select("*")
                .eq("reviewed", False)
                .in_("verdict", ["DANGEROUS", "SUSPICIOUS"])
                .order("submitted_at", desc=True)
                .limit(50)
                .execute())
            return res.data
        except Exception as e:
            print(f"Error fetching pending reports: {e}")
            return []

    async def confirm_threat(self, submission_id: str, confirmed: bool, notes: str = "") -> dict:
        """
        Confirms a threat submission. If confirmed=True, the domain is extracted
        and recorded in the 'community_threats' blocklist.
        """
        try:
            # 1. Fetch submission
            res = await db(lambda: supabase.table("threat_submissions")
                .select("*").eq("id", submission_id).execute())
            if not res.data:
                return {"success": False, "error": "Submission not found"}

            submission = res.data[0]
            raw_input = submission.get("raw_input", "")

            # 2. Mark reviewed=True
            await db(lambda: supabase.table("threat_submissions")
                .update({"reviewed": True})
                .eq("id", submission_id)
                .execute())

            # 3. If confirmed, extract domain and upsert into community_threats
            if confirmed and raw_input:
                ext = tldextract.extract(raw_input)
                domain = f"{ext.domain}.{ext.suffix}".lower()

                if domain and ext.domain:
                    threat_data = {
                        "indicator": domain,
                        "indicator_type": "domain",
                        "confirmed": True,
                        "confirmed_at": datetime.now(timezone.utc).isoformat(),
                        "source": "community",
                        "notes": notes
                    }
                    await db(lambda: supabase.table("community_threats")
                        .upsert(threat_data).execute())

            return {"success": True, "threat_added": confirmed}

        except Exception as e:
            print(f"Error confirming threat {submission_id}: {e}")
            return {"success": False, "error": str(e)}

    async def run_weekly_review(self) -> dict:
        """
        Collects all pending reports and clusters them by domain for batch review.
        """
        try:
            pending = await self.get_pending_reports()

            domains: dict = {}
            for report in pending:
                raw_input = report.get("raw_input", "")
                if raw_input:
                    ext = tldextract.extract(raw_input)
                    domain = f"{ext.domain}.{ext.suffix}".lower()
                    if domain:
                        domains[domain] = domains.get(domain, 0) + 1

            sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
            return {"pending_count": len(pending), "domains": sorted_domains}

        except Exception as e:
            print(f"Error in weekly review: {e}")
            return {"pending_count": 0, "domains": []}
