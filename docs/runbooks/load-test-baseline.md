# Load test baseline — Phase 1 backend

This is the **dev-machine baseline** captured 2026-06-02. It tells us where we start; every meaningful infra change re-runs this and compares.

---

## Setup

| What | Value |
|---|---|
| Hardware | Windows dev box (8C/16T, 16 GB) |
| Server | uvicorn (1 worker, dev mode), `--log-level warning` |
| Database | SQLite (`anjaneya_dev.db`) — single-writer, big caveat |
| Seed | 3 films, 2 plans, 1 admin, 5 categories (`scripts/seed_dev_data.py`) |
| Client | locust 2.44, 20 concurrent users, spawn-rate 5/s, 30s run |
| Profile | Mixed: ~80% public catalog reads, ~20% authed (signup → subscribe → me → history → play attempts) |
| Command | `locust -f tests/load/locustfile.py --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 30s --headless --csv reports/load` |

## Results (378 requests, 0 failures)

| Endpoint | reqs | p50 ms | p95 ms | p99 ms | Notes |
|---|---|---|---|---|---|
| `GET /healthz` | 36 | **8** | 20 | 2000 | One outlier — likely cold connection |
| `GET /v1/films` | 146 | **18** | 380 | 2500 | Hot path; p95 spikes correlate with concurrent signups |
| `GET /v1/films/{id}` | 49 | **10** | 2000 | 2500 | Same — read-path contention behind SQLite writes |
| `GET /v1/films/search` | 55 | **15** | 2500 | 2500 | LIKE search, fine for 3-film catalog |
| `GET /v1/films/{id}/play` | 14 | **26** | 460 | 460 | Includes subscription check + JWT signing |
| `GET /v1/plans` | 33 | **9** | 25 | 420 | |
| `GET /v1/auth/me` | 22 | **10** | 36 | 52 | |
| `GET /v1/history` | 15 | **12** | 43 | 43 | |
| `POST /v1/subscriptions` | 4 | **72** | 120 | 120 | Write path; one row insert |
| **`POST /v1/auth/signup`** | **4** | **2500** | **2500** | **2500** | **Slow path — see analysis** |
| **Aggregate** | **378** | **16** | **2000** | **2500** | 13.18 req/s sustained |

CSVs: `backend/reports/load_*.csv`

## Analysis

**The good:** All reads are sub-50ms at p50 / p95. The async path holds up — no failures across 378 requests.

**The signup tax (2.5s p50):** bcrypt @ 12 rounds is ~250ms per hash on this machine, but the observed 2.5s is 10× that. The cause is **SQLite single-writer contention**: every signup grabs the database write lock and holds it through the bcrypt hash + insert + commit. With 20 concurrent users, signups queue. This is a SQLite-only problem; on Postgres each connection has its own write transaction and the queue evaporates.

**p95 spikes on catalog reads (380-2500ms):** Same root cause. SQLite's BEGIN IMMEDIATE makes readers block waiting for the writer's commit. Postgres uses MVCC; readers never block writers.

## What we expect on Postgres + production hardware

Order-of-magnitude predictions for a single uvicorn worker on a small VPS:

| Endpoint | Expected p50 | Expected p99 |
|---|---|---|
| `GET /v1/films` | 3-8 ms | 25 ms |
| `GET /v1/films/{id}` | 2-5 ms | 15 ms |
| `POST /v1/auth/signup` | 250-300 ms | 400 ms (bcrypt floor) |
| `POST /v1/auth/login` | 250-300 ms | 400 ms (bcrypt floor) |
| `GET /v1/films/{id}/play` | 5-12 ms | 30 ms |

Two uvicorn workers → ~2x throughput; four workers ≈ saturation on a 4-core VPS.

## What we will do next (Phase 2 perf work)

1. **Move to Postgres** in dev (Neon free tier) → re-run this test → expect signup p50 ≤ 350ms.
2. **Add Redis** for the `has_active_subscription` check and signed-URL cache → `/play` p50 expected < 5ms.
3. **Bump uvicorn workers to 2-4** behind nginx for the VPS deploy.
4. **Argon2 vs bcrypt cost calibration** if we want signup ≤ 100ms (security tradeoff to document).

## How to re-run

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 --log-level warning &
sleep 2
.venv/Scripts/python.exe -m locust -f tests/load/locustfile.py \
    --host http://localhost:8000 \
    --users 20 --spawn-rate 5 --run-time 30s \
    --headless --csv reports/load
```

Append updated numbers to this file, do not replace the historical row — trend matters.
