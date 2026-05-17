"""
upload_models.py
----------------
One-time script: uploads local .joblib model files to a Supabase Storage
bucket called "models" so they can be downloaded at deployment time.

Run from the backend/ directory:
    cd backend
    python scripts/upload_models.py

You must have SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR  = BACKEND_DIR / "models"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = "models"

FILES = [
    "model.joblib",
    "email_model.joblib",
    "email_vectorizer.joblib",
]

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env first.")

from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create the bucket if it doesn't exist (public=False keeps models private)
try:
    client.storage.create_bucket(BUCKET, options={"public": False})
    print(f"[upload] Bucket '{BUCKET}' created.")
except Exception as e:
    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
        print(f"[upload] Bucket '{BUCKET}' already exists.")
    else:
        print(f"[upload] Bucket note: {e}")

for filename in FILES:
    src = MODELS_DIR / filename
    if not src.exists():
        print(f"[upload] ✗ {filename} not found at {src}, skipping.")
        continue

    data = src.read_bytes()
    size_mb = len(data) / 1_048_576
    print(f"[upload] ↑ Uploading {filename} ({size_mb:.1f} MB) ...", flush=True)

    try:
        # upsert=True overwrites if already present
        client.storage.from_(BUCKET).upload(
            path=filename,
            file=data,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
        print(f"[upload] ✓ {filename} uploaded successfully.")
    except Exception as exc:
        print(f"[upload] ✗ Failed to upload {filename}: {exc}")

print("\n[upload] Done. Run 'python scripts/download_models.py' to verify.")
