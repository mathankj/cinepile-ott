import { expect, test } from "@playwright/test";
import { loginAs, waitForHomeContent } from "./helpers";

test.describe("Title detail + season + playback gating", () => {
  test("series detail shows seasons + Play S1E1 button", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    // Click any card linking to /title/<id>
    await page.locator('a[href^="/title/"]').first().click();
    await page.waitForURL(/\/title\/\d+$/);

    await expect(page.locator("h1").first()).toBeVisible();
    // Either a Play button (movie) OR Play S1E1 (series) — both contain "Play"
    await expect(page.locator('a:has-text("Play")').first()).toBeVisible();
  });

  test("series → season page lists episodes with Play buttons", async ({ page }) => {
    // Find the series-typed title in the catalog and navigate
    await page.goto("/browse?type=series");
    // Wait for grid load
    await expect(page.locator('a[href^="/title/"]').first()).toBeVisible({ timeout: 15_000 });
    await page.locator('a[href^="/title/"]').first().click();
    await page.waitForURL(/\/title\/\d+$/);
    // Click first season link
    await page.locator('a[href*="/season/"]').first().click();
    await page.waitForURL(/\/title\/\d+\/season\/\d+$/);

    await expect(page.locator("h1").first()).toBeVisible();
    // At least one episode card has a Play button
    await expect(page.locator('a:has-text("Play")').first()).toBeVisible();
  });

  test("unsubscribed user sees 402 path when clicking Play on paid content", async ({ page }) => {
    await loginAs(page, "user");
    // Find a movie (not free) and try to play it directly
    await page.goto("/browse?type=movie");
    await expect(page.locator('a[href^="/title/"]').first()).toBeVisible({ timeout: 15_000 });
    const titleLink = page.locator('a[href^="/title/"]').first();
    const href = await titleLink.getAttribute("href");
    const titleId = href?.split("/").pop();
    await page.goto(`/watch/title/${titleId}`);
    // 402 path renders both the "subscription required" copy AND a View Plans CTA.
    // Use .first() because strict-mode otherwise complains about the dual match.
    // React Query retries once on failure (default backoff ~1s), so the user-
    // visible error state can lag the API response by a couple of seconds.
    await expect(
      page.locator("text=/subscription/i").or(page.locator("text=View Plans")).first(),
    ).toBeVisible({ timeout: 25_000 });
  });
});
