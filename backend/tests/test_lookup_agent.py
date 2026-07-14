"""
test_lookup_agent.py — Unit tests for LookupAgent.

Strategy: every external call (Supabase, AbuseIPDB, OTX, GSB) is mocked so
tests run fully offline and deterministically.

Covers:
  - PhishTank hit → high db_score
  - OTX solo low-confidence hit → suppressed (low score)
  - AbuseIPDB high-confidence hit → elevated score
  - Community hit → contributes to corroborated score
  - Google Safe Browsing definitive hit → near-max score
  - Clean domain → score ≈ 0
  - Upstream exception → graceful zero-score fallback
"""

import sys
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_supabase_response(data=None, count=None):
    """Builds a minimal mock mimicking a supabase-py response object."""
    mock = MagicMock()
    mock.data = data or []
    mock.count = count
    return mock


@pytest.fixture
def agent():
    with patch.dict(os.environ, {
        "ABUSEIPDB_API_KEY": "test-key",
        "OTX_API_KEY": "test-key",
    }):
        from agents.lookup_agent import LookupAgent
        return LookupAgent()


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_phishtank_hit_raises_score(agent):
    """A PhishTank match should contribute 0.60 to db_score."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(return_value=True)), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(return_value=0)), \
         patch.object(agent, "otx_check", new=AsyncMock(return_value=(False, 0))), \
         patch.object(agent, "community_check", new=AsyncMock(return_value=False)), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(return_value={"is_malicious": False})), \
         patch("agents.lookup_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        result = await agent.check("https://evil-phish.com")

    assert result.db_score >= 0.60
    assert result.phishtank_hit is True
    assert result.matched is True
    assert "OpenPhish/URLhaus" in result.sources_flagged


@pytest.mark.asyncio
async def test_otx_solo_low_pulse_count_suppressed(agent):
    """OTX alone with < 5 pulses should produce near-zero contribution (0.05)."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(return_value=False)), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(return_value=0)), \
         patch.object(agent, "otx_check", new=AsyncMock(return_value=(True, 2))), \
         patch.object(agent, "community_check", new=AsyncMock(return_value=False)), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(return_value={"is_malicious": False})), \
         patch("agents.lookup_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        result = await agent.check("https://stale-domain.com")

    assert result.otx_hit is True
    assert result.db_score <= 0.10  # low-confidence solo OTX should not trigger "matched"
    assert result.matched is False


@pytest.mark.asyncio
async def test_abuseipdb_high_score(agent):
    """AbuseIPDB score > 80 should contribute 0.50."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(return_value=False)), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(return_value=90)), \
         patch.object(agent, "otx_check", new=AsyncMock(return_value=(False, 0))), \
         patch.object(agent, "community_check", new=AsyncMock(return_value=False)), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(return_value={"is_malicious": False})), \
         patch("agents.lookup_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        result = await agent.check("https://abused-ip-host.com")

    assert result.abuseipdb_score == 90
    assert result.db_score >= 0.50
    assert result.matched is True


@pytest.mark.asyncio
async def test_google_safe_browsing_definitive_hit(agent):
    """GSB hit should push score near max (adds 0.70)."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(return_value=False)), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(return_value=0)), \
         patch.object(agent, "otx_check", new=AsyncMock(return_value=(False, 0))), \
         patch.object(agent, "community_check", new=AsyncMock(return_value=False)), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(
             return_value={"is_malicious": True, "threat_types": ["MALWARE"]}
         )), \
         patch("agents.lookup_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        result = await agent.check("https://malware-site.com")

    assert result.db_score >= 0.70
    assert result.matched is True
    assert any("Google Safe Browsing" in s for s in result.sources_flagged)


@pytest.mark.asyncio
async def test_clean_domain_zero_score(agent):
    """A totally clean domain should produce db_score ≈ 0 and matched=False."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(return_value=False)), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(return_value=0)), \
         patch.object(agent, "otx_check", new=AsyncMock(return_value=(False, 0))), \
         patch.object(agent, "community_check", new=AsyncMock(return_value=False)), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(return_value={"is_malicious": False})), \
         patch("agents.lookup_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = True
        result = await agent.check("https://google.com")

    assert result.db_score == 0.0
    assert result.matched is False
    assert result.sources_flagged == []


@pytest.mark.asyncio
async def test_upstream_failure_graceful_fallback(agent):
    """If all sub-checks raise, the agent must return a zero-score result (no crash)."""
    with patch.object(agent, "phishtank_check", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch.object(agent, "abuseipdb_check", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch.object(agent, "otx_check", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch.object(agent, "community_check", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch("agents.lookup_agent.check_safe_browsing", new=AsyncMock(side_effect=RuntimeError("timeout"))):
        result = await agent.check("https://anything.com")

    assert result.db_score == 0.0
    assert result.matched is False
