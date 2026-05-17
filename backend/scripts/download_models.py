"""
download_models.py
------------------
Downloads trained ML model artifacts from Supabase Storage into the
/app/models/ directory at container startup.

Run order (in Dockerfile):
    python scripts/download_models.py && uvicorn main:app ...

Models expected in Supabase Storage bucket "models":
    - model.joblib           (URL phishing/malware RF classifier, ~83 MB)
    - email_model.joblib     (email spam/phishing RF classifier)
    - email_vectorizer.joblib (TF-IDF vectorizer for email model)

Environment variables required:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = SCRIPT_DIR.parent                       # backend/
MODELS_DIR  = BACKEND_DIR / "models"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

BUCKET = "models"

MODEL_FILES = [
    "model.joblib",
    "email_model.joblib",
    "email_vectorizer.joblib",
]

# ── Guard ─────────────────────────────────────────────────────────────────────
if not SUPABASE_URL or not SUPABASE_KEY:
    print("[download_models] WARNING: SUPABASE_URL / SUPABASE_SERVICE_KEY not set. "
          "Skipping model download — agents will run in degraded mode.", flush=True)
    sys.exit(0)

# ── Download ──────────────────────────────────────────────────────────────────
try:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:
    print(f"[download_models] ERROR: Could not create Supabase client: {exc}", flush=True)
    sys.exit(0)  # non-fatal: degrade gracefully

MODELS_DIR.mkdir(parents=True, exist_ok=True)

all_ok = True
for filename in MODEL_FILES:
    dest = MODELS_DIR / filename
    if dest.exists():
        print(f"[download_models] ✓ {filename} already present ({dest.stat().st_size // 1024} KB), skipping.", flush=True)
        continue

    print(f"[download_models] ↓ Downloading {filename} from Supabase Storage ...", flush=True)
    try:
        data: bytes = client.storage.from_(BUCKET).download(filename)
        dest.write_bytes(data)
        print(f"[download_models] ✓ {filename} saved ({len(data) // 1024} KB).", flush=True)
    except Exception as exc:
        print(f"[download_models] ✗ Failed to download {filename}: {exc}", flush=True)
        all_ok = False

if all_ok:
    print("[download_models] All models ready.", flush=True)
else:
    print("[download_models] Some models could not be downloaded. "
          "Affected agents will run in degraded mode.", flush=True)
