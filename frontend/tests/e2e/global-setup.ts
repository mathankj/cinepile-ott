/**
 * Global setup — runs ONCE before the e2e suite.
 *
 * Two cold-start problems we solve before any test runs:
 *
 *   1. Neon free-tier Postgres suspends compute after 5 min idle and takes
 *      5-10 s to wake. We ping the heaviest read endpoints so the DB is
 *      already hot when test #1 starts.
 *
 *   2. Vite dev server transforms lazy route chunks on-demand the FIRST time
 *      they're requested. With 6 parallel workers, six tests can race to be
 *      the first request for /title/:id (or any other lazy route) — most of
 *      them time out. We pre-walk the key routes with a real browser so
 *      chunks land in Vite's transform cache before workers spread out.
 */
import { chromium, request } from "@playwright/test";

const BACKEND = "http://localhost:8000";
const FRONTEND = "http://localhost:5173";

export default async function globalSetup() {
  const api = await request.newContext({ timeout: 30_000 });
  try {
    await api.get(`${BACKEND}/healthz`);
  } catch (e) {
    throw new Error(
      `Backend not reachable at ${BACKEND}. Start it with: ` +
        `cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`,
    );
  }
  await api.get(`${BACKEND}/readyz`);
  await api.get(`${BACKEND}/v1/home`);
  await api.get(`${BACKEND}/v1/titles?page_size=10`);
  await api.dispose();

  // Warm Vite chunks for every lazy route the suite hits. We visit each URL
  // and wait for networkidle so React Query + lazy chunk are fully resolved
  // before we move on.
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const warmRoutes = ["/", "/login", "/signup", "/search", "/browse?type=movie", "/browse?type=series"];
  for (const url of warmRoutes) {
    try {
      await page.goto(`${FRONTEND}${url}`, { waitUntil: "networkidle", timeout: 30_000 });
    } catch {
      // Best-effort warm-up; one failed route shouldn't block the suite.
    }
  }
  await browser.close();
}
