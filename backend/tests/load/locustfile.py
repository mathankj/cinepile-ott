"""
Load smoke test for Anjaneya OTT backend.

Usage (headless):
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 10 --run-time 60s --headless --csv reports/load

Usage (interactive UI):
    locust -f tests/load/locustfile.py --host http://localhost:8000
    # then open http://localhost:8089

User profile:
- Most weight on public catalog reads (list + detail + search) — these are the
  hot paths an unauthenticated visitor hits when browsing.
- A smaller slice runs the full authenticated journey (signup → subscribe → play).
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
    def list_films(self) -> None:
        self.client.get("/v1/films?page=1&page_size=20", name="GET /v1/films")

    @task(2)
    def search(self) -> None:
        q = random.choice(["bunny", "sin", "tears", "test", "a"])
        self.client.get(f"/v1/films/search?q={q}", name="GET /v1/films/search")

    @task(2)
    def detail(self) -> None:
        film_id = random.randint(1, 20)
        with self.client.get(
            f"/v1/films/{film_id}", name="GET /v1/films/{id}", catch_response=True
        ) as resp:
            # 404 is expected when we miss; don't count it as a failure
            if resp.status_code in (200, 404):
                resp.success()

    @task(1)
    def plans(self) -> None:
        self.client.get("/v1/plans", name="GET /v1/plans")

    @task(1)
    def health(self) -> None:
        self.client.get("/healthz", name="GET /healthz")


class AuthedSubscriber(HttpUser):
    """A user who signs up, subscribes, and plays a film."""
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

        # Try to subscribe to monthly (no-op if no plan seeded)
        self.client.post(
            "/v1/subscriptions",
            json={"plan_code": "monthly"},
            name="POST /v1/subscriptions",
        )

    @task(3)
    def me(self) -> None:
        self.client.get("/v1/auth/me", name="GET /v1/auth/me")

    @task(3)
    def history(self) -> None:
        self.client.get("/v1/history", name="GET /v1/history")

    @task(2)
    def play_attempt(self) -> None:
        film_id = random.randint(1, 5)
        with self.client.get(
            f"/v1/films/{film_id}/play",
            name="GET /v1/films/{id}/play",
            catch_response=True,
        ) as resp:
            # Any of 200/402/404/409 is a known business outcome, not a load failure
            if resp.status_code in (200, 402, 404, 409):
                resp.success()
