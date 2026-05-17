import time
from urllib.parse import urlparse
from typing import List
from pydantic import BaseModel
from tools.behavioral_analysis import behavioral_analyzer
from schemas.agent_outputs import BehavioralAgentResult

class BehavioralAgent:
    def __init__(self):
        self.name = "behavioral"

    async def analyze(self, url: str, is_trusted: bool = False) -> BehavioralAgentResult:
        start_time = time.time()
        parsed = urlparse(url)
        hostname = parsed.netloc or parsed.path.split("/")[0] # Fallback for scheme-less URLs
        
        if not hostname:
            return BehavioralAgentResult(
                behavior_score=0.0, red_flags=[], redirect_chain=[],
                ssl_issuer="Unknown", dynamic_findings={}, finding="Behavioral analysis skipped: Invalid URL structure.",
                execution_ms=int((time.time() - start_time) * 1000)
            )
        
        # 1. Check SSL / DNS first to verify domain status
        ssl_info = await behavioral_analyzer.check_ssl(hostname)
        
        is_offline = False
        dns_error = ssl_info.get("error")
        if dns_error and ("DNS Resolution Failed" in dns_error or "socket.gaierror" in dns_error):
            is_offline = True

        redirect_chain = []
        dynamic_info = {
            "cloaking_detected": False,
            "dynamic_content_detected": False,
            "has_password_field": False,
            "scripts_count": 0,
            "evidence": [],
            "html": "",
            "text": "",
            "error": dns_error or "Host unreachable"
        }

        if is_offline:
            redirect_chain = [url]
            dynamic_info["evidence"].append("DNS resolution failed. The domain does not exist or the hosting server is currently offline.")
        else:
            # 2. Trace Redirects (only if online)
            redirect_chain = await behavioral_analyzer.trace_redirects(url)
            
            # 3. Dynamic Analysis (only if online)
            dynamic_info = await behavioral_analyzer.analyze_dynamic_behavior(url)

        # Merge SSL age details into dynamic_info so the frontend DeepEvidence component can render them
        dynamic_info["days_to_expire"] = ssl_info.get("days_to_expire", 0)
        dynamic_info["cert_age_days"] = ssl_info.get("cert_age_days", 0)
        
        # Calculate Risk Score
        risk_score = 0.0
        red_flags = []
        
        if is_offline:
            risk_score += 0.5
            red_flags.append("DNS Resolution Failed: Host is unreachable or offline.")
        else:
            # SSL Risks (Bypass for trusted domains to avoid rotation false positives)
            if ssl_info.get("cert_age_days", 0) < 30 and not is_trusted:
                risk_score += 0.2
                red_flags.append("Domain has a very young SSL certificate (<30 days).")
            if ssl_info.get("issuer") == "Let's Encrypt" and ssl_info.get("cert_age_days", 0) < 7:
                 risk_score += 0.1 # Minor suspicion
                 
            # Redirect Risks
            if len(redirect_chain) > 3:
                risk_score += 0.3
                red_flags.append(f"Excessive redirect chain detected ({len(redirect_chain)} hops).")
                
            # Dynamic Risks
            if dynamic_info.get("cloaking_detected"):
                risk_score += 0.5
                red_flags.append("Behavioral cloaking detected (content varies between browser and crawler).")
            if dynamic_info.get("has_password_field") and "https" not in url.lower():
                risk_score += 0.8
                red_flags.append("DANGEROUS: Credential harvesting form detected over unencrypted connection.")

        # In-depth finding
        if is_offline:
            finding = "DNS Resolution Failed | Host Offline"
        else:
            finding = f"SSL: {ssl_info.get('issuer', 'Unknown')} (Age: {ssl_info.get('cert_age_days', 0)}d) | Hops: {len(redirect_chain)}"
            if dynamic_info.get("cloaking_detected"):
                finding += " | CLOAKING DETECTED"

        return BehavioralAgentResult(
            behavior_score=min(1.0, risk_score),
            red_flags=red_flags,
            redirect_chain=redirect_chain,
            ssl_issuer=ssl_info.get("issuer", "Unknown"),
            dynamic_findings=dynamic_info,
            finding=finding,
            raw_html=dynamic_info.get("html", ""),
            raw_text=dynamic_info.get("text", ""),
            execution_ms=int((time.time() - start_time) * 1000)
        )
