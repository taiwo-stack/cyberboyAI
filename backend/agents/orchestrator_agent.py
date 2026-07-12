import time
import re
import asyncio
from typing import Optional, List, Dict

from schemas.agent_inputs import AnalyzeRequest
from schemas.agent_outputs import (
    VerdictResponse, BrandAgentResult, LookupAgentResult, 
    MLAgentResult, OpenAIAgentResult, BehavioralAgentResult, AgentTrace,
    EmailAgentResult
)
from agents.brand_agent import BrandAgent
from agents.lookup_agent import LookupAgent
from agents.ml_agent import MLAgent
from agents.openai_agent import OpenAIAgent
from agents.behavioral_agent import BehavioralAgent
from agents.email_agent import EmailAgent
from agents.verdict import compute_verdict
from tools.supabase_client import supabase
from tools.async_db import db

class OrchestratorAgent:
    def __init__(self):
        """Initializes all sub-agents and loads models."""
        self.brand = BrandAgent()
        self.lookup = LookupAgent()
        self.ml = MLAgent()       
        self.openai = OpenAIAgent()
        self.behavioral = BehavioralAgent()
        self.email = EmailAgent()

    def _detect_input_type(self, input_str: str) -> str:
        """Categorizes the raw input string."""
        input_str = input_str.strip().lower()
        
        if input_str.startswith("http://") or input_str.startswith("https://"):
            return "url"
            
        # IPv4 regex match
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", input_str):
            return "ip"
            
        # Email match
        if "@" in input_str and "." in input_str and " " not in input_str:
            return "email"
            
        # Domain-like pattern (has . and no spaces)
        if "." in input_str and " " not in input_str:
            return "url"
            
        return "message"

    def _normalize_url(self, input_str: str) -> str:
        """Ensures a URL string has an http/https prefix for processing."""
        input_str = input_str.strip()
        if not input_str.startswith("http://") and not input_str.startswith("https://"):
            return f"https://{input_str}"
        return input_str

    async def _store_submission(self, input_str: str, response: VerdictResponse) -> None:
        """
        Asynchronously records the threat submission and verdict in Supabase.
        Uses async_db so the fire-and-forget task doesn't block the event loop.
        """
        try:
            data = {
                "raw_input": input_str,
                "input_type": "url",
                "verdict": response.verdict,
                "final_score": response.score,
                "red_flags": response.red_flags,
                "explanation": response.explanation,
                "advice": response.advice,
                "agent_trace": [t.model_dump() for t in response.agent_trace],
                "brand_score": response.brand_result.similarity_score if response.brand_result else 0.0,
                "db_score": response.lookup_result.db_score if response.lookup_result else 0.0,
                "ml_score": response.ml_result.ml_score if response.ml_result else 0.0,
                # "email_score": response.email_result.email_score if response.email_result else 0.0,
                "claude_score": response.openai_result.openai_score if response.openai_result else 0.0,
                "source": "api",
                "reviewed": False,
                # "threat_type": response.threat_type  <-- REMOVED UNTIL COLUMN IS ADDED TO SUPABASE
            }
            await db(lambda: supabase.table("threat_submissions").insert(data).execute())
        except Exception as e:
            print(f"Error storing submission to Supabase: {e}")

    async def _analyze_single_url(
        self,
        target_url: str,
        email_result: Optional[EmailAgentResult],
        sms_urgent: bool,
        sms_msg: str,
        start_time: float
    ) -> VerdictResponse:
        """
        Runs the full analysis pipeline for a single target URL.
        """
        try:
            # 2. Normalize
            target_url = self._normalize_url(target_url)

            # 2b. URL UNSHORTENING ────────────────────────────────────────────────
            # Follows redirect chains (bit.ly, tinyurl, t.co etc.) before analysis.
            from tools.url_unshortener import unshorten, _is_shortener
            from urllib.parse import urlparse as _urlparse
            _is_short = _is_shortener(target_url)
            if _is_short:
                resolved_url, _redirect_chain = await unshorten(target_url)
                if resolved_url != target_url:
                    print(f"[Orchestrator] Unshortened {target_url} → {resolved_url} ({len(_redirect_chain)} hops)")
                    target_url = resolved_url

            # 3. Domain Logic
            import tldextract as _tld
            _ext = _tld.extract(target_url)
            _domain = f"{_ext.domain}.{_ext.suffix}".lower() if _ext.suffix else _ext.domain.lower()
            _path = _urlparse(target_url).path.strip("/")
            _path_depth = len([s for s in _path.split("/") if s])

            from tools.trusted_domains import trusted_domain_manager
            # Never blindly trust a link shortener domain
            _is_trusted = trusted_domain_manager.is_trusted(_domain) and not _is_short
            
            if _is_trusted:
                if _path_depth <= 1:
                    _skip_tier2 = True
                    _is_bare_trusted = True
                else:
                    _skip_tier2 = False
                    _is_bare_trusted = False
                _skip_brand = True
            else:
                _skip_tier2 = False
                _is_bare_trusted = False
                _skip_brand = False

            # 4. Database Cache Fast-Path (per URL)
            from datetime import datetime, timedelta, timezone
            try:
                recent_res = await db(lambda: supabase.table("threat_submissions")
                    .select("verdict, final_score, red_flags, explanation, advice, submitted_at, agent_trace")
                    .eq("raw_input", target_url)
                    .order("submitted_at", desc=True)
                    .limit(1)
                    .execute())
                
                if recent_res.data:
                    last_sub = recent_res.data[0]
                    last_time = datetime.fromisoformat(last_sub["submitted_at"])
                    if datetime.now(timezone.utc) - last_time < timedelta(hours=24) and last_sub["verdict"] != "PENDING_REVIEW":
                        stored_trace = last_sub.get("agent_trace", [])
                        reconstructed_trace = [AgentTrace(**t) for t in stored_trace] if stored_trace else []

                        return VerdictResponse(
                            verdict=last_sub["verdict"],
                            score=last_sub["final_score"],
                            red_flags=last_sub["red_flags"],
                            explanation=last_sub["explanation"] + " (Retrieved from recent database scan)",
                            advice=last_sub["advice"],
                            threat_type=last_sub.get("threat_type", "benign" if last_sub["verdict"] == "SAFE" else "phishing"),
                            agents_used=["database_cache"],
                            agent_trace=reconstructed_trace,
                            brand_result=None, lookup_result=None, ml_result=None, openai_result=None,
                            processing_ms=int((time.time() - start_time) * 1000)
                        )
            except Exception as e:
                print(f"[Orchestrator] Cache check failed (SSL/Network) for {target_url}: {e}. Skipping cache.")

            # 5. Run Tier 1 Agents in Parallel
            from schemas.agent_outputs import BrandAgentResult

            async def _time(aw):
                t0 = time.time()
                res = await aw
                if res:
                    res.execution_ms = int((time.time() - t0) * 1000)
                return res

            if _skip_brand:
                # Always run behavioral analysis to capture SSL and redirects, 
                # but pass is_trusted so behavioral agent skips the heavy Playwright scan
                lookup_r, ml_r, behavior_r = await asyncio.gather(
                    _time(self.lookup.check(target_url)),
                    _time(self.ml.check(target_url)),
                    _time(self.behavioral.analyze(target_url, is_trusted=_is_trusted))
                )
                
                brand_r = BrandAgentResult(
                    is_impersonation=False, similarity_score=0.0,
                    closest_brand=_domain, legitimate_domain=_domain, 
                    red_flag=None, finding=f"Verified Official Domain: '{_domain}'", execution_ms=0
                )
            else:
                brand_r, lookup_r, ml_r, behavior_r = await asyncio.gather(
                    _time(self.brand.check(target_url)),
                    _time(self.lookup.check(target_url)),
                    _time(self.ml.check(target_url)),
                    _time(self.behavioral.analyze(target_url, is_trusted=_is_trusted))
                )

            # 5. Conditionally Run Tier 2 Agent (OpenAI)
            openai_r = None
            already_dangerous = (
                (lookup_r.matched and lookup_r.db_score >= 0.95) or
                (brand_r.is_impersonation and brand_r.similarity_score >= 0.90) or
                _skip_tier2
            )

            if not already_dangerous:
                openai_task = _time(self.openai.analyze(
                    url=target_url,
                    ml_score=ml_r.ml_score,
                    brand_result=brand_r,
                    force=True,
                    scraped_data=behavior_r.model_dump()
                ))
                
                from tools.cloaking_detector import detect_cloaking
                cloak_task = detect_cloaking(target_url, is_trusted=_is_trusted)
                openai_r, cloak_result = await asyncio.gather(openai_task, cloak_task)
            else:
                cloak_result = {"cloaking_score": 0.0, "is_suspicious": False, "evidence": []}

            # 6. Final Verdict
            response = await compute_verdict(
                brand=brand_r,
                lookup=lookup_r,
                ml=ml_r,
                openai=openai_r,
                behavior=behavior_r,
                email=email_result,
                start_time=start_time,
                sms_urgent=sms_urgent,
                sms_msg=sms_msg,
                is_trusted_domain=_is_trusted
            )

            # 6b. Apply Cloaking Escalation
            if cloak_result.get("is_suspicious") and response.verdict != "DANGEROUS":
                cloak_boost = cloak_result["cloaking_score"] * 0.25
                new_score = min(1.0, round(response.score + cloak_boost, 2))
                cloak_flags = [f"[CLOAKING DETECTED] {e}" for e in cloak_result.get("evidence", [])]
                
                new_verdict = response.verdict
                if new_score >= 0.75: new_verdict = "DANGEROUS"
                elif new_score >= 0.45: new_verdict = "SUSPICIOUS"

                new_threat_type = response.threat_type
                if new_verdict != "SAFE" and new_threat_type == "benign":
                    new_threat_type = "phishing"

                response = response.model_copy(update={
                    "score": new_score,
                    "verdict": new_verdict,
                    "threat_type": new_threat_type,
                    "red_flags": response.red_flags + cloak_flags,
                })

            # Store to Database (Fire-and-forget)
            asyncio.create_task(self._store_submission(target_url, response))
            return response

        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            print(f"\n[Orchestrator] URL ANALYSIS ERROR for {target_url}:\n{error_msg}")
            
            return VerdictResponse(
                verdict="SUSPICIOUS",
                score=0.5,
                red_flags=[f"URL Scan Error: {str(e)}"],
                explanation=f"Encountered an error while scanning {target_url}.",
                advice="Standard caution advised.",
                threat_type="phishing",
                agents_used=["error_handler"],
                agent_trace=[],
                brand_result=None, lookup_result=None, ml_result=None, openai_result=None,
                processing_ms=int((time.time() - start_time) * 1000)
            )

    async def analyze(self, request: AnalyzeRequest) -> VerdictResponse:
        """
        The main conduit for the pipeline. Parses input, runs respective agents, checks thresholds,
        calls the verdict engine, and logs to Supabase asynchronously.
        """
        start_time = time.time()
        
        # 0. Handle OCR from Image if provided
        if request.image_base64:
            from tools.vision_tools import extract_text_from_image
            print("[Orchestrator] Image detected. Running OCR via VisionTool...")
            extracted_text = await extract_text_from_image(request.image_base64)
            if extracted_text:
                print(f"[Orchestrator] OCR Result: {extracted_text}")
                # Combine the extracted text with any text the user typed
                request.input = f"{extracted_text}\n\n{request.input}".strip()
            else:
                print("[Orchestrator] VisionTool failed to extract text.")
        
        try:
            # 1. Detect Input Type
            input_type = self._detect_input_type(request.input)
            
            # Global Database Cache check on raw input
            from datetime import datetime, timedelta, timezone
            try:
                recent_res = await db(lambda: supabase.table("threat_submissions")
                    .select("verdict, final_score, red_flags, explanation, advice, submitted_at, agent_trace")
                    .eq("raw_input", request.input)
                    .order("submitted_at", desc=True)
                    .limit(1)
                    .execute())
                
                if recent_res.data:
                    last_sub = recent_res.data[0]
                    last_time = datetime.fromisoformat(last_sub["submitted_at"])
                    if datetime.now(timezone.utc) - last_time < timedelta(hours=24) and last_sub["verdict"] != "PENDING_REVIEW":
                        stored_trace = last_sub.get("agent_trace", [])
                        reconstructed_trace = [AgentTrace(**t) for t in stored_trace] if stored_trace else []

                        return VerdictResponse(
                            verdict=last_sub["verdict"],
                            score=last_sub["final_score"],
                            red_flags=last_sub["red_flags"],
                            explanation=last_sub["explanation"] + " (Retrieved from recent database scan)",
                            advice=last_sub["advice"],
                            threat_type=last_sub.get("threat_type", "benign" if last_sub["verdict"] == "SAFE" else "phishing"),
                            agents_used=["database_cache"],
                            agent_trace=reconstructed_trace,
                            brand_result=None, lookup_result=None, ml_result=None, openai_result=None,
                            processing_ms=int((time.time() - start_time) * 1000)
                        )
            except Exception as e:
                print(f"[Orchestrator] Global cache check failed: {e}. Skipping cache.")

            # 2. Extract links and classify text
            extracted_urls = []
            sms_urgent = False
            sms_msg = ""
            email_result = None

            if input_type in ["message", "email"]:
                from tools.sms_tools import extract_urls_from_message, analyze_sms_urgency, openai_extract_urls
                extracted_urls = extract_urls_from_message(request.input)
                
                # Always run email classifier on raw text input
                email_result = await self.email.check(request.input)

                # Fallback to LLM extraction if regex found nothing
                if not extracted_urls:
                    print("[Orchestrator] Regex found no URL — trying OpenAI URL extractor...")
                    extracted_urls = await openai_extract_urls(request.input)
                    if extracted_urls:
                        print(f"[Orchestrator] OpenAI extracted URLs: {extracted_urls}")

                sms_urgent, sms_msg = await analyze_sms_urgency(request.input)
            else:
                # Direct URL/IP input
                extracted_urls = [request.input]

            # 3. If NO URLs were found in the content
            if not extracted_urls:
                email_score = email_result.email_score if email_result else 0.0

                if email_score >= 0.75 or (sms_urgent and email_score >= 0.5):
                    verdict = "DANGEROUS"
                    explanation = (
                        f"No hyperlinks were found, but the message content is highly suspicious. "
                        f"{email_result.finding if email_result else ''} {sms_msg if sms_urgent else ''}"
                    ).strip()
                    advice = "Do not share personal details or respond to the sender. If it claims to be your bank, call them through their official number."
                    score = email_score
                    threat_type = "phishing"

                elif email_score >= 0.40 or sms_urgent:
                    verdict = "SUSPICIOUS"
                    explanation = (
                        f"No hyperlinks were found, but certain patterns in the message warrant caution. "
                        f"{email_result.finding if email_result else ''} {sms_msg if sms_urgent else ''}"
                    ).strip()
                    advice = "Treat this message with caution. Verify the sender through an independent channel before acting."
                    score = max(email_score, 0.40 if sms_urgent else 0.0)
                    threat_type = "phishing"

                else:
                    verdict = "SAFE"
                    explanation = (
                        f"No hyperlinks were found and the message content shows no signs of "
                        f"social engineering or phishing. {email_result.finding if email_result else ''}"
                    ).strip()
                    advice = "Content appears benign. Continue to verify unexpected requests through official channels."
                    score = email_score
                    threat_type = "benign"

                agent_trace = []
                if email_result and email_result.execution_ms > 0:
                    agent_trace.append(AgentTrace(
                        agent="email",
                        score=email_result.email_score,
                        finding=email_result.finding,
                        duration_ms=email_result.execution_ms
                    ))

                response = VerdictResponse(
                    verdict=verdict,
                    score=score,
                    red_flags=[sms_msg] if sms_urgent else [],
                    explanation=explanation,
                    advice=advice,
                    threat_type=threat_type,
                    agents_used=["sms_extractor", "email"],
                    agent_trace=agent_trace,
                    brand_result=None, lookup_result=None, ml_result=None,
                    openai_result=None, behavior_result=None,
                    email_result=email_result,
                    processing_ms=int((time.time() - start_time) * 1000)
                )
                asyncio.create_task(self._store_submission(request.input, response))
                return response

            # 4. We have URLs! Normalize and deduplicate them first to avoid duplicate scans
            normalized_urls = []
            seen_normalized = set()
            for url in extracted_urls:
                norm = self._normalize_url(url).strip().lower()
                norm_clean = norm.rstrip("/")
                if norm_clean not in seen_normalized:
                    seen_normalized.add(norm_clean)
                    normalized_urls.append(url)

            target_urls = normalized_urls[:5]
            
            tasks = [
                self._analyze_single_url(url, email_result, sms_urgent, sms_msg, start_time)
                for url in target_urls
            ]
            url_responses = await asyncio.gather(*tasks)

            # 5. Aggregate multiple URL results
            # Rank: DANGEROUS > SUSPICIOUS > SAFE
            def verdict_rank(v):
                if v == "DANGEROUS": return 3
                if v == "SUSPICIOUS": return 2
                return 1
                
            sorted_responses = sorted(
                url_responses,
                key=lambda r: (verdict_rank(r.verdict), r.score),
                reverse=True
            )
            
            worst_response = sorted_responses[0]
            
            # Combine red flags, traces, and agents used
            all_red_flags = []
            all_traces = []
            all_agents_used = set()
            seen_traces = set()
            
            for resp in url_responses:
                for flag in resp.red_flags:
                    if flag not in all_red_flags:
                        all_red_flags.append(flag)
                for t in resp.agent_trace:
                    trace_key = (t.agent, t.score, t.finding)
                    if trace_key not in seen_traces:
                        seen_traces.add(trace_key)
                        all_traces.append(t)
                all_agents_used.update(resp.agents_used)
                
            # If multiple URLs were scanned, append summary list to the explanation
            if len(target_urls) > 1:
                verdicts_summary = ", ".join(
                    f"'{resp.brand_result.closest_brand if (resp.brand_result and resp.brand_result.closest_brand) else resp.agent_trace[0].finding.split(':')[0] if (resp.agent_trace) else 'URL'}' ({resp.verdict})"
                    for resp in url_responses
                )
                explanation_prefix = f"Scanned {len(target_urls)} URLs found in content. Verdicts: {verdicts_summary}. "
                aggregated_explanation = explanation_prefix + worst_response.explanation
            else:
                aggregated_explanation = worst_response.explanation

            final_response = VerdictResponse(
                verdict=worst_response.verdict,
                score=worst_response.score,
                red_flags=all_red_flags,
                explanation=aggregated_explanation,
                advice=worst_response.advice,
                threat_type=worst_response.threat_type,
                identified_brand=worst_response.identified_brand,
                agents_used=list(all_agents_used),
                agent_trace=all_traces,
                brand_result=worst_response.brand_result,
                lookup_result=worst_response.lookup_result,
                ml_result=worst_response.ml_result,
                openai_result=worst_response.openai_result,
                behavior_result=worst_response.behavior_result,
                email_result=email_result or worst_response.email_result,
                processing_ms=int((time.time() - start_time) * 1000)
            )

            # Store the aggregated verdict for this raw input in the database
            asyncio.create_task(self._store_submission(request.input, final_response))
            return final_response

        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            print(f"\n[Orchestrator] CRITICAL ANALYSIS ERROR:\n{error_msg}")
            
            return VerdictResponse(
                verdict="SUSPICIOUS",
                score=0.5,
                red_flags=[f"System Engine Error: {str(e)}"],
                explanation="The GaudOn engine encountered a technical error during analysis.",
                advice="Standard caution advised. Re-scan the link in a few minutes.",
                threat_type="phishing",
                agents_used=["error_handler"],
                agent_trace=[],
                brand_result=None, lookup_result=None, ml_result=None, openai_result=None,
                processing_ms=int((time.time() - start_time) * 1000)
            )
