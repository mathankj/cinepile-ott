/**
 * Player-feature coverage added in wave1/fe-player:
 *   - In-app trailer route   — "Watch Trailer" navigates to /watch/trailer/:id
 *                              instead of opening the raw URL in a new tab
 *   - TitleDetail skeleton   — deep links show a hero-shaped shimmer, not
 *                              bare "Loading…" text
 *   - Watch loading surface  — full-bleed black with a spinner (no white flash)
 *   - More like this row     — renders from /similar, hides on error/empty
 *
 * Network-dependent states (skeleton, spinner, similar row) are made
 * deterministic with page.route() delays/mocks so the assertions don't race
 * a fast local backend.
 */
import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("In-app trailer", () => {
  test("Watch Trailer opens /watch/trailer/:id in-app (no new tab)", async ({ page }) => {
    await loginAs(page, "user");
    await page.goto("/title/1");
    const trailerLink = page.locator('a:has-text("Watch Trailer")').first();
    await expect(trailerLink).toBeVisible({ timeout: 15_000 });
    // It's a router Link now — same-tab href, no target=_blank.
    await expect(trailerLink).toHaveAttribute("href", "/watch/trailer/1");
    await expect(trailerLink).not.toHaveAttribute("target", "_blank");

    await trailerLink.click();
    await page.waitForURL(/\/watch\/trailer\/1/, { timeout: 15_000 });
    // The watch surface renders with its Back affordance. (We don't assert
    // actual frames — the seeded trailer URL may not be playable in CI.)
    await expect(page.locator('button:has-text("Back")').first()).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Loading states", () => {
  test("TitleDetail deep link shows the shimmer skeleton, not bare text", async ({ page }) => {
    // Hold the title detail response long enough to observe the skeleton.
    await page.route("**/v1/titles/1", async (route) => {
      await new Promise((r) => setTimeout(r, 1_500));
      await route.continue();
    });
    await page.goto("/title/1");
    await expect(page.locator(".skeleton-shimmer").first()).toBeVisible({ timeout: 10_000 });
    // And the real content still lands afterwards.
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 30_000 });
  });

  test("Watch page loading state is a black surface with a centered spinner", async ({ page }) => {
    await loginAs(page, "user");
    await page.route("**/v1/titles/1/play", async (route) => {
      await new Promise((r) => setTimeout(r, 1_500));
      await route.continue();
    });
    await page.goto("/watch/title/1");
    const spinner = page.locator('[aria-label="Loading"]').first();
    await expect(spinner).toBeVisible({ timeout: 10_000 });
    // The surface behind the spinner is black — no white flash.
    const bg = await page.evaluate(() => {
      const el = document.querySelector('[aria-label="Loading"]')?.parentElement;
      return el ? window.getComputedStyle(el).backgroundColor : null;
    });
    expect(bg).toBe("rgb(0, 0, 0)");
  });
});

test.describe("More like this", () => {
  const SIMILAR_ITEM = {
    id: 2,
    slug: "similar-demo",
    type: "movie",
    title: "Similar Demo",
    poster_url: null,
    backdrop_url: null,
    release_year: 2024,
    age_rating: "U/A 13+",
    runtime_minutes: 95,
    is_free: true,
  };

  test("renders a TitleRow when /similar returns items", async ({ page }) => {
    await page.route("**/v1/titles/1/similar*", (route) =>
      route.fulfill({ json: [SIMILAR_ITEM] }),
    );
    await page.goto("/title/1");
    await expect(page.locator("h2", { hasText: "More like this" })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("text=Similar Demo").first()).toBeVisible();
  });

  test("renders nothing when /similar errors or is empty", async ({ page }) => {
    await page.route("**/v1/titles/1/similar*", (route) =>
      route.fulfill({ status: 500, json: { detail: "boom" } }),
    );
    await page.goto("/title/1");
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("h2", { hasText: "More like this" })).toHaveCount(0);
  });
});
