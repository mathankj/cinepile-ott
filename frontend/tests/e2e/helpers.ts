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
  admin: { email: "admin@anjaneya.app", password: "admin1234" },
  contentManager: { email: "cm@anjaneya.app", password: "cm123456" },
  user: { email: "user@anjaneya.app", password: "user1234" },
} as const;

export async function loginAs(page: Page, who: keyof typeof ACCOUNTS) {
  const { email, password } = ACCOUNTS[who];
  await page.goto("/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  // After successful login the router redirects to "/"
  await page.waitForURL("/", { timeout: 10_000 });
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
 * round trip).
 */
export async function waitForHomeContent(page: Page) {
  await expect(page.locator("main h1").first()).toBeVisible({ timeout: 30_000 });
}
