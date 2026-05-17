import sys
import asyncio

# ---------------------------------------------------------------------------
# CRITICAL WINDOWS ASYNCIO FIX (Must be at the absolute top)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    # Force ProactorEventLoop to support Playwright's browser subprocesses
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import hmac
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
from pydantic import BaseModel

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from agents.orchestrator_agent import OrchestratorAgent
from agents.community_agent import CommunityAgent
from scheduler import start_scheduler, stop_scheduler
from schemas.agent_inputs import AnalyzeRequest
from tools.supabase_client import supabase
from tools.async_db import db
from tools.trusted_domains import trusted_domain_manager
from tools.global_brands import global_brand_manager

# ---------------------------------------------------------------------------
# Simple in-memory result cache
# ---------------------------------------------------------------------------
_CACHE_TTL = 600
_CACHE_MAX = 500

class _ResultCache:
    def __init__(self):
        self._store: OrderedDict = OrderedDict()

    def get(self, key: str):
        entry = self._store.get(key)
        if entry and (time.time() - entry["ts"] < _CACHE_TTL):
            self._store.move_to_end(key)
            return entry["value"]
        if entry:
            del self._store[key]
        return None

    def set(self, key: str, value):
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

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _prewarm_tldextract)

    orchestrator = OrchestratorAgent()
    community_agent = CommunityAgent()
    await trusted_domain_manager.load()
    global_brand_manager.load()
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="CyberBoyAI API", lifespan=lifespan)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:8080")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class AdminConfirmRequest(BaseModel):
    submission_id: str
    confirmed: bool
    notes: str = ""

class ReportRequest(BaseModel):
    url: str
    description: str = ""
    reporter_tag: str = "anonymous"

def verify_admin_key(x_admin_key: str = Header(None)):
    expected = os.getenv("ADMIN_SECRET_KEY", "")
    if not x_admin_key or not hmac.compare_digest(
        x_admin_key.encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_admin_key

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CyberBoyAI", "version": "1.0"}

@app.post("/analyze")
@limiter.limit("30/minute")
async def analyze_url(request: Request, analyze_req: AnalyzeRequest):
    try:
        if not orchestrator:
            raise Exception("Orchestrator not initialized.")

        cached = _result_cache.get(analyze_req.input.strip().lower())
        if cached:
            return cached

        response = await orchestrator.analyze(analyze_req)
        _result_cache.set(analyze_req.input.strip().lower(), response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.get("/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request):
    try:
        total     = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").execute())
        dangerous = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "DANGEROUS").execute())
        suspicious= await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "SUSPICIOUS").execute())
        safe      = await db(lambda: supabase.table("threat_submissions").select("id", count="exact").eq("verdict", "SAFE").execute())
        community = await db(lambda: supabase.table("community_threats").select("id", count="exact").eq("confirmed", True).execute())

        return {
            "total_scans": total.count or 0,
            "dangerous_count": dangerous.count or 0,
            "suspicious_count": suspicious.count or 0,
            "safe_count": safe.count or 0,
            "community_threats_count": community.count or 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.post("/report")
@limiter.limit("10/minute")
async def report_threat(request: Request, report: ReportRequest):
    try:
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
        await db(lambda: supabase.table("threat_submissions").insert(data).execute())
        return {"success": True, "message": "Thank you. Your report has been submitted for review."}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.get("/admin/pending")
@limiter.limit("30/minute")
async def admin_pending(request: Request, admin_key: str = Depends(verify_admin_key)):
    try:
        reports = await community_agent.get_pending_reports()
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.post("/admin/confirm")
@limiter.limit("30/minute")
async def admin_confirm(request: Request, req: AdminConfirmRequest, admin_key: str = Depends(verify_admin_key)):
    try:
        result = await community_agent.confirm_threat(
            submission_id=req.submission_id,
            confirmed=req.confirmed,
            notes=req.notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})
