import { expect, test } from "@playwright/test";
import { waitForHomeContent } from "./helpers";

// This file uses the "mobile-chromium" project automatically when run with
// `npx playwright test --project=mobile-chromium`. The default desktop project
// also runs it, but with the desktop viewport — still useful as a regression.

test.describe("Mobile (375x667 iPhone 13)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("home renders with hamburger menu", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    // The desktop <nav> exists in the DOM but is display:none on mobile.
    // toBeHidden checks actual visibility, not the presence of any class.
    await expect(page.locator('nav a:has-text("TV Shows")').first()).toBeHidden();
    // Hamburger button is visible
    await expect(page.locator('button[aria-label="Open menu"]')).toBeVisible();
  });

  test("hamburger opens the drawer with all nav links", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    await page.locator('button[aria-label="Open menu"]').click();
    // Drawer items
    await expect(page.locator('aside a:has-text("Home")')).toBeVisible();
    await expect(page.locator('aside a:has-text("TV Shows")')).toBeVisible();
    await expect(page.locator('aside a:has-text("Movies")')).toBeVisible();
    // Sign In CTA in the drawer
    await expect(page.locator('aside a:has-text("Sign In")')).toBeVisible();
  });

  test("cards row scrolls horizontally", async ({ page }) => {
    await page.goto("/");
    await waitForHomeContent(page);
    // First row's scroll container has overflow-x-auto
    const firstRowScroller = page.locator(".no-scrollbar").first();
    await expect(firstRowScroller).toBeVisible();
    const overflow = await firstRowScroller.evaluate((el) =>
      window.getComputedStyle(el).overflowX,
    );
    expect(overflow).toBe("auto");
  });
});
