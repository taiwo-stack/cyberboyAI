"""
download_models.py
------------------
Downloads trained ML model artifacts into /app/models/ at container startup.

Sources:
  model.joblib            <- Hugging Face Hub  (HF_REPO_ID env var)
  email_model.joblib      <- Supabase Storage  bucket "models"
  email_vectorizer.joblib <- Supabase Storage  bucket "models"

Run order in Dockerfile CMD:
    python scripts/download_models.py && uvicorn main:app ...

Required environment variables (set in Render/Vercel/etc dashboard):
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    HF_TOKEN      <- Hugging Face read token
    HF_REPO_ID    <- e.g. "taiwo-stack/gaudon-models"
"""

import os, sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR  = BACKEND_DIR / "models"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
HF_REPO_ID   = os.getenv("HF_REPO_ID", "")
BUCKET       = "models"

SUPABASE_FILES = ["email_model.joblib", "email_vectorizer.joblib"]
HF_FILES       = ["model.joblib"]

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Download small models from Supabase Storage
# ─────────────────────────────────────────────────────────────────────────────
if not SUPABASE_URL or not SUPABASE_KEY:
    print("[download_models] WARNING: Supabase creds missing. Skipping email model downloads.", flush=True)
else:
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)

        for filename in SUPABASE_FILES:
            dest = MODELS_DIR / filename
            if dest.exists():
                print(f"[download_models] SKIP {filename} (already present, {dest.stat().st_size // 1024} KB)", flush=True)
                continue
            print(f"[download_models] >> Downloading {filename} from Supabase ...", flush=True)
            try:
                data: bytes = sb.storage.from_(BUCKET).download(filename)
                dest.write_bytes(data)
                print(f"[download_models] OK {filename} ({len(data) // 1024} KB)", flush=True)
            except Exception as exc:
                print(f"[download_models] FAIL {filename}: {exc}", flush=True)
    except Exception as exc:
        print(f"[download_models] Supabase client error: {exc}", flush=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Download large model from Hugging Face Hub
# ─────────────────────────────────────────────────────────────────────────────
if not HF_TOKEN or not HF_REPO_ID:
    print("[download_models] WARNING: HF_TOKEN / HF_REPO_ID not set. Skipping model.joblib download.", flush=True)
    print("[download_models] URL ML scoring will run in degraded mode.", flush=True)
else:
    for filename in HF_FILES:
        dest = MODELS_DIR / filename
        if dest.exists():
            print(f"[download_models] SKIP {filename} (already present, {dest.stat().st_size // 1024} KB)", flush=True)
            continue
        print(f"[download_models] >> Downloading {filename} from Hugging Face ({HF_REPO_ID}) ...", flush=True)
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(
                repo_id=HF_REPO_ID,
                filename=filename,
                token=HF_TOKEN,
                local_dir=str(MODELS_DIR),
                local_dir_use_symlinks=False,
            )
            print(f"[download_models] OK {filename} -> {path}", flush=True)
        except Exception as exc:
            print(f"[download_models] FAIL {filename}: {exc}", flush=True)

print("[download_models] Done.", flush=True)
