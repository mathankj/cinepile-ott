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
    // New floating-label form: target by id (set on each FloatingField input).
    await page.locator('#signup-name').fill("New User");
    await page.locator('#signup-email').fill(email);
    await page.locator('#signup-password').fill("supersecret9");
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("/", { timeout: 10_000 });
    // Logged in — the navbar's anonymous Sign In CTA is gone (the only one).
    // Drawer / footer copy may still contain "Sign In" strings but the link
    // with href="/login" is the canonical check.
    await expect(page.locator('a[href="/login"]:has-text("Sign In")')).toHaveCount(0);
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
