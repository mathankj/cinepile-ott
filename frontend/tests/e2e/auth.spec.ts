import { expect, test } from "@playwright/test";
import { ACCOUNTS, loginAs } from "./helpers";

test.describe("Auth flow", () => {
  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.locator('input[type="email"]').fill(ACCOUNTS.user.email);
    await page.locator('input[type="password"]').fill("wrong-pass-9");
    await page.locator('button[type="submit"]').click();
    await expect(page.locator("text=/Email or password is incorrect/i")).toBeVisible();
  });

  test("admin login redirects to home and exposes Admin link", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Profile avatar lives in the desktop header; mobile uses the drawer");
    await loginAs(page, "admin");
    // After login we're on /
    await expect(page).toHaveURL(/\/$/);
    // Profile menu has the Admin link (we click the profile avatar first)
    await page.locator('header button:has(span)').first().click();
    await expect(page.locator('a[href="/admin"]:has-text("Admin")')).toBeVisible();
  });

  test("signup with valid input creates account + logs user in", async ({ page }) => {
    const ts = Date.now();
    const email = `new-${ts}@anjaneya.app`;
    await page.goto("/signup");
    await page.locator('input[placeholder*="name" i]').fill("New User");
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').fill("supersecret9");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("/", { timeout: 10_000 });
    // Logged in — Sign In button is gone
    await expect(page.locator("text=Sign In")).toHaveCount(0);
  });

  test("logout via profile menu clears session", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Profile menu lives in the desktop header; mobile logout is in the drawer");
    await loginAs(page, "user");
    await page.locator('header button:has(span)').first().click();
    await page.locator('button:has-text("Sign out")').click();
    await page.waitForURL("/", { timeout: 5_000 });
    await expect(page.locator("text=Sign In").first()).toBeVisible();
  });
});
