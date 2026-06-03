import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("Admin area (role-gated)", () => {
  test("regular user cannot reach /admin (redirect home)", async ({ page }) => {
    await loginAs(page, "user");
    await page.goto("/admin");
    // ProtectedRoute redirects unauthorized users to "/"
    await expect(page).toHaveURL(/\/$/);
  });

  test("admin dashboard renders stats + recent activity", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/admin");

    await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible();
    await expect(page.locator("text=Published titles")).toBeVisible();
    await expect(page.locator("text=Recent audit entries")).toBeVisible();
  });

  test("titles list shows seeded titles + edit links", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/admin/titles");

    await expect(page.locator("h1", { hasText: "Titles" })).toBeVisible();
    // 4 seeded titles → 4 rows
    const editButtons = page.locator('a:has-text("Edit")');
    await expect(editButtons.first()).toBeVisible();
    expect(await editButtons.count()).toBeGreaterThanOrEqual(4);
  });

  test("new title editor form renders all fields", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/admin/titles/new");

    await expect(page.locator("h1", { hasText: "New title" })).toBeVisible();
    // Form labels (rendered uppercase via CSS, source text is mixed case).
    // Use :text-is to anchor exact match — otherwise "Title" hits the nav too.
    await expect(page.locator('label:text-is("Slug")')).toBeVisible();
    await expect(page.locator('label:text-is("Type")')).toBeVisible();
    await expect(page.locator('label:text-is("Title")')).toBeVisible();
    await expect(page.locator('label:text-is("Synopsis")')).toBeVisible();
    await expect(page.locator('label:has-text("Free for unsubscribed users")')).toBeVisible();
    await expect(page.locator('button:has-text("Create")')).toBeVisible();
  });

  test("content_manager can reach /admin but not /admin/users", async ({ page }) => {
    await loginAs(page, "contentManager");
    await page.goto("/admin/titles");
    await expect(page.locator("h1", { hasText: "Titles" })).toBeVisible();

    await page.goto("/admin/users");
    // Admin-only page redirects content_manager home
    await expect(page).toHaveURL(/\/$/);
  });
});
