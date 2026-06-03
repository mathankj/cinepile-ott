"""
Load smoke test for Anjaneya OTT backend (V1.5 surface).

Usage (headless):
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 10 --run-time 60s --headless --csv reports/load

Usage (interactive UI):
    locust -f tests/load/locustfile.py --host http://localhost:8000
    # then open http://localhost:8089

User profile:
- Most weight on public catalog reads (list + detail + search + home) — the
  hot paths an unauthenticated visitor hits when browsing.
- A smaller slice runs the full authenticated journey (signup → subscribe →
  /me → history → play).
"""
from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def _email() -> str:
    # Use a real-looking TLD; email-validator rejects reserved .test / .invalid
    return "u_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12)) + "@loadtest.dev"


class CatalogBrowser(HttpUser):
    """Unauthenticated visitor browsing the catalog."""
    wait_time = between(0.5, 2.0)
    weight = 4  # 4x as many of these as authenticated users

    @task(5)
    def list_titles(self) -> None:
        self.client.get("/v1/titles?page=1&page_size=20", name="GET /v1/titles")

    @task(3)
    def home(self) -> None:
        self.client.get("/v1/home", name="GET /v1/home")

    @task(2)
    def search(self) -> None:
        q = random.choice(["bunny", "sin", "tears", "chronicles", "anjaneya"])
        self.client.get(f"/v1/titles/search?q={q}", name="GET /v1/titles/search")

    @task(2)
    def detail(self) -> None:
        title_id = random.randint(1, 10)
        with self.client.get(
            f"/v1/titles/{title_id}", name="GET /v1/titles/{id}", catch_response=True
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()

    @task(1)
    def coming_soon(self) -> None:
        self.client.get("/v1/titles/coming-soon", name="GET /v1/titles/coming-soon")

    @task(1)
    def plans(self) -> None:
        self.client.get("/v1/plans", name="GET /v1/plans")

    @task(1)
    def healthz(self) -> None:
        self.client.get("/healthz", name="GET /healthz")


class AuthedViewer(HttpUser):
    """A user who signs up, subscribes (mock or real), and browses authed."""
    wait_time = between(1, 3)
    weight = 1

    def on_start(self) -> None:
        email = _email()
        r = self.client.post(
            "/v1/auth/signup",
            json={"email": email, "password": "loadtest1234", "full_name": "Load Tester"},
            name="POST /v1/auth/signup",
        )
        if r.status_code != 201:
            self.environment.runner.quit()
            return
        token = r.json()["tokens"]["access_token"]
        self.client.headers["Authorization"] = f"Bearer {token}"
        # Try to subscribe — only succeeds in mock mode; real mode 502s in load
        # context because no checkout completes. Catch both as expected outcomes.
        with self.client.post(
            "/v1/subscriptions",
            json={"plan_code": "monthly"},
            name="POST /v1/subscriptions",
            catch_response=True,
        ) as resp:
            if resp.status_code in (201, 502, 409):
                resp.success()

    @task(4)
    def me(self) -> None:
        self.client.get("/v1/auth/me", name="GET /v1/auth/me")

    @task(3)
    def home_authed(self) -> None:
        self.client.get("/v1/home", name="GET /v1/home (authed)")

    @task(3)
    def continue_watching(self) -> None:
        self.client.get("/v1/me/continue-watching", name="GET /v1/me/continue-watching")

    @task(2)
    def my_list(self) -> None:
        self.client.get("/v1/me/list", name="GET /v1/me/list")

    @task(2)
    def play_attempt(self) -> None:
        title_id = random.randint(1, 5)
        with self.client.get(
            f"/v1/titles/{title_id}/play",
            name="GET /v1/titles/{id}/play",
            catch_response=True,
        ) as resp:
            # 200=play, 402=no sub (expected for new users), 404=no title, 409=type mismatch
            if resp.status_code in (200, 402, 404, 409):
                resp.success()
