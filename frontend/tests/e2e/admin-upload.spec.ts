/**
 * Admin upload e2e — upload a real video file to the admin endpoint and verify
 * the playable URL it returns is reachable.
 *
 * Storage IS configured for this dev environment (see backend/.env STORAGE_*).
 * If you take this code to a different machine without storage credentials,
 * these tests will fail with a 503 — that's intentional. Configure storage or
 * the suite breaks. We don't paper over real infrastructure problems.
 *
 * What the suite verifies:
 *   1. admin can upload a .mp4, gets back a presigned playable URL
 *   2. the playable URL actually serves the bytes (HEAD/GET succeeds)
 *   3. the upload attaches as an asset on the title
 *   4. wrong-MIME extensions are rejected before storage is touched
 *   5. non-admin users cannot reach the endpoint
 */
import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

// Minimal valid MP4 — a 32-byte ftyp box. The backend validates extension +
// MIME and size only; it does not parse the container. We don't ship a real
// MP4 file because we don't want a binary in the repo.
const TINY_MP4_FTYP_BOX = Buffer.from([
  0x00, 0x00, 0x00, 0x20, // box size = 32
  0x66, 0x74, 0x79, 0x70, // "ftyp"
  0x69, 0x73, 0x6f, 0x6d, // major brand "isom"
  0x00, 0x00, 0x02, 0x00, // minor version
  0x69, 0x73, 0x6f, 0x6d, // compatible brand "isom"
  0x69, 0x73, 0x6f, 0x32, // compatible brand "iso2"
  0x61, 0x76, 0x63, 0x31, // compatible brand "avc1"
  0x6d, 0x70, 0x34, 0x31, // compatible brand "mp41"
]);

/** Pull the auth token out of zustand+persist's localStorage entry. */
async function getToken(page: import("@playwright/test").Page): Promise<string> {
  const token = await page.evaluate(() => {
    try {
      const raw = localStorage.getItem("anjaneya-auth");
      if (!raw) return null;
      return JSON.parse(raw).state?.accessToken ?? null;
    } catch {
      return null;
    }
  });
  expect(token, "auth token must be present after login").toBeTruthy();
  return token!;
}

test.describe("Admin upload flow", () => {
  test("upload .mp4 to a title and verify playable URL is reachable", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Admin pages are desktop-only; covered there");
    await loginAs(page, "admin");
    const token = await getToken(page);

    // Real upload — Playwright's APIRequestContext multipart streams just like
    // Python requests + boto3 does. 60s timeout because B2 cold connections
    // can take 5-10 s on the first hit of a session.
    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: "e2e-upload.mp4",
          mimeType: "video/mp4",
          buffer: TINY_MP4_FTYP_BOX,
        },
      },
      timeout: 60_000,
    });
    expect(upload.ok(), `upload failed: ${upload.status()} ${await upload.text()}`).toBe(true);

    const result = await upload.json();
    expect(result.title_id).toBe(1);
    expect(result.stored_ref).toBeTruthy();
    expect(result.playable_url).toMatch(/^https?:\/\//);

    // The playable URL should be a presigned B2 URL — fetch it and confirm
    // the storage actually has the bytes we uploaded.
    const fetched = await request.get(result.playable_url, { timeout: 30_000 });
    expect(fetched.ok(), `playable URL not reachable: ${fetched.status()}`).toBe(true);
    const body = await fetched.body();
    expect(body.length).toBe(TINY_MP4_FTYP_BOX.length);

    // Confirm the title detail now shows the uploaded asset.
    const detail = await request.get("http://localhost:8000/v1/titles/1", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(detail.ok()).toBe(true);
    const detailJson = await detail.json();
    const hasAsset = (detailJson.assets ?? []).some((a: { storage_url: string }) =>
      a.storage_url === result.stored_ref || a.storage_url.includes(result.key),
    );
    expect(hasAsset, "uploaded asset should appear on the title detail").toBe(true);
  });

  test("upload endpoint rejects non-video extensions", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Same validator regardless of viewport");
    await loginAs(page, "admin");
    const token = await getToken(page);

    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: "malicious.exe",
          mimeType: "application/octet-stream",
          buffer: Buffer.from("MZ\x90\x00"), // PE header bytes
        },
      },
      timeout: 30_000,
    });
    expect([400, 415, 422]).toContain(upload.status());
  });

  test("non-admin users cannot reach the upload endpoint", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Same auth check regardless of viewport");
    await loginAs(page, "user");
    const token = await getToken(page);

    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: { name: "x.mp4", mimeType: "video/mp4", buffer: TINY_MP4_FTYP_BOX },
      },
      timeout: 30_000,
    });
    expect([401, 403]).toContain(upload.status());
  });
});
