"""
ProxyRotationManager
====================
Manages a pool of residential proxy credentials and rotates them per request
to defeat ASN-based cloaking detection by phishing kits.

Supported providers (via SOCKS5/HTTP proxy format):
  - Bright Data (formerly Luminati)
  - Oxylabs
  - Smartproxy
  - Any provider supporting username:password@host:port format

Configuration (add to .env):
  PROXY_PROVIDER=brightdata        # or: oxylabs, smartproxy, custom
  PROXY_HOST=brd.superproxy.io     # Your provider's gateway host
  PROXY_PORT=22225                 # Your provider's gateway port
  PROXY_USERNAME=your_username     # Your proxy account username
  PROXY_PASSWORD=your_password     # Your proxy account password
  PROXY_COUNTRY=ng                 # Target country (ng = Nigeria)
  PROXY_ENABLED=true               # Set to false to disable proxy entirely

For Bright Data specifically, the session ID encodes geo-targeting:
  Username format: user-CUSTOMER_ID-country-ng-session-RANDOM_SESSION

Usage:
  from tools.proxy_manager import proxy_manager
  proxy_url = proxy_manager.get_proxy()   # Returns None if not configured
  # Then pass to httpx.AsyncClient(proxies=proxy_url) or Playwright context
"""

import os
import random
import string
from typing import Optional


def _random_session() -> str:
    """Generate a random 8-char session ID for sticky session support."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


class ProxyRotationManager:
    """
    Wraps residential proxy configuration and provides rotating proxy URLs
    compatible with both httpx and Playwright.
    """

    def __init__(self):
        self._enabled   = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        self._provider  = os.getenv("PROXY_PROVIDER", "custom")
        self._host      = os.getenv("PROXY_HOST", "")
        self._port      = os.getenv("PROXY_PORT", "")
        self._username  = os.getenv("PROXY_USERNAME", "")
        self._password  = os.getenv("PROXY_PASSWORD", "")
        self._country   = os.getenv("PROXY_COUNTRY", "ng")  # Nigeria by default

        if self._enabled and not all([self._host, self._port, self._username, self._password]):
            print(
                "[ProxyRotationManager] WARNING: PROXY_ENABLED=true but credentials "
                "are incomplete. Proxy will not be used. Check your .env file."
            )
            self._enabled = False

        if self._enabled:
            print(
                f"[ProxyRotationManager] Residential proxy active via "
                f"{self._provider} ({self._host}:{self._port}, country={self._country})"
            )

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_proxy(self) -> Optional[str]:
        """
        Returns a fully-formed proxy URL with a fresh rotating session ID,
        or None if proxy is not configured.

        For Bright Data, the session ID is embedded in the username to
        enable sticky sessions (same IP within one analysis run).
        For other providers, the standard username:password format is used.
        """
        if not self._enabled:
            return None

        session = _random_session()

        if self._provider == "brightdata":
            # Bright Data username encodes geo + session
            username = (
                f"{self._username}-country-{self._country}-session-{session}"
            )
        elif self._provider in ("oxylabs", "smartproxy"):
            # Most providers accept country via username suffix
            username = f"{self._username}-cc-{self._country.upper()}"
        else:
            # Generic: just use the configured username as-is
            username = self._username

        return f"http://{username}:{self._password}@{self._host}:{self._port}"

    def get_playwright_proxy(self) -> Optional[dict]:
        """
        Returns a Playwright-compatible proxy dict, or None if not configured.

        Usage:
            proxy_conf = proxy_manager.get_playwright_proxy()
            context = await browser.new_context(proxy=proxy_conf, ...)
        """
        if not self._enabled:
            return None

        session = _random_session()

        if self._provider == "brightdata":
            username = (
                f"{self._username}-country-{self._country}-session-{session}"
            )
        elif self._provider in ("oxylabs", "smartproxy"):
            username = f"{self._username}-cc-{self._country.upper()}"
        else:
            username = self._username

        return {
            "server": f"http://{self._host}:{self._port}",
            "username": username,
            "password": self._password,
        }


# Module-level singleton
proxy_manager = ProxyRotationManager()
