import { expect, test } from "@playwright/test";

test.describe("Browse + Search", () => {
  test("browse type=movie filter shows movies only", async ({ page }) => {
    await page.goto("/browse?type=movie");
    await expect(page.locator("h1", { hasText: "Movies" })).toBeVisible();
    await expect(page.locator('a[href^="/title/"]').first()).toBeVisible({ timeout: 15_000 });
  });

  test("browse type=series filter shows series only", async ({ page }) => {
    await page.goto("/browse?type=series");
    await expect(page.locator("h1", { hasText: "TV Shows" })).toBeVisible();
  });

  test("genre dropdown is populated from API", async ({ page }) => {
    await page.goto("/browse");
    // /browse has three filter selects now: Type / Genre / Sort. Target Genre
    // explicitly by its aria-label (the type filter has 3 options, not 6).
    const genreSelect = page.locator('select[aria-label="Genre"]');
    await expect(genreSelect).toBeVisible();
    await expect(genreSelect.locator("option")).toHaveCount(6, { timeout: 15_000 });
  });

  test("search finds bunny movie", async ({ page }) => {
    await page.goto("/search");
    await page.locator('input[type="search"]').fill("bunny");
    // Debounced 300ms; wait for the result
    await expect(page.locator("text=Big Buck Bunny").first()).toBeVisible({ timeout: 8_000 });
  });

  test("search rejects 1-char query (no results)", async ({ page }) => {
    await page.goto("/search");
    await page.locator('input[type="search"]').fill("b");
    // We render a hint, not a results grid
    await expect(page.locator("text=/Type at least 2 characters/i")).toBeVisible();
  });

  test("search literal wildcard returns no matches (LIKE escape works)", async ({ page }) => {
    await page.goto("/search");
    // Use 2+ chars so the page's "min 2 characters" guard doesn't short-circuit.
    // The double-% probes the backend's LIKE-escape — should NOT match all titles.
    await page.locator('input[type="search"]').fill("%%");
    // No literal match for "%%" exists in seeded titles, so the result grid is empty
    // and the page renders the empty-state copy.
    await expect(page.locator("text=/No matches/i")).toBeVisible({ timeout: 8_000 });
  });
});
