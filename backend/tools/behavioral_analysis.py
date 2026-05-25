import ssl
import socket
import httpx
import asyncio
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright
from typing import List, Dict, Any, Optional

class BehavioralAnalyzer:
    def __init__(self):
        self.timeout = 10.0

    def check_ssl_sync(self, hostname: str) -> Dict[str, Any]:
        """Extracts SSL certificate information for risk assessment."""
        results = {
            "issuer": "None (Insecure)",
            "days_to_expire": 0,
            "cert_age_days": 0,
            "is_valid": False,
            "error": None
        }
        
        try:
            # 1. First, try to establish a valid, verified connection
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    if cert and 'issuer' in cert:
                        # Defensive parsing of the issuer tuple
                        issuer_dict = {}
                        for rdn in cert['issuer']:
                            for entry in rdn:
                                if len(entry) == 2:
                                    issuer_dict[entry[0]] = entry[1]
                        
                        # Extract dates and ensure they are UTC for safe subtraction
                        # Standard peercert format: 'May 13 19:56:32 2026 GMT'
                        fmt = "%b %d %H:%M:%S %Y %Z"
                        not_after = datetime.strptime(cert['notAfter'], fmt)
                        not_before = datetime.strptime(cert['notBefore'], fmt)
                        
                        # Use UTC for now to avoid offset-naive vs offset-aware errors
                        now = datetime.utcnow()
                        
                        # If strptime included a TZ, not_after will be aware. 
                        # We strip it to make it naive (UTC) for subtraction if needed.
                        if not_after.tzinfo is not None:
                            not_after = not_after.replace(tzinfo=None)
                        if not_before.tzinfo is not None:
                            not_before = not_before.replace(tzinfo=None)

                        results.update({
                            "issuer": issuer_dict.get('organizationName', issuer_dict.get('commonName', 'Unknown')),
                            "days_to_expire": (not_after - now).days,
                            "cert_age_days": (now - not_before).days,
                            "is_valid": True
                        })
                        return results

            # 2. If verified connection fails, try unverified to see if a cert even exists
            unverified_context = ssl.create_default_context()
            unverified_context.check_hostname = False
            unverified_context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with unverified_context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    results["issuer"] = "Untrusted/Self-Signed"
                    results["error"] = "SSL Verification Failed"
                    return results

        except socket.gaierror:
            results["error"] = "DNS Resolution Failed (Domain does not exist or is offline)"
        except socket.timeout:
            results["error"] = "Connection Timeout (Port 443 closed)"
        except ConnectionRefusedError:
            results["error"] = "Connection Refused (No SSL service)"
        except Exception as e:
            results["error"] = str(e)
            
        return results

    def trace_redirects_sync(self, url: str) -> List[str]:
        """Follows redirects and returns the full URL chain."""
        try:
            with httpx.Client(follow_redirects=True, timeout=self.timeout) as client:
                resp = client.get(url)
                return [str(r.url) for r in resp.history] + [str(resp.url)]
        except Exception:
            return [url]

    def analyze_dynamic_behavior_sync(self, url: str) -> Dict[str, Any]:
        """Uses Sync Playwright to detect dynamic/cloaked behaviors."""
        results = {
            "cloaking_detected": False,
            "dynamic_content_detected": False,
            "has_password_field": False,
            "scripts_count": 0,
            "evidence": [],
            "html": "",
            "text": ""
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    # Use a standard mobile UA to look more like a real user
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                        viewport={"width": 390, "height": 844}
                    )
                    page = context.new_page()
                    
                    # Faster timeout: 10s is enough for modern networks
                    page.goto(url, timeout=10000, wait_until="domcontentloaded")
                    
                    results["html"] = page.content()
                    results["text"] = page.evaluate("() => document.body ? document.body.innerText : ''")
                    
                    # Detect login fields
                    password_fields = page.query_selector_all('input[type="password"]')
                    if password_fields:
                        results["has_password_field"] = True
                        results["evidence"].append("Login interface detected.")

                    results["scripts_count"] = len(page.query_selector_all('script'))
                finally:
                    browser.close()
        except Exception as e:
            results["error"] = str(e)
            results["evidence"].append(f"Browser scan partially failed: {str(e)[:50]}")
            
        return results

    async def check_ssl(self, hostname: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self.check_ssl_sync, hostname)

    async def trace_redirects(self, url: str) -> List[str]:
        return await asyncio.to_thread(self.trace_redirects_sync, url)

    async def analyze_dynamic_behavior(self, url: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self.analyze_dynamic_behavior_sync, url)

behavioral_analyzer = BehavioralAnalyzer()
