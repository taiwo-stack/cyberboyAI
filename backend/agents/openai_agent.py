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
Forms: {page_data['forms']}
Brand Match: {brand_ctx}
ML Score: {ml_score}

{boundary}_START
{sanitized_text}
{boundary}_END
"""

        # 3. Call AI
        system_prompt = (
            "You are a global cybersecurity forensic analyst. Analyze the page content and URL for phishing.\n\n"
            "ZERO-DAY BRAND DETECTION RULE:\n"
            "1. If the host is UNREACHABLE (Status 0 / DNS Resolution Failure), YOU MUST NOT identify a brand unless the domain is a near-identical character match for a major global entity.\n"
            "2. DO NOT use similarity or 'feel' to identify brands for unreachable sites. If in doubt, set identified_brand to null.\n"
            "3. For reachable sites, extract the 'identified_brand' only if it is explicitly stated in the page content or logos.\n"
            "4. NEVER guess generic brands like 'walmart' or 'amazon' from ambiguous strings if the site is unreachable.\n\n"
            "Respond ONLY with valid JSON:\n"
            "{\n"
            "  \"openai_score\": float (0.0-1.0),\n"
            "  \"threat_type\": string ('benign', 'phishing', 'malware', 'defacement'),\n"
            "  \"identified_brand\": string or null,\n"
            "  \"official_domain\": string or null,\n"
            "  \"confidence\": int (0-100),\n"
            "  \"red_flags\": string[],\n"
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
            off_domain = data.get("official_domain")
            
            finding = f"AI Analysis complete. {f'Identified impersonation of {brand_info}.' if brand_info else 'No clear brand impersonation found.'}"

            return OpenAIAgentResult(
                openai_score=float(data.get("openai_score", ml_score)),
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
