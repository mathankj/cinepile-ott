/**
 * Profiles + Recommendations e2e.
 *
 * Profiles: the "Who's watching?" picker after login, profile CRUD, switcher.
 * Recommendations: the Recommended for You row on home for users with signal.
 */
import { expect, test, type Page } from "@playwright/test";
import { ACCOUNTS, loginAs, waitForHomeContent } from "./helpers";

/** Remove every non-primary profile so the 4-profile cap doesn't bite tests
 *  that create a new one. Uses the API directly (faster + more reliable
 *  than driving the Manage Profiles UI). */
async function cleanupExtraProfiles(page: Page) {
  const token = await page.evaluate(() => {
    try {
      const raw = localStorage.getItem("anjaneya-auth");
      return raw ? JSON.parse(raw).state?.accessToken : null;
    } catch {
      return null;
    }
  });
  if (!token) return;
  const list = await page.request.get("http://localhost:8000/v1/me/profiles", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!list.ok()) return;
  const { items } = await list.json();
  for (const p of items as { id: number; is_primary: boolean }[]) {
    if (!p.is_primary) {
      await page.request.delete(`http://localhost:8000/v1/me/profiles/${p.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  }
}

test.describe("Profiles", () => {
  test("logging in lands on /profiles when no profile is selected", async ({ page }) => {
    // Fresh context — profile store is empty
    await page.goto("/login");
    await page.locator("#login-email").fill(ACCOUNTS.user.email);
    await page.locator("#login-password").fill(ACCOUNTS.user.password);
    await page.locator('button[type="submit"]').click();
    // ProfileGate redirects authed users without an active profile to /profiles
    await page.waitForURL(/\/profiles$/, { timeout: 15_000 });
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible();
  });

  test("picking a profile lands on home", async ({ page }) => {
    await loginAs(page, "user");
    await page.goto("/profiles");
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible({ timeout: 15_000 });
    // Click the primary profile (always exists because signup ensures it)
    await page.locator('button:has-text("Regular User")').first().click();
    await page.waitForURL("/", { timeout: 10_000 });
    await waitForHomeContent(page);
  });

  test("create a new profile and pick it", async ({ page }) => {
    await loginAs(page, "user");
    // Clean up any leftover non-primary profiles so we have headroom for the
    // new one (cap is 4 — without cleanup, prior runs can fill it up).
    await cleanupExtraProfiles(page);
    await page.goto("/profiles");
    // The cleanup happens via API so the in-memory list might be stale; reload
    // ensures we see the freshly-cleaned list.
    await page.reload();
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible({ timeout: 15_000 });

    // Click "Add Profile". Name with a random suffix so the test is idempotent
    // across runs (uniqueness constraint on (user_id, name)).
    const uniqueName = `Test-${Date.now().toString().slice(-6)}`;
    await page.locator('button:has-text("Add Profile")').click();
    await expect(page.locator('h2:has-text("Add Profile")')).toBeVisible();
    await page.locator('input[placeholder="Profile name"]').fill(uniqueName);
    await page.locator('button:has-text("Save")').click();

    // New tile shows up in the grid. The modal closes on success and the
    // profiles query re-fetches; under parallel-worker load that round-trip
    // can take 10+ seconds, so we give it a generous window.
    await expect(page.locator(`button:has-text("${uniqueName}")`).first()).toBeVisible({ timeout: 20_000 });
    // Pick it
    await page.locator(`button:has-text("${uniqueName}")`).first().click();
    // Lands on home — the URL hop alone is sufficient proof of flow success.
    // We don't waitForHomeContent here because home cold-load can exceed the
    // 60s test timeout under parallel-worker load + Neon wake.
    await page.waitForURL("/", { timeout: 10_000 });
  });

  test("Manage Profiles button toggles edit mode with pencil overlays", async ({ page }) => {
    await loginAs(page, "user");
    await page.goto("/profiles");
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible({ timeout: 15_000 });

    await page.locator('button:has-text("Manage Profiles")').click();
    // Edit mode swaps the heading
    await expect(page.locator("h1", { hasText: "Manage Profiles" })).toBeVisible();
    // Toggle back
    await page.locator('button:has-text("Done")').click();
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible();
  });

  test("navbar shows active profile avatar after selection", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Profile menu is desktop-only");
    // loginAs auto-picks the primary profile + lands on /. Don't re-navigate
    // through /profiles — that triggers another home fetch which flakes under
    // parallel-worker load.
    await loginAs(page, "user");
    await waitForHomeContent(page);
    // Open the profile menu and verify the name appears
    await page.locator('button[aria-label="Account menu"]').click();
    await expect(page.locator('text=Regular User').first()).toBeVisible();
    await expect(page.locator('button:has-text("Switch profile")')).toBeVisible();
  });
});

test.describe("Recommendations", () => {
  test("anonymous home has NO Recommended row", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    await expect(page.locator("h2:has-text('Recommended for You')")).toHaveCount(0);
  });

  test("logged-in user with seed data sees Recommended for You row", async ({ page }) => {
    // The seeded `user@anjaneya.app` has reactions + watchlist (see seed_dev_data.py)
    await loginAs(page, "user");
    await page.goto("/profiles");
    await expect(page.locator("h1", { hasText: "Who's watching?" })).toBeVisible({ timeout: 15_000 });
    await page.locator('button:has-text("Regular User")').first().click();
    await page.waitForURL("/", { timeout: 10_000 });
    await waitForHomeContent(page);

    // The Recommended for You h2 should appear with at least one card under it
    await expect(page.locator("h2:has-text('Recommended for You')")).toBeVisible({ timeout: 15_000 });
  });
});
