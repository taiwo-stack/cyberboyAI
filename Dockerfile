# ─────────────────────────────────────────────────────────────
# GaudOn – Backend API
# Build context: repository root  (docker build -f Dockerfile .)
# The backend source lives in ./backend/
# ─────────────────────────────────────────────────────────────

FROM python:3.10-slim

# ── Environment ──────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ── System dependencies (Playwright + wheel builds) ───────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (cached layer) ───────────────────────
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Playwright browser + system libs ─────────────────────────
RUN pip install --no-cache-dir playwright \
    && playwright install chromium \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# ── Application source ────────────────────────────────────────
COPY backend/ .

# ── Port ──────────────────────────────────────────────────────
EXPOSE 8000

# ── Start ─────────────────────────────────────────────────────
CMD python scripts/download_models.py && uvicorn main:app --host 0.0.0.0 --port 8000
