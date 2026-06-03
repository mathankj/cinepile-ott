import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — spins up the Vite dev server, runs e2e specs against it.
 * The backend (uvicorn on :8000) must be started SEPARATELY before running:
 *   - Terminal A:  cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
 *   - Terminal B:  npm run test:e2e
 *
 * We don't auto-start the backend because (a) it needs the Python venv on PATH
 * and (b) tests assume the dev DB has been seeded (admin@anjaneya.app / admin1234).
 */
export default defineConfig({
  testDir: "./tests/e2e",
  // Generous timeouts — first request after idle hits Neon cold-start and
  // also triggers Vite's per-route lazy chunk build.
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false, // serial — tests share login state via the seed
  // Cap workers locally: the dev Vite server + Neon free-tier + bcrypt can't
  // service 6 simultaneous workers (login bcrypt alone is ~500 ms × N). One CPU
  // worker on local keeps the suite fast enough (~3 min) without flakiness.
  workers: process.env.CI ? undefined : 2,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html"]] : [["list"], ["html", { open: "never" }]],
  globalSetup: "./tests/e2e/global-setup.ts",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    // Mobile uses Chromium (Pixel 5 metrics) instead of iPhone 13 — iPhone 13's device
    // descriptor defaults to WebKit and we don't ship the WebKit binary by default.
    // The viewport + user-agent are what trigger responsive breakpoints anyway.
    { name: "mobile-chromium", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    stdout: "ignore",
    stderr: "pipe",
    timeout: 30_000,
  },
});
