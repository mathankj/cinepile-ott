# Dev setup — backend

For Windows (the dev machine) and Linux/macOS (the eventual VPS). Steps are identical except for venv activation.

---

## Prerequisites

- Python **3.11+** (3.13 used on the dev machine; 3.14 also works but 3.13 is the safer pin)
- `git`
- Optional but recommended for prod-parity DB: a free Neon Postgres URL — sign up at https://neon.tech and create a project. Copy the connection string.

You do **not** need Docker, Postgres, or Redis locally. The default `.env` uses SQLite so you can start cold.

---

## First-time setup

```bash
# From repo root
cd backend

# Create venv
py -3.13 -m venv .venv             # Windows
# python3.13 -m venv .venv         # Linux/macOS

# Activate
.venv/Scripts/activate             # Windows (Git Bash / PowerShell uses Activate.ps1)
# source .venv/bin/activate        # Linux/macOS

# Install backend (editable) + dev tools
pip install -e ".[dev]"

# Copy env template
cp .env.example .env
# Open .env and at minimum set JWT_SECRET to a random 32+ char string.
# DATABASE_URL defaults to SQLite — fine for first boot.
```

## Run the dev server

```bash
uvicorn app.main:app --reload --port 8000
```

Open:
- API docs (Swagger UI): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/healthz
- Raw OpenAPI: http://localhost:8000/openapi.json

## Run the tests

```bash
pytest                              # all tests
pytest tests/unit                   # unit only
pytest tests/integration            # integration only
pytest -k "test_healthz"            # by name match
pytest --cov=app --cov-report=html  # coverage report → htmlcov/index.html
```

## Switch to real Postgres (Neon)

1. Get the connection string from your Neon dashboard.
2. **Three substitutions required** — Neon's default string is shaped for psycopg2; we use asyncpg:
   - `postgresql://` → `postgresql+asyncpg://`
   - `sslmode=require` → `ssl=require` (asyncpg doesn't understand `sslmode`)
   - Use the `-pooler` host (Neon's built-in PgBouncer) for better connection reuse
3. Final shape:
   ```
   DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST-pooler.REGION.aws.neon.tech/DB?ssl=require
   ```
4. Apply the migration:
   ```bash
   cd backend
   .venv/Scripts/python.exe -m alembic upgrade head
   ```
5. Seed:
   ```bash
   .venv/Scripts/python.exe ../scripts/seed_dev_data.py
   ```
6. Restart the dev server. `/healthz` should show `"db": "ok"`.

**Test suite is unaffected** — pytest forces `DATABASE_URL=sqlite+aiosqlite:///:memory:` via conftest, so the 65 tests keep running against isolated in-memory SQLite regardless of what's in `.env`.

## Lint and type-check

```bash
ruff check app tests                # lint
ruff format app tests               # format
mypy app                            # type check (will be enforced once code lands)
```

## When something goes wrong

- **"DATABASE_URL is required"** at startup → check `.env` exists and is in `backend/`.
- **`bcrypt` install fails on Windows** → already pinned to a wheel-shipping version; if pip falls back to source, install MS Build Tools or `pip install bcrypt --only-binary :all:`.
- **Port in use** → another uvicorn is running. `taskkill /F /IM python.exe` on Windows.
- **Tests hang** → almost always a missing `await`. Run `pytest -x` to stop on first failure.
