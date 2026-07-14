import sys
import asyncio

# ---------------------------------------------------------------------------
# CRITICAL WINDOWS ASYNCIO FIX (Must be at the absolute top)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    # Force ProactorEventLoop to support Playwright's browser subprocesses
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import hmac
import logging
import os
import threading
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Optional

# Ensure the backend directory is always on the path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from agents.orchestrator_agent import OrchestratorAgent
from agents.community_agent import CommunityAgent
from exceptions import (
    GaudonError,
    AnalysisError,
    ServiceUnavailableError,
    AuthorizationError,
    NotFoundError,
    gaudon_error_handler,
    unhandled_exception_handler,
)
from scheduler import start_scheduler, stop_scheduler
from schemas.agent_inputs import AnalyzeRequest
from tools.supabase_client import supabase
from tools.async_db import db
from tools.trusted_domains import trusted_domain_manager
from tools.global_brands import global_brand_manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gaudon.main")

# ---------------------------------------------------------------------------
# Thread-safe LRU + TTL in-memory result cache
# ---------------------------------------------------------------------------
_CACHE_TTL = 600   # seconds
_CACHE_MAX = 500   # max entries


class _ResultCache:
    """LRU + TTL cache backed by an OrderedDict.

    Thread-safe: all mutations are protected by a reentrant lock so that
    concurrent async tasks (running in a thread pool) cannot corrupt state.
    """

    def __init__(self) -> None:
        self._store: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry and (time.time() - entry["ts"] < _CACHE_TTL):
                self._store.move_to_end(key)
                return entry["value"]
            if entry:
                del self._store[key]
            return None

    def set(self, key: str, value) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = {"value": value, "ts": time.time()}
            if len(self._store) > _CACHE_MAX:
                self._store.popitem(last=False)


_result_cache = _ResultCache()

orchestrator: Optional[OrchestratorAgent] = None
community_agent: Optional[CommunityAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator, community_agent

    def _prewarm_tldextract():
        import tldextract
        tldextract.extract("prewarm.example.com")

    # Use get_running_loop() — get_event_loop() is deprecated in Python 3.10+
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _prewarm_tldextract)

    orchestrator = OrchestratorAgent()
    community_agent = CommunityAgent()
    await trusted_domain_manager.load()
    global_brand_manager.load()
    start_scheduler()
    logger.info("GaudOn startup complete.")
    yield
    stop_scheduler()
    logger.info("GaudOn shutdown complete.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="GaudOn API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS — read allowed origins from env; never fall back to wildcard "*"
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:8080",
)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Exception Handlers — safe, non-leaking responses
# ---------------------------------------------------------------------------
app.add_exception_handler(GaudonError, gaudon_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class AdminConfirmRequest(BaseModel):
    submission_id: str
    confirmed: bool
    notes: str = ""


class ReportRequest(BaseModel):
    url: str
    description: str = ""
    reporter_tag: str = "anonymous"


# ---------------------------------------------------------------------------
# Admin Auth Dependency
# ---------------------------------------------------------------------------
def verify_admin_key(x_admin_key: str = Header(None)) -> str:
    expected = os.getenv("ADMIN_SECRET_KEY", "")
    if not x_admin_key or not hmac.compare_digest(
        x_admin_key.encode(), expected.encode()
    ):
        raise AuthorizationError(
            internal_detail="Invalid or missing X-Admin-Key header.",
        )
    return x_admin_key


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "GaudOn API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "GaudOn", "version": "1.0"}


@app.post("/analyze")
@limiter.limit("30/minute")
async def analyze_url(request: Request, analyze_req: AnalyzeRequest):
    if not orchestrator:
        raise ServiceUnavailableError(
            internal_detail="Orchestrator not initialized — lifespan may not have completed.",
        )

    cache_key = analyze_req.raw_input.strip().lower()
    cached = _result_cache.get(cache_key)
    if cached:
        return cached

    try:
        response = await orchestrator.analyze(analyze_req)
    except GaudonError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in /analyze for input=%r", analyze_req.raw_input)
        raise AnalysisError(internal_detail=str(exc)) from exc

    _result_cache.set(cache_key, response)
    return response


@app.get("/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request):
    try:
        total     = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").execute())
        dangerous = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "DANGEROUS").execute())
        suspicious= await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "SUSPICIOUS").execute())
        safe      = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "SAFE").execute())
        community = await db(lambda: supabase.table("community_threats").select("id", count="exact").eq("confirmed", True).execute())
    except Exception as exc:
        logger.exception("DB error in /stats")
        raise ServiceUnavailableError(internal_detail=str(exc)) from exc

    return {
        "total_scans": total.count or 0,
        "dangerous_count": dangerous.count or 0,
        "suspicious_count": suspicious.count or 0,
        "safe_count": safe.count or 0,
        "community_threats_count": community.count or 0,
    }


@app.post("/report")
@limiter.limit("10/minute")
async def report_threat(request: Request, report: ReportRequest):
    data = {
        "raw_input": report.url.strip(),
        "input_type": "url",
        "verdict": "PENDING_REVIEW",
        "final_score": 0.0,
        "red_flags": [],
        "explanation": report.description or "User-submitted suspicious URL.",
        "advice": "Under review.",
        "agent_trace": [],
        "brand_score": 0.0,
        "db_score": 0.0,
        "ml_score": 0.0,
        "claude_score": 0.0,
        "source": "community_report",
        "reviewed": False,
        "reporter_tag": report.reporter_tag,
    }
    try:
        await db(lambda: supabase.table("threat_submissions").insert(data).execute())
    except Exception as exc:
        logger.exception("DB error in /report for url=%r", report.url)
        raise ServiceUnavailableError(internal_detail=str(exc)) from exc

    return {"success": True, "message": "Thank you. Your report has been submitted for review."}


@app.get("/admin/pending")
@limiter.limit("30/minute")
async def admin_pending(request: Request, admin_key: str = Depends(verify_admin_key)):
    try:
        reports = await community_agent.get_pending_reports()
    except Exception as exc:
        logger.exception("DB error in /admin/pending")
        raise ServiceUnavailableError(internal_detail=str(exc)) from exc
    return reports


@app.post("/admin/confirm")
@limiter.limit("30/minute")
async def admin_confirm(
    request: Request,
    req: AdminConfirmRequest,
    admin_key: str = Depends(verify_admin_key),
):
    try:
        result = await community_agent.confirm_threat(
            submission_id=req.submission_id,
            confirmed=req.confirmed,
            notes=req.notes,
        )
    except Exception as exc:
        logger.exception("DB error in /admin/confirm for submission_id=%r", req.submission_id)
        raise ServiceUnavailableError(internal_detail=str(exc)) from exc

    if not result.get("success"):
        raise NotFoundError(
            internal_detail=f"confirm_threat returned failure: {result}",
            safe_message=result.get("error", "Submission not found."),
        )
    return result
