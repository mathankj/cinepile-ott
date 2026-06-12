# Backend image — FastAPI + uvicorn.
#
# Runs Alembic migrations on every start (idempotent — `upgrade head` is a
# no-op when the DB is current), then serves on :8000. The port is only
# exposed on the compose-internal network; the web container's nginx is the
# single public entrypoint.
FROM python:3.13-slim

# Non-root user — the app needs no privileges inside the container.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Install the package (deps come from pyproject.toml). Copying everything in
# one layer keeps this simple; the VPS rebuilds rarely and `pip install`
# itself caches wheels poorly across image builds anyway.
COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN pip install --no-cache-dir .

USER appuser

# Config (DATABASE_URL, JWT_SECRET, Razorpay keys, ...) comes exclusively from
# environment variables — compose injects backend/.env via env_file. There is
# deliberately no .env baked into the image.
EXPOSE 8000

# Two uvicorn workers: enough for a small VPS without starving the kotak
# services of CPU. Note the in-process TTL caches and rate-limit windows are
# per-worker — fine for caching (just duplicated), slightly looser for rate
# limiting (each worker counts separately).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]

# Healthcheck without curl (slim image): python stdlib only.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"]
