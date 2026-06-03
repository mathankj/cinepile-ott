/**
 * Global setup — runs ONCE before the e2e suite.
 *
 * Neon free-tier Postgres suspends compute after 5 min idle and takes 5-10 s
 * to wake. If we let the first test be the one that triggers this, that test
 * always flakes. So we warm Neon ourselves by pinging the heaviest read
 * endpoints, then return — actual tests run against an already-warm DB.
 */
import { request } from "@playwright/test";

const BACKEND = "http://localhost:8000";
const FRONTEND = "http://localhost:5173";

export default async function globalSetup() {
  const api = await request.newContext({ timeout: 30_000 });

  // Confirm backend is up
  try {
    await api.get(`${BACKEND}/healthz`);
  } catch (e) {
    throw new Error(
      `Backend not reachable at ${BACKEND}. Start it with: ` +
        `cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`,
    );
  }
  await api.get(`${BACKEND}/readyz`);
  // Warm Neon — hits the multi-query endpoint that drives /v1/home rows
  await api.get(`${BACKEND}/v1/home`);
  await api.get(`${BACKEND}/v1/titles?page_size=10`);
  await api.dispose();

  // Confirm frontend is up
  const fe = await request.newContext({ timeout: 15_000 });
  try {
    await fe.get(FRONTEND);
  } catch (e) {
    throw new Error(`Frontend not reachable at ${FRONTEND}. Playwright's webServer should have started it.`);
  }
  await fe.dispose();
}
