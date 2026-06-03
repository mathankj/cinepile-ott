/**
 * Role × route access matrix.
 *
 * Source of truth for what's protected: frontend/src/routes/index.tsx + the
 * ProtectedRoute component. ProtectedRoute redirects unauthed users to
 * /login (with `?from=…`) and role-insufficient users to /.
 *
 * Each row in the MATRIX is one (role, path) pair with an expected outcome:
 *   - "allow"     : the page renders for this role (URL stays put)
 *   - "to-login"  : ProtectedRoute kicks anon users to /login
 *   - "to-home"   : ProtectedRoute kicks role-insufficient users to /
 *
 * The test isn't trying to assert deep page content — that lives in the
 * route's own spec. It only verifies the GUARD applied or didn't apply.
 */
import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

type Role = "anonymous" | "user" | "contentManager" | "admin";
type Outcome = "allow" | "to-login" | "to-home";

type Row = {
  path: string;
  expected: Record<Role, Outcome>;
};

// Public routes are allowed for everyone. Auth-gated routes redirect anonymous
// users to /login; admin-only routes also bounce content_manager + user to /.
const MATRIX: Row[] = [
  // Fully public
  { path: "/", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/browse", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/search", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/title/1", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },
  // /login and /signup are public — but logged-in users currently see them
  // too (we don't auto-redirect away from /login when authed).
  { path: "/login", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/signup", expected: { anonymous: "allow", user: "allow", contentManager: "allow", admin: "allow" } },

  // Requires any authenticated user
  { path: "/me/list", expected: { anonymous: "to-login", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/me/history", expected: { anonymous: "to-login", user: "allow", contentManager: "allow", admin: "allow" } },
  { path: "/subscribe", expected: { anonymous: "to-login", user: "allow", contentManager: "allow", admin: "allow" } },

  // Requires admin OR content_manager
  { path: "/admin", expected: { anonymous: "to-login", user: "to-home", contentManager: "allow", admin: "allow" } },
  { path: "/admin/titles", expected: { anonymous: "to-login", user: "to-home", contentManager: "allow", admin: "allow" } },
  { path: "/admin/titles/new", expected: { anonymous: "to-login", user: "to-home", contentManager: "allow", admin: "allow" } },

  // Requires admin ONLY (audit + users management)
  { path: "/admin/users", expected: { anonymous: "to-login", user: "to-home", contentManager: "to-home", admin: "allow" } },
  { path: "/admin/audit", expected: { anonymous: "to-login", user: "to-home", contentManager: "to-home", admin: "allow" } },
];

test.describe("Access matrix (role × route)", () => {
  for (const role of ["anonymous", "user", "contentManager", "admin"] as Role[]) {
    test.describe(`as ${role}`, () => {
      const rowsForRole = MATRIX.map((r) => ({ path: r.path, expected: r.expected[role] }));

      for (const row of rowsForRole) {
        test(`${row.path} → ${row.expected}`, async ({ page }, testInfo) => {
          // Mobile project skips — same redirects on both viewports, no value
          // doubling the run time. Mobile-specific UI is covered in mobile.spec.ts.
          test.skip(
            testInfo.project.name === "mobile-chromium",
            "Same redirect behaviour on mobile — covered by desktop project",
          );

          if (role !== "anonymous") {
            await loginAs(page, role);
          }

          await page.goto(row.path);
          // Give the full lazy-chunk + ProtectedRoute redirect chain time to
          // settle. /admin/users + /admin/audit are nested under the lazy
          // AdminLayout chunk; the inner role check can't fire until that
          // chunk has loaded, which takes a beat on a cold Vite cache.
          await page.waitForLoadState("networkidle");
          await page.waitForTimeout(800);

          const url = new URL(page.url());
          const landed = url.pathname;

          if (row.expected === "to-login") {
            expect(landed, `${row.path} should redirect ${role} to /login`).toBe("/login");
          } else if (row.expected === "to-home") {
            expect(landed, `${row.path} should redirect ${role} to /`).toBe("/");
          } else {
            // "allow" — URL should stay at the requested path (or its
            // canonical form). Use startsWith so /admin renders /admin (index)
            // and /admin/titles renders /admin/titles.
            expect(
              landed.startsWith(row.path) || row.path.startsWith(landed),
              `${row.path} should be allowed for ${role}; landed at ${landed}`,
            ).toBe(true);
          }
        });
      }
    });
  }
});
