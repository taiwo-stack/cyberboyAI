import os
import json
import uuid
import random
import time
import asyncio
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI
from playwright.sync_api import sync_playwright
from schemas.agent_outputs import OpenAIAgentResult

load_dotenv()

# Real Chrome user-agent strings
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

class OpenAIAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def _fetch_page_sync(self, url: str) -> dict:
        """Launches Sync Playwright headless browser."""
        from tools.proxy_manager import proxy_manager
        fallback = {"title": "", "text": "", "forms": 0, "meta_desc": "", "status": 0, "html": ""}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context_kwargs = {
                        "user_agent": random.choice(_USER_AGENTS),
                        "java_script_enabled": False,
                    }
                    
                    proxy_conf = proxy_manager.get_playwright_proxy()
                    if proxy_conf:
                        context_kwargs["proxy"] = proxy_conf

                    context = browser.new_context(**context_kwargs)
                    page = context.new_page()

                    try:
                        response = page.goto(url, timeout=15000, wait_until="domcontentloaded")
                        status = response.status if response else 200
                    except Exception as e:
                        print(f"Playwright navigation error for {url}: {e}")
                        status = 0
                    
                    title = ""
                    try: title = page.title()
                    except: pass
                        
                    html_content = ""
                    try: html_content = page.content()
                    except: pass
                        
                    text = ""
                    try: 
                        text = page.evaluate("() => document.body.innerText")
                        text = text[:2500] if text else ""
                    except: pass
                        
                    forms = 0
                    try:
                        forms = page.locator("input[type=password]").count()
                    except: pass
                        
                    meta_desc = ""
                    try:
                        meta_loc = page.locator("meta[name=description]")
                        if meta_loc.count() > 0:
                            meta_desc = meta_loc.first.get_attribute("content") or ""
                    except: pass

                finally:
                    browser.close()
                    
                return {
                    "title": title,
                    "text": text,
                    "html": html_content,
                    "forms": forms,
                    "meta_desc": meta_desc,
                    "status": status
                }
        except Exception as e:
            print(f"Playwright general error: {e}")
            return fallback

    async def _fetch_page(self, url: str) -> dict:
        return await asyncio.to_thread(self._fetch_page_sync, url)

    async def analyze(self, url: str, ml_score: float, brand_result=None, force: bool = False, scraped_data: dict = None) -> OpenAIAgentResult:
        start_time = time.time()
        
        is_offline = False
        if scraped_data:
            dyn_findings = scraped_data.get("dynamic_findings", {})
            evidence_str = " ".join(dyn_findings.get("evidence", [])).lower()
            if "dns resolution failed" in evidence_str or "dns resolution failed" in scraped_data.get("finding", "").lower():
                is_offline = True
        
        # 1. Fetch page (or reuse scraped data from Behavioral Agent)
        if is_offline:
            page_data = {
                "title": "",
                "text": "",
                "html": "",
                "forms": 0,
                "status": 0
            }
        elif scraped_data and scraped_data.get("html"):
            page_data = {
                "title": brand_result.closest_brand if brand_result else "", 
                "text": scraped_data.get("text", ""),
                "html": scraped_data.get("html", ""),
                "forms": scraped_data.get("dynamic_findings", {}).get("has_password_field", 0),
                "status": 200
            }
            print(f"[OpenAIAgent] Reusing DOM data from pipeline (Fast-Path active)")
        else:
            page_data = await self._fetch_page(url)
        
        status = page_data.get("status", 200)

        # 1a. Deterministic Checks
        if is_offline or status == 0:
            finding = "Host Unreachable. DNS resolution failed or the domain is offline."
            return OpenAIAgentResult(
                openai_score=0.75, confidence=100,
                red_flags=["Host Unreachable: DNS resolution failed or the server is offline."],
                explanation="The domain could not be resolved or is currently offline.",
                advice="The link appears to be inactive or decommissioned. However, the sender should still be treated as suspicious.",
                threat_type="phishing",
                finding=finding, execution_ms=int((time.time() - start_time) * 1000)
            )

        if status in [404, 403, 410]:
            finding = f"Host Unreachable (HTTP {status}). DNS resolution failed or service unavailable."
            return OpenAIAgentResult(
                openai_score=0.75, confidence=100,
                red_flags=[f"Host Unreachable: Server returned HTTP {status}."],
                explanation=f"The server is currently unreachable or returned an HTTP {status} error.",
                advice="The destination is offline. This is likely a decommissioned threat.",
                threat_type="phishing",
                finding=finding, execution_ms=int((time.time() - start_time) * 1000)
            )

        from tools.rules_engine import rules_engine
        is_kit, kit_name, _ = rules_engine.scan_for_phishing_kits(page_data.get("html", ""))
        if is_kit:
            finding = f"Heuristic signature match: {kit_name} Phishing Framework."
            return OpenAIAgentResult(
                openai_score=0.98, confidence=100,
                red_flags=[f"DOM Signature Match: {kit_name}"],
                explanation=f"Detected signatures belonging to a known phishing kit ({kit_name}).",
                advice="CRITICAL: Sophisticated phishing framework detected. Close immediately.",
                threat_type="phishing",
                finding=finding, execution_ms=int((time.time() - start_time) * 1000)
            )

        if rules_engine.scan_for_suspension(page_data.get("text", "")):
            finding = "Verified Host-Level Suspension (TOS Violation)."
            return OpenAIAgentResult(
                openai_score=0.75, confidence=100,
                red_flags=["Platform Takedown: Page deactivated for TOS violation."],
                explanation="The hosting platform has suspended this page.",
                advice="The link is dead, but the sender is a confirmed scammer.",
                threat_type="phishing",
                finding=finding, execution_ms=int((time.time() - start_time) * 1000)
            )

        # 2. Build Context
        boundary = f"BOUNDARY_{uuid.uuid4().hex.upper()}"
        brand_ctx = "None detected"
        if brand_result and brand_result.closest_brand:
            sim = round(getattr(brand_result, 'similarity_score', 0) * 100, 1)
            brand_ctx = f"{brand_result.closest_brand} (Similarity: {sim}%)"
        
        sanitized_text = (page_data.get('text') or "").replace("<<<", "").replace(">>>", "")
        context = f"""URL: {url}
Site Status: {status}
Title: {page_data['title']}
Meta: {page_data['meta_desc']}
Forms (password inputs): {page_data['forms']}
Domain Brand Match Hint: {brand_ctx}

{boundary}_START
{sanitized_text}
{boundary}_END
"""
        # NOTE: ml_score is intentionally excluded from the prompt so GPT derives its own
        # independent judgment from page content and URL structure alone. This prevents
        # the AI from anchoring on or echoing the ML score.

        # 3. Call AI
        system_prompt = (
            "You are a global cybersecurity forensic analyst. Your job is to perform a comprehensive multi-vector threat analysis of the page content and URL provided.\n\n"
            "MULTI-VECTOR THREAT DETECTION — Analyze ALL of the following, not just brand impersonation:\n"
            "1. CREDENTIAL HARVESTING: Are there login forms, password fields, OTP/PIN prompts, or requests for banking credentials? Even without a brand logo, a credential form on a suspicious domain is a major threat signal.\n"
            "2. SOCIAL ENGINEERING LANGUAGE: Is there urgency ('Your account will be suspended'), threats ('Act now or lose access'), authority impersonation ('HMRC', 'FBI', 'Microsoft Support'), or fear tactics?\n"
            "3. CONTENT-CONTEXT MISMATCH: Does the page content contradict what the URL structure suggests? (e.g., URL looks like a tracking link but page asks for credit card details)\n"
            "4. SUSPICIOUS DOWNLOADS / INSTALLS: Are there prompts to download files (.exe, .apk, .dmg), install browser extensions, or run scripts?\n"
            "5. OBFUSCATION SIGNALS: Heavy JavaScript dependency with no readable content, encoded strings, minimal visible text, or pages that load differently without JS?\n"
            "6. DECEPTIVE UX PATTERNS: Fake countdown timers, misleading 'click here' overlays, hidden form fields, invisible iframes, CAPTCHA abuse, or fake progress indicators?\n"
            "7. BRAND IMPERSONATION: Does the page display logos, trademarks, or content belonging to a known brand while served from a non-official domain?\n\n"
            "List ALL signals found across these 7 categories in the 'red_flags' array. Do not limit red_flags to brand signals only.\n\n"
            "SCORING RULE (CRITICAL):\n"
            "You MUST derive 'openai_score' entirely from the page content and URL structure you are given.\n"
            "DO NOT echo or anchor on any externally provided score. Evaluate independently:\n"
            "  - Legitimate service with no threat signals → score 0.0–0.15\n"
            "  - One minor structural concern, no content threats → score 0.15–0.35\n"
            "  - Multiple structural anomalies OR ambiguous content → score 0.35–0.55\n"
            "  - Credential forms, social engineering language, OR brand mimicry → score 0.65–0.85\n"
            "  - Multiple active threat vectors simultaneously → score 0.85–1.0\n\n"
            "ZERO-DAY BRAND DETECTION RULE:\n"
            "1. If the host is UNREACHABLE (Status 0 / DNS Resolution Failure), YOU MUST NOT identify a brand unless the domain is a near-identical character match for a major global entity.\n"
            "2. DO NOT use similarity or 'feel' to identify brands for unreachable sites. If in doubt, set identified_brand to null.\n"
            "3. For reachable sites, extract the 'identified_brand' only if it is explicitly stated in the page content or logos.\n"
            "4. NEVER guess generic brands like 'walmart' or 'amazon' from ambiguous strings if the site is unreachable.\n\n"
            "EXPLANATION GUIDELINE:\n"
            "The 'explanation' field must be a comprehensive forensic summary covering: URL structural analysis, page content review, form presence, social engineering signals, brand signals, and JavaScript dependency. Do NOT just describe what you did not find — describe what you observed across all vectors.\n\n"
            "Respond ONLY with valid JSON:\n"
            "{\n"
            "  \"openai_score\": float (0.0-1.0, YOUR OWN independent assessment),\n"
            "  \"threat_type\": string ('benign', 'phishing', 'malware', 'defacement'),\n"
            "  \"identified_brand\": string or null,\n"
            "  \"official_domain\": string or null,\n"
            "  \"confidence\": int (0-100),\n"
            "  \"red_flags\": string[] (one entry per distinct threat signal found across ALL 7 categories above),\n"
            "  \"explanation\": string,\n"
            "  \"advice\": string\n"
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            brand_info = data.get("identified_brand")
            off_domain = data.get("official_domain") or ""

            # ── Impersonation guard ──────────────────────────────────────────────
            # GPT returns the brand it sees.  We only say "impersonation" if
            # the *official* domain label (e.g. "paypal") differs from the
            # *submitted* domain label (e.g. "paypal-login").  If GPT recognised
            # the site's own legitimate brand, that is confirmation, not attack.
            import tldextract as _tlde
            submitted_label = _tlde.extract(url).domain.lower()
            official_label  = _tlde.extract(off_domain).domain.lower() if off_domain else ""

            is_impersonating = bool(
                brand_info and official_label and
                official_label != submitted_label
            )

            red_flags_list = data.get("red_flags", [])

            if is_impersonating:
                finding = (
                    f"AI Analysis complete. "
                    f"Identified impersonation of {brand_info} "
                    f"(official domain: {off_domain})."
                )
            elif brand_info:
                finding = (
                    f"AI Analysis complete. "
                    f"Brand confirmed as '{brand_info}'. "
                    f"No impersonation of an external entity detected."
                )
            elif red_flags_list and gpt_score >= 0.35:
                # Surface the primary red flag from GPT's multi-vector analysis
                primary_flag = red_flags_list[0]
                extra = len(red_flags_list) - 1
                if extra > 0:
                    finding = f"AI Analysis complete. {primary_flag} (+{extra} additional signal{'s' if extra > 1 else ''} detected)."
                else:
                    finding = f"AI Analysis complete. {primary_flag}."
            elif gpt_score < 0.20:
                finding = "AI Analysis complete. No threats detected across all 7 threat vectors."
            else:
                finding = f"AI Analysis complete. Ambiguous signals detected (score: {gpt_score*100:.0f}%). Proceed with caution."

            # Use GPT's own score. If GPT omits or returns 0 (which can mean "not sure"),
            # fall back to 0.1 (neutral) — NOT ml_score, to preserve independence.
            raw_score = data.get("openai_score")
            if raw_score is None:
                gpt_score = 0.1
            else:
                gpt_score = float(raw_score)

            return OpenAIAgentResult(
                openai_score=gpt_score,
                confidence=int(data.get("confidence", 0)),
                red_flags=data.get("red_flags", []),
                explanation=data.get("explanation", "No explanation."),
                advice=data.get("advice", "Be cautious."),
                threat_type=data.get("threat_type", "benign"),
                identified_brand=brand_info,
                official_domain=off_domain,
                finding=finding,
                execution_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            return OpenAIAgentResult(
                openai_score=ml_score, confidence=0, red_flags=[],
                explanation=f"AI analysis error: {str(e)}",
                advice="Standard caution advised.",
                threat_type="benign",
                finding="AI Analysis failed (Internal Error)."
            )
