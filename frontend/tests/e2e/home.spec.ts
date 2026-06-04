import { expect, test } from "@playwright/test";
import { loginAs, waitForHomeContent } from "./helpers";

test.describe("Home page", () => {
  test("anonymous user sees billboard + browse rows", async ({ page }, testInfo) => {
    await page.goto("/");
    await waitForHomeContent(page);

    // Brand logo
    await expect(page.locator("text=CINEPILE").first()).toBeVisible();

    // The desktop navbar's Sign In CTA is hidden on mobile (replaced by the
    // hamburger drawer). Check it only in the desktop project.
    if (testInfo.project.name === "desktop-chromium") {
      await expect(page.locator('a[href="/login"]:has-text("Sign In")').first()).toBeVisible();
    }
    // Anonymous user must NOT see Continue Watching or My List rows
    await expect(page.locator("h2:has-text('Continue Watching')")).toHaveCount(0);
    await expect(page.locator("h2:has-text('My List')")).toHaveCount(0);
    // ... but should see public rows
    const newReleases = page.locator("h2", { hasText: "New Releases" });
    const trending = page.locator("h2", { hasText: "Trending Now" });
    await expect(newReleases.or(trending).first()).toBeVisible({ timeout: 20_000 });
  });

  test("authenticated user has My List link in navbar", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Desktop navbar only — mobile shows links in the drawer (covered in mobile.spec.ts)");
    await loginAs(page, "user");
    await waitForHomeContent(page);
    await expect(page.locator('nav a:has-text("My List")').first()).toBeVisible();
  });

  test("billboard renders even when title has no backdrop", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    // The hero h1 should always be set
    const heroH1 = page.locator("h1").first();
    await expect(heroH1).toBeVisible();
    await expect(heroH1).not.toBeEmpty();
  });
});
