/**
 * Shared e2e helpers.
 *
 * Login credentials assume the dev DB has been seeded via
 *   `python scripts/seed_dev_data.py`
 * which creates:
 *   admin@anjaneya.app  / admin1234        (role: admin)
 *   cm@anjaneya.app     / cm12345          (role: content_manager)
 *   user@anjaneya.app   / user1234         (role: user)
 */
import { expect, type Page } from "@playwright/test";

export const ACCOUNTS = {
  admin: { email: "admin@anjaneya.app", password: "admin1234", profileName: "Local Admin" },
  contentManager: { email: "cm@anjaneya.app", password: "cm123456", profileName: "Content Manager" },
  user: { email: "user@anjaneya.app", password: "user1234", profileName: "Regular User" },
} as const;

export async function loginAs(page: Page, who: keyof typeof ACCOUNTS) {
  const { email, password, profileName } = ACCOUNTS[who];
  await page.goto("/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  // After successful login the router redirects to "/" (or the captured ?from=).
  // Under parallel-worker load the exact-URL wait can race the JS that flips
  // the URL bar — accept any non-/login URL as "logged in".
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20_000 });

  // ProfileGate redirects authed users without a selected profile to /profiles,
  // but the redirect fires AFTER Zustand persist finishes hydrating (one tick
  // post-mount). So Home can render briefly first; we mustn't take that brief
  // render as "logged-in and done". Wait specifically for the picker to land,
  // up to 8s — if it doesn't, assume the user already had a persisted profile
  // and we're on Home for real.
  const pickerHeading = page.locator("h1", { hasText: "Who's watching?" });
  await pickerHeading.waitFor({ timeout: 8_000 }).catch(() => null);

  if (await pickerHeading.isVisible().catch(() => false)) {
    // Wait for the profile button to render — the GET /v1/me/profiles call
    // can take several seconds on a cold Neon connection.
    const profileBtn = page.locator(`button:has-text("${profileName}")`).first();
    await profileBtn.waitFor({ timeout: 20_000 });
    await profileBtn.click();
    await page.waitForURL((url) => !url.pathname.startsWith("/profiles"), { timeout: 10_000 });
  }
}

/**
 * Wait for the home page to finish loading.
 *
 * The hero `<h1>` is the most reliable signal because:
 *   - the H1 always renders (vs row H2s which depend on data shape)
 *   - it lives outside any conditional / suspense fallback once the lazy
 *     chunk has loaded, so it appears as soon as `/v1/home` resolves
 *
 * Generous timeout: Vite dev mode compiles route chunks on first request, and
 * the React Query call has retry: 1 (so a transient cold-Neon flake adds another
 * round trip). Under parallel-worker load (matrix file + home file both
 * running) Neon + bcrypt can be slow, so we give it 45s.
 */
export async function waitForHomeContent(page: Page) {
  await expect(page.locator("main h1").first()).toBeVisible({ timeout: 45_000 });
}
