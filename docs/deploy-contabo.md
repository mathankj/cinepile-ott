# Deploying to the Contabo VPS (alongside the kotak apps)

The VPS at `185.197.249.70` already runs two stock-trading applications as
systemd services behind the host nginx:

| Existing app          | Host ports it owns        |
|-----------------------|---------------------------|
| kotak.service         | 5000 (app), 80 (nginx)    |
| kotak-reverse.service | 5001 (app), 8081 (nginx)  |

**The OTT deployment must never touch these.** That is why it ships as Docker
containers: its entire host footprint is one directory (`/opt/cinepile`), the
Docker engine, and one TCP port — **8090**. No systemd units are added or
edited, and the host nginx config is not modified.

## Architecture

```
internet ──:8090──> [web container: nginx]
                       ├── serves the built React SPA
                       └── proxies /v1, /healthz, /docs ──> [api container: FastAPI :8000]
                                                                  └──> Neon Postgres (cloud)
```

- The API port (8000) exists only on the compose-internal network — never on
  the host, so it can't collide with anything.
- The database is Neon (cloud). Nothing stateful lives on the VPS; you can
  `docker compose down`, delete `/opt/cinepile`, and the kotak apps won't
  notice it was ever there.

## One-command deploy

From the repo root on the dev machine (Windows):

```powershell
$env:CONTABO_PASSWORD = "<current root password>"
python deploy/deploy_contabo.py
```

The script: checks the kotak services are running and port 8090 is free →
installs Docker if absent → uploads a `git archive` of HEAD → uploads
`deploy/.env.production` as `backend/.env` → `docker compose up -d --build` →
health-checks `http://127.0.0.1:8090/healthz` → re-checks the kotak services
and prints a before/after comparison.

Re-running the script is the update procedure (it re-ships HEAD and rebuilds).

## Secrets

`deploy/.env.production` holds the real DATABASE_URL, JWT secret, Razorpay
test keys, and B2 storage keys. It is **gitignored** (`.env.*` rule) and only
ever copied over SSH to `/opt/cinepile/backend/.env` (chmod 600).

## Useful commands on the server

```bash
cd /opt/cinepile
docker compose ps               # both containers should be "running (healthy)"
docker compose logs -f api      # backend logs
docker compose restart api      # bounce just the backend
docker compose down             # stop the OTT app (kotak unaffected)
```

## Known gaps before real production

- Port 8090 over plain HTTP. For a domain + HTTPS, add a server block to the
  host nginx (or a Caddy container on 443) — coordinate with the kotak nginx
  on port 80/443 when that day comes.
- Same Neon database as dev/staging — create a separate Neon branch/database
  for real client data and swap `DATABASE_URL`.
- Razorpay is in TEST mode until the client's KYC clears.
