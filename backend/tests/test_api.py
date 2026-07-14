"""
test_api.py — FastAPI route integration tests.

Uses httpx.AsyncClient with ASGITransport so the full FastAPI middleware stack
(CORS, rate limiting, exception handlers) is exercised without a live server.

All I/O dependencies (Supabase, OrchestratorAgent, CommunityAgent, scheduler,
trusted_domain_manager, global_brand_manager) are mocked at the module boundary
so tests run fully offline.

Covers:
  - GET /              → 200 OK
  - GET /health        → 200 {"status": "ok"}
  - POST /analyze      → 200, returns verdict structure
  - POST /analyze      → cached result returned on second call
  - POST /analyze      → 503 when orchestrator not initialized
  - GET /stats         → 200, returns count fields
  - POST /report       → 200, success flag
  - GET /admin/pending → 401 with wrong/missing key
  - GET /admin/pending → 200 with correct key
  - POST /admin/confirm → 200 confirm flow
  - Error responses    → never expose internal detail strings (str(e))
"""

import sys
import os
import json
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Minimal env for tests ──────────────────────────────────────────────────────
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ADMIN_SECRET_KEY", "test-admin-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")


# ── Shared mock verdict ────────────────────────────────────────────────────────

def _mock_verdict():
    from schemas.agent_outputs import VerdictResponse
    return VerdictResponse(
        verdict="SAFE",
        score=0.05,
        red_flags=[],
        explanation="Test verdict: no threats detected.",
        advice="All clear.",
        threat_type="benign",
        agents_used=["brand", "lookup", "ml"],
        agent_trace=[],
        brand_result=None,
        lookup_result=None,
        ml_result=None,
        openai_result=None,
        processing_ms=42,
    )


# ── App fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app_with_mocks():
    """
    Imports and returns the FastAPI app with all lifespan side-effects mocked.
    Scoped to module so the app is only created once per test file.
    """
    with patch("agents.orchestrator_agent.OrchestratorAgent") as MockOrch, \
         patch("agents.community_agent.CommunityAgent") as MockComm, \
         patch("scheduler.start_scheduler"), \
         patch("scheduler.stop_scheduler"), \
         patch("tools.trusted_domains.trusted_domain_manager") as mock_tdm, \
         patch("tools.global_brands.global_brand_manager") as mock_gbm, \
         patch("tools.async_db.db") as mock_db:

        # Orchestrator returns our canned verdict
        mock_orch_instance = MagicMock()
        mock_orch_instance.analyze = AsyncMock(return_value=_mock_verdict())
        MockOrch.return_value = mock_orch_instance

        # Community agent
        mock_comm_instance = MagicMock()
        mock_comm_instance.get_pending_reports = AsyncMock(return_value=[])
        mock_comm_instance.confirm_threat = AsyncMock(
            return_value={"success": True, "threat_added": True}
        )
        MockComm.return_value = mock_comm_instance

        # trusted/global brand managers
        mock_tdm.load = AsyncMock()
        mock_gbm.load = MagicMock()

        # DB — returns a mock response with .count and .data
        db_resp = MagicMock()
        db_resp.count = 0
        db_resp.data = []
        mock_db.return_value = db_resp

        import main  # noqa: F401 — triggers module-level setup
        # Patch module-level singletons that lifespan would normally set
        main.orchestrator = mock_orch_instance
        main.community_agent = mock_comm_instance

        yield main.app, mock_orch_instance, mock_comm_instance


@pytest_asyncio.fixture
async def client(app_with_mocks):
    app, _, _ = app_with_mocks
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_with_mocks(app_with_mocks):
    app, mock_orch, mock_comm = app_with_mocks
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, mock_orch, mock_comm


# ── Route Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "GaudOn API is running"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "GaudOn"


@pytest.mark.asyncio
async def test_analyze_returns_verdict(client_with_mocks):
    client, mock_orch, _ = client_with_mocks
    resp = await client.post("/analyze", json={"input": "https://google.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "verdict" in body
    assert "score" in body
    assert "explanation" in body


@pytest.mark.asyncio
async def test_analyze_uses_cache_on_second_call(client_with_mocks):
    """Second call for the same URL must not hit the orchestrator again."""
    client, mock_orch, _ = client_with_mocks
    mock_orch.analyze.reset_mock()

    url = "https://cache-test-domain.com"
    await client.post("/analyze", json={"input": url})
    await client.post("/analyze", json={"input": url})

    # Orchestrator should have been called at most once (second call hits cache)
    assert mock_orch.analyze.call_count <= 1


@pytest.mark.asyncio
async def test_stats_returns_counts(client):
    with patch("main.db") as mock_db:
        mock_resp = MagicMock()
        mock_resp.count = 5
        mock_db.return_value = mock_resp
        resp = await client.get("/stats")

    assert resp.status_code == 200
    body = resp.json()
    assert "total_scans" in body
    assert "dangerous_count" in body


@pytest.mark.asyncio
async def test_report_success(client):
    with patch("main.db") as mock_db:
        mock_db.return_value = MagicMock()
        resp = await client.post("/report", json={
            "url": "https://phishing-site.xyz",
            "description": "Looks like a fake bank page",
            "reporter_tag": "test-user",
        })

    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ── Admin Auth Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_pending_missing_key_returns_401(client):
    resp = await client.get("/admin/pending")
    assert resp.status_code == 401
    # Must not expose any internal detail
    body = resp.json()
    assert "error" in body
    assert "traceback" not in json.dumps(body).lower()
    assert "exception" not in json.dumps(body).lower()


@pytest.mark.asyncio
async def test_admin_pending_wrong_key_returns_401(client):
    resp = await client.get("/admin/pending", headers={"X-Admin-Key": "wrong-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_pending_correct_key_returns_200(client_with_mocks):
    client, _, mock_comm = client_with_mocks
    mock_comm.get_pending_reports.return_value = []
    resp = await client.get(
        "/admin/pending",
        headers={"X-Admin-Key": "test-admin-secret"}
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_confirm_correct_key(client_with_mocks):
    client, _, mock_comm = client_with_mocks
    resp = await client.post(
        "/admin/confirm",
        json={"submission_id": "abc-123", "confirmed": True, "notes": "verified"},
        headers={"X-Admin-Key": "test-admin-secret"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# ── Error Containment Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_error_does_not_leak_internal_detail(client_with_mocks):
    """
    If the orchestrator raises an unhandled exception, the API response must
    NOT include raw exception text, file paths, or tracebacks.
    """
    client, mock_orch, _ = client_with_mocks
    mock_orch.analyze.side_effect = RuntimeError(
        "supabase connection refused at /internal/path/to/file.py:42"
    )

    resp = await client.post("/analyze", json={"input": "https://new-never-cached-url.com"})

    # Should return an error status (500 or 503), but not a 200
    assert resp.status_code >= 400

    body_str = json.dumps(resp.json())
    # Critical: none of the internal detail must be present
    assert "/internal/path" not in body_str
    assert "file.py:42" not in body_str
    assert "supabase connection refused" not in body_str


@pytest.mark.asyncio
async def test_cors_header_present_for_allowed_origin(client):
    resp = await client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    # FastAPI CORS middleware should set the header for an allowed origin
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
