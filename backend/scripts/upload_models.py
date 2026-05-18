"""
upload_models.py
----------------
One-time script: uploads ML model artifacts to their appropriate hosts.

  model.joblib           -> Hugging Face Hub (79 MB, exceeds Supabase 50 MB limit)
  email_model.joblib     -> Supabase Storage  bucket "models"
  email_vectorizer.joblib -> Supabase Storage bucket "models"

Run from the backend/ directory:
    cd backend
    pip install huggingface_hub
    python scripts/upload_models.py

Required env vars in backend/.env:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    HF_TOKEN          <- Hugging Face write token  (https://huggingface.co/settings/tokens)
    HF_REPO_ID        <- e.g. "taiwo-stack/cyberboyai-models"
"""

import os, sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR  = BACKEND_DIR / "models"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
HF_REPO_ID   = os.getenv("HF_REPO_ID", "")
BUCKET       = "models"

# ── Supabase: small models ────────────────────────────────────────────────────
SUPABASE_FILES = ["email_model.joblib", "email_vectorizer.joblib"]

# ── Hugging Face: large model ─────────────────────────────────────────────────
HF_FILES = ["model.joblib"]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Upload small models to Supabase Storage
# ─────────────────────────────────────────────────────────────────────────────
if not SUPABASE_URL or not SUPABASE_KEY:
    print("[upload] WARNING: SUPABASE_URL / SUPABASE_SERVICE_KEY not set. Skipping Supabase uploads.")
else:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        sb.storage.create_bucket(BUCKET, options={"public": False})
        print(f"[upload] Supabase bucket '{BUCKET}' created.")
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg:
            print(f"[upload] Supabase bucket '{BUCKET}' already exists.")
        else:
            print(f"[upload] Supabase bucket note: {e}")

    for filename in SUPABASE_FILES:
        src = MODELS_DIR / filename
        if not src.exists():
            print(f"[upload] SKIP {filename} - not found at {src}")
            continue

        data = src.read_bytes()
        print(f"[upload] >> Uploading {filename} ({len(data)/1_048_576:.1f} MB) to Supabase ...", flush=True)
        try:
            sb.storage.from_(BUCKET).upload(
                path=filename,
                file=data,
                file_options={"content-type": "application/octet-stream", "upsert": "true"},
            )
            print(f"[upload] OK {filename} -> Supabase Storage")
        except Exception as exc:
            print(f"[upload] FAIL {filename}: {exc}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Upload large model to Hugging Face Hub
# ─────────────────────────────────────────────────────────────────────────────
if not HF_TOKEN or not HF_REPO_ID:
    print("\n[upload] WARNING: HF_TOKEN / HF_REPO_ID not set. Skipping Hugging Face upload.")
    print("         Set these in backend/.env and re-run to upload model.joblib.")
else:
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        raise SystemExit("ERROR: Install huggingface_hub first:  pip install huggingface_hub")

    api = HfApi(token=HF_TOKEN)

    # Create the repo if it doesn't exist
    try:
        create_repo(HF_REPO_ID, token=HF_TOKEN, repo_type="model", exist_ok=True, private=True)
        print(f"[upload] HF repo '{HF_REPO_ID}' ready.")
    except Exception as e:
        print(f"[upload] HF repo note: {e}")

    for filename in HF_FILES:
        src = MODELS_DIR / filename
        if not src.exists():
            print(f"[upload] SKIP {filename} - not found at {src}")
            continue

        size_mb = src.stat().st_size / 1_048_576
        print(f"[upload] >> Uploading {filename} ({size_mb:.1f} MB) to Hugging Face ...", flush=True)
        try:
            api.upload_file(
                path_or_fileobj=str(src),
                path_in_repo=filename,
                repo_id=HF_REPO_ID,
                repo_type="model",
            )
            print(f"[upload] OK {filename} -> HF Hub ({HF_REPO_ID})")
        except Exception as exc:
            print(f"[upload] FAIL {filename}: {exc}")

print("\n[upload] Complete.")
