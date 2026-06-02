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
2. Convert the prefix from `postgresql://` to `postgresql+asyncpg://`.
3. Put it in `backend/.env` as `DATABASE_URL=postgresql+asyncpg://...`.
4. Restart the dev server. `/healthz` should still show `"db": "ok"`.

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
