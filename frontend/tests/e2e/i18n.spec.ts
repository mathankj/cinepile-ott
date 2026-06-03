/**
 * i18n e2e — language picker swaps UI strings and persists across reloads.
 *
 * We don't test EVERY translated string (that would be brittle and slow); we
 * pick one HIGH-SIGNAL string per language (the navbar's "Sign In" / "साइन इन"
 * / "உள்நுழைய") and verify that the swap actually happened. Other strings
 * are covered implicitly — they all read from the same i18next instance.
 */
import { expect, test } from "@playwright/test";
import { waitForHomeContent } from "./helpers";

test.describe("i18n", () => {
  test("desktop language picker switches UI to Hindi and persists across reload", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Language picker lives in the desktop navbar");

    await page.goto("/");
    await waitForHomeContent(page);

    // English baseline — the anonymous Sign In CTA is in English.
    await expect(page.locator('a[href="/login"]:has-text("Sign In")').first()).toBeVisible();

    // Open the language picker and pick Hindi
    await page.locator('button[aria-label="Language"]').click();
    await page.locator('button:has-text("हिन्दी")').click();

    // The Sign In CTA flips to its Hindi translation. Same href, new text.
    await expect(page.locator('a[href="/login"]:has-text("साइन इन")').first()).toBeVisible({ timeout: 5_000 });

    // Reload — language survives.
    await page.reload();
    await waitForHomeContent(page);
    await expect(page.locator('a[href="/login"]:has-text("साइन इन")').first()).toBeVisible({ timeout: 5_000 });
  });

  test("switching to Tamil updates the navbar Home link", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Language picker lives in the desktop navbar");

    await page.goto("/");
    await waitForHomeContent(page);

    await page.locator('button[aria-label="Language"]').click();
    await page.locator('button:has-text("தமிழ்")').click();

    // Navbar "Home" → "முகப்பு" in Tamil
    await expect(page.locator('nav a:has-text("முகப்பு")').first()).toBeVisible({ timeout: 5_000 });

    // Reset to English for the next test to start clean.
    await page.locator('button[aria-label="Language"]').click();
    await page.locator('button:has-text("English")').click();
  });
});
