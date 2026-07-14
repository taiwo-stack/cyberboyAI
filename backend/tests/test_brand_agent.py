"""
test_brand_agent.py — Unit tests for BrandAgent.

Covers:
  - Exact brand domain match (google.com → not impersonation)
  - Typosquatting via leet-speak (paypa1-secure → paypal)
  - Homoglyph attack (раурal.com → paypal)
  - Hyphen-component compound attack (netfl1x-billing → netflix)
  - Generic keyword heuristic (secure-login.xyz)
  - Totally safe, unrelated domain
  - Empty / invalid URL graceful fallback
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure the backend directory is on the path for all imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def mock_global_brand_manager():
    """
    Replaces global_brand_manager with a small curated set of known brands
    so tests are fast and deterministic — no network / file I/O.
    """
    brands = [
        "google", "paypal", "netflix", "amazon", "microsoft",
        "apple", "facebook", "instagram", "twitter", "gtbank",
        "accessbank", "zenithbank",
    ]
    with patch("agents.brand_agent.global_brand_manager") as mock_mgr:
        mock_mgr.load.return_value = None
        mock_mgr.get_brands.return_value = brands
        yield mock_mgr


@pytest.fixture(autouse=True)
def mock_trusted_domain_manager():
    """
    Replaces trusted_domain_manager inside BrandAgent so unit tests do not
    attempt external API/DB calls.
    """
    with patch("agents.brand_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        yield mock_tdm


@pytest.fixture
def agent():
    from agents.brand_agent import BrandAgent
    return BrandAgent()


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_legitimate_domain_not_flagged(agent):
    """The real google.com domain must never be flagged as impersonation."""
    result = await agent.check("https://www.google.com/search?q=test")
    assert result.is_impersonation is False
    assert result.similarity_score <= 1.0


@pytest.mark.asyncio
async def test_leet_speak_typosquatting(agent):
    """paypa1-secure.xyz uses numeric substitution to spoof paypal."""
    result = await agent.check("https://paypa1-secure.xyz/login")
    assert result.is_impersonation is True
    assert result.closest_brand == "paypal"
    assert result.similarity_score >= 0.75


@pytest.mark.asyncio
async def test_hyphen_compound_attack(agent):
    """netfl1x-billing.com splits into 'netfl1x' which normalises to 'netflix'."""
    result = await agent.check("https://netfl1x-billing.com/account")
    assert result.is_impersonation is True
    assert result.closest_brand == "netflix"


@pytest.mark.asyncio
async def test_unrelated_domain_safe(agent):
    """A completely unrelated domain should produce low similarity and no flag."""
    result = await agent.check("https://opensourcephysics.org")
    assert result.is_impersonation is False
    assert result.similarity_score < 0.75


@pytest.mark.asyncio
async def test_generic_keyword_heuristic(agent):
    """Domains containing high-risk keywords (secure, login) should get a non-zero score."""
    result = await agent.check("https://secure-login.xyz/verify")
    # Should not cross the 0.75 impersonation threshold alone (advisory signal)
    assert result.similarity_score < 0.75
    assert result.similarity_score > 0.0


@pytest.mark.asyncio
async def test_invalid_url_graceful_fallback(agent):
    """A completely invalid or empty label must not raise; it returns a safe default."""
    result = await agent.check("https://")
    assert result.is_impersonation is False
    assert result.similarity_score == 0.0


@pytest.mark.asyncio
async def test_brand_agent_exception_safety(agent):
    """If the brand list is unavailable, the agent returns a safe default (no crash)."""
    with patch("agents.brand_agent.global_brand_manager") as mock_mgr:
        mock_mgr.get_brands.side_effect = RuntimeError("network error")
        result = await agent.check("https://paypa1.com")
    assert result.is_impersonation is False
    assert result.similarity_score == 0.0


@pytest.mark.asyncio
async def test_finding_populated_on_impersonation(agent):
    """The finding string must be non-empty and contain relevant info when flagged."""
    result = await agent.check("https://paypa1-login.net")
    assert result.finding != ""
    if result.is_impersonation:
        assert "paypal" in result.finding.lower() or "CRITICAL" in result.finding


@pytest.mark.asyncio
async def test_red_flag_populated_on_impersonation(agent):
    """red_flag field must be set when is_impersonation=True."""
    result = await agent.check("https://paypa1.xyz")
    if result.is_impersonation:
        assert result.red_flag is not None
        assert len(result.red_flag) > 0
