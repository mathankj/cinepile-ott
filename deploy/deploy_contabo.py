"""Deploy CinePile OTT to the Contabo VPS — containers only, zero contact with
the kotak applications already running there.

What it does, in order:
  1. Connects over SSH (paramiko — sshpass isn't a thing on Windows).
  2. Pre-flight: confirms the kotak services are running BEFORE we start, and
     that port 8090 is free. We re-check kotak again at the end — if this
     script ever breaks them, it tells you loudly.
  3. Installs Docker via get.docker.com if missing (additive; touches nothing
     existing).
  4. Uploads a `git archive` tarball of HEAD (works for private repos, no
     GitHub token ever lands on the server) and unpacks to /opt/cinepile.
  5. Uploads deploy/.env.production as backend/.env on the server.
  6. `docker compose up -d --build`, waits, then curls /healthz through the
     published port.

Usage (from the repo root):
    python deploy/deploy_contabo.py            # password from CONTABO_PASSWORD env var
    python deploy/deploy_contabo.py --password <pw>

Re-running is safe: it re-uploads HEAD and rebuilds; compose only restarts
containers whose image changed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import paramiko

HOST = "185.197.249.70"
USER = "root"
REMOTE_DIR = "/opt/cinepile"
PUBLIC_PORT = 8090
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "deploy" / ".env.production"

# Services that must NOT be disturbed. Checked before and after. These are the
# two stock apps actually running on the box (verified 2026-06-12): the main
# Kotak dashboard (gunicorn :5000) and the trading-decision preview (:5001).
PROTECTED_SERVICES = ["kotak.service", "kotak-trading-decision.service"]


def run_remote(client: paramiko.SSHClient, cmd: str, *, check: bool = True, quiet: bool = False) -> str:
    if not quiet:
        print(f"  $ {cmd}")
    _, out, err = client.exec_command(cmd, timeout=600)
    exit_code = out.channel.recv_exit_status()
    stdout, stderr = out.read().decode(), err.read().decode()
    if stdout.strip() and not quiet:
        print("    " + stdout.strip().replace("\n", "\n    "))
    if check and exit_code != 0:
        print(stderr, file=sys.stderr)
        raise RuntimeError(f"remote command failed ({exit_code}): {cmd}")
    return stdout


def protected_services_status(client: paramiko.SSHClient) -> dict[str, str]:
    status = {}
    for svc in PROTECTED_SERVICES:
        out = run_remote(client, f"systemctl is-active {svc} || true", check=False, quiet=True)
        status[svc] = out.strip()
    return status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--password", default=os.environ.get("CONTABO_PASSWORD"))
    args = ap.parse_args()
    if not args.password:
        sys.exit("Set CONTABO_PASSWORD or pass --password.")
    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE} — production secrets file is required.")

    print(f"[1/6] Connecting to {USER}@{HOST} ...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=args.password, timeout=25)

    print("[2/6] Pre-flight: protected services + port check")
    before = protected_services_status(client)
    for svc, st in before.items():
        print(f"    {svc}: {st}")
    port_in_use = run_remote(
        client, f"ss -tln | grep -q ':{PUBLIC_PORT} ' && echo BUSY || echo FREE", check=False, quiet=True
    ).strip()
    if port_in_use == "BUSY":
        # Re-deploys land here because OUR web container holds 8090 — that's fine.
        owner = run_remote(
            client,
            f"docker ps --filter publish={PUBLIC_PORT} --format '{{{{.Names}}}}' 2>/dev/null || true",
            check=False, quiet=True,
        ).strip()
        if "cinepile" not in owner:
            sys.exit(f"Port {PUBLIC_PORT} is in use by something that isn't us ({owner or 'unknown'}). Aborting.")
        print(f"    port {PUBLIC_PORT}: held by our own container ({owner}) — re-deploy")
    else:
        print(f"    port {PUBLIC_PORT}: free")

    print("[3/6] Ensuring Docker is installed")
    run_remote(client, "command -v docker >/dev/null || (curl -fsSL https://get.docker.com | sh)")
    run_remote(client, "docker --version && docker compose version")

    print("[4/6] Uploading code (git archive of HEAD)")
    tarball = REPO_ROOT / "deploy" / "cinepile-head.tar.gz"
    subprocess.run(
        ["git", "archive", "--format=tar.gz", "-o", str(tarball), "HEAD"],
        cwd=REPO_ROOT, check=True,
    )
    sftp = client.open_sftp()
    sftp.put(str(tarball), "/tmp/cinepile-head.tar.gz")
    tarball.unlink()
    # Fresh tree each deploy; backend/.env is re-uploaded right after, so
    # wiping the dir loses nothing.
    run_remote(client, f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR}")
    run_remote(client, f"tar xzf /tmp/cinepile-head.tar.gz -C {REMOTE_DIR} && rm /tmp/cinepile-head.tar.gz")

    print("[5/6] Uploading production .env")
    sftp.put(str(ENV_FILE), f"{REMOTE_DIR}/backend/.env")
    run_remote(client, f"chmod 600 {REMOTE_DIR}/backend/.env", quiet=True)
    sftp.close()

    print("[6/6] Building + starting containers (first build takes a few minutes)")
    run_remote(client, f"cd {REMOTE_DIR} && docker compose up -d --build")

    print("Waiting for the stack to come up ...")
    healthy = False
    for _ in range(30):
        time.sleep(5)
        out = run_remote(
            client, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{PUBLIC_PORT}/healthz || true",
            check=False, quiet=True,
        ).strip()
        if out == "200":
            healthy = True
            break
    after = protected_services_status(client)
    client.close()

    print()
    print("=" * 60)
    print(f"App health: {'OK — http://' + HOST + ':' + str(PUBLIC_PORT) if healthy else 'NOT RESPONDING — check `docker compose logs`'}")
    for svc in PROTECTED_SERVICES:
        flag = "OK" if after[svc] == before[svc] else "!!! CHANGED !!!"
        print(f"{svc}: before={before[svc]} after={after[svc]}  [{flag}]")
    print("=" * 60)
    if not healthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
