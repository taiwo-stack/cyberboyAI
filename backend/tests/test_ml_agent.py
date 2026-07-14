"""
test_ml_agent.py — Unit tests for MLAgent.

Strategy:
  - joblib.load is mocked so no actual model file is needed.
  - trusted_domain_manager is mocked for whitelist tests.
  - extract_features is mocked for feature-extraction tests.

Covers:
  - Model load failure → graceful 0.50 fallback
  - Whitelisted domain → near-zero score, no inference
  - Feature extraction failure → 0.50 fallback
  - Normal phishing classification path
  - Normal benign classification path
  - High-risk feature detection (IP address, non-standard port, entropy)
"""

import sys
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_mock_model(proba: list[float]):
    """Creates a mock scikit-learn model that returns the given class probabilities."""
    model = MagicMock()
    model.predict_proba.return_value = np.array([proba])
    return model


@pytest.fixture
def agent_with_model():
    """MLAgent with a mocked model that classifies as phishing (benign=0.1)."""
    mock_model = _make_mock_model([0.1, 0.8, 0.05, 0.05])  # phishing dominant
    with patch("agents.ml_agent.joblib.load", return_value=mock_model), \
         patch("agents.ml_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        from agents.ml_agent import MLAgent
        agent = MLAgent()
        agent.model = mock_model
        yield agent, mock_tdm


@pytest.fixture
def agent_benign_model():
    """MLAgent with a model that classifies as benign (benign=0.95)."""
    mock_model = _make_mock_model([0.95, 0.03, 0.01, 0.01])
    with patch("agents.ml_agent.joblib.load", return_value=mock_model), \
         patch("agents.ml_agent.trusted_domain_manager") as mock_tdm:
        mock_tdm.is_trusted.return_value = False
        from agents.ml_agent import MLAgent
        agent = MLAgent()
        agent.model = mock_model
        yield agent, mock_tdm


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_load_failure_returns_fallback():
    """When joblib.load raises, ml_score must be 0.50 and finding warns the caller."""
    with patch("agents.ml_agent.joblib.load", side_effect=FileNotFoundError("no model")), \
         patch("agents.ml_agent.trusted_domain_manager"):
        from agents.ml_agent import MLAgent
        # Re-import to pick up fresh state
        import importlib
        import agents.ml_agent
        importlib.reload(agents.ml_agent)
        agent = agents.ml_agent.MLAgent()

    result = await agent.check("https://suspicious.example.com")
    assert result.ml_score == 0.50
    assert "WARNING" in result.finding


@pytest.mark.asyncio
async def test_whitelisted_domain_bypasses_inference(agent_with_model):
    """A trusted domain must short-circuit inference and return ml_score ≈ 0.01."""
    agent, mock_tdm = agent_with_model
    mock_tdm.is_trusted.return_value = True

    with patch("agents.ml_agent.extract_features", return_value={f: 0 for f in agent.feature_names}):
        result = await agent.check("https://google.com")

    assert result.ml_score == 0.01
    assert "whitelist" in result.finding.lower() or "bypassed" in result.finding.lower()
    # Model must NOT have been called
    agent.model.predict_proba.assert_not_called()


@pytest.mark.asyncio
async def test_feature_extraction_failure_returns_fallback(agent_with_model):
    """If extract_features returns None, ml_score must be 0.50."""
    agent, _ = agent_with_model
    with patch("agents.ml_agent.extract_features", return_value=None):
        result = await agent.check("https://suspicious-domain.xyz")

    assert result.ml_score == 0.50
    assert "WARNING" in result.finding


@pytest.mark.asyncio
async def test_phishing_classification(agent_with_model):
    """Model predicting phishing (benign_prob=0.1) should produce ml_score ≈ 0.90."""
    agent, _ = agent_with_model
    features = {name: 0 for name in agent.feature_names}
    features["entropy"] = 5.0          # triggers high-risk flag
    features["is_https"] = 0           # triggers HTTP flag

    with patch("agents.ml_agent.extract_features", return_value=features):
        result = await agent.check("https://evildomain.xyz/login")

    assert result.ml_score > 0.5
    assert result.threat_type == "phishing"
    assert len(result.high_risk_features) >= 1


@pytest.mark.asyncio
async def test_benign_classification(agent_benign_model):
    """Model predicting benign (benign_prob=0.95) should produce ml_score ≈ 0.05."""
    agent, _ = agent_benign_model
    features = {name: 0 for name in agent.feature_names}
    features["is_https"] = 1
    features["domain_age_days"] = 3650

    with patch("agents.ml_agent.extract_features", return_value=features):
        result = await agent.check("https://legitimate-site.com")

    assert result.ml_score < 0.5
    assert result.threat_type == "benign"
    assert result.high_risk_features == []


@pytest.mark.asyncio
async def test_high_risk_feature_ip_address(agent_with_model):
    """is_ip_address=1 in features should appear in high_risk_features."""
    agent, _ = agent_with_model
    features = {name: 0 for name in agent.feature_names}
    features["is_ip_address"] = 1

    with patch("agents.ml_agent.extract_features", return_value=features):
        result = await agent.check("http://192.168.1.1/admin")

    assert any("IP" in f or "ip" in f.lower() for f in result.high_risk_features)


@pytest.mark.asyncio
async def test_score_clamped_to_one(agent_with_model):
    """ml_score must never exceed 1.0 regardless of model output."""
    agent, _ = agent_with_model
    # Force predict_proba to return 0 for benign → ml_score = 1 - 0 = 1.0
    agent.model.predict_proba.return_value = np.array([[0.0, 1.0, 0.0, 0.0]])
    features = {name: 0 for name in agent.feature_names}

    with patch("agents.ml_agent.extract_features", return_value=features):
        result = await agent.check("https://worst-phish.com")

    assert result.ml_score <= 1.0
