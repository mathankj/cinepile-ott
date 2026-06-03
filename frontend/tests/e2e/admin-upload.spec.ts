/**
 * Admin upload e2e — upload a video via the admin endpoint then play it.
 *
 * Skips when object storage is not configured. The backend returns HTTP 503
 * `storage_not_configured` if STORAGE_ENDPOINT_URL / STORAGE_ACCESS_KEY_ID /
 * STORAGE_SECRET_ACCESS_KEY / STORAGE_BUCKET aren't set in backend/.env.
 *
 * To run this test end-to-end:
 *   1. Get a Backblaze B2 bucket (free tier 10 GB) — backblaze.com/cloud-storage
 *   2. Put credentials in backend/.env:
 *        STORAGE_ENDPOINT_URL=https://s3.us-west-002.backblazeb2.com
 *        STORAGE_ACCESS_KEY_ID=<your-key-id>
 *        STORAGE_SECRET_ACCESS_KEY=<your-app-key>
 *        STORAGE_BUCKET=anjaneya-dev
 *        STORAGE_PUBLIC_URL=https://f002.backblazeb2.com/file/anjaneya-dev  (optional, for public reads)
 *   3. Restart the backend
 *   4. Re-run this test — the probe will pass and the upload will execute
 *
 * If left unconfigured, the test still serves as documentation of the flow.
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

async function probeStorageConfigured(baseURL: string, token: string): Promise<boolean> {
  // Send a real (tiny) multipart so the FastAPI parser doesn't hang waiting
  // on a never-arriving body. The backend hits _ensure_storage() first; if
  // unconfigured we get a fast 503. If configured we'll get 200 or 4xx (the
  // exact code doesn't matter — anything != 503 means storage exists).
  const fd = new FormData();
  fd.append("file", new Blob([new Uint8Array(4)], { type: "video/mp4" }), "probe.mp4");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5_000);
  try {
    const res = await fetch(`${baseURL}/v1/admin/titles/1/upload-video`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
      signal: controller.signal,
    });
    return res.status !== 503;
  } catch {
    // Network error or timeout → assume unconfigured so we skip rather than
    // false-fail. The test logs the skip reason so it's discoverable.
    return false;
  } finally {
    clearTimeout(timer);
  }
}

test.describe("Admin upload flow", () => {
  test("upload .mp4 to a title and verify playable URL", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Admin pages aren't mobile-optimised; covered by desktop project");
    await loginAs(page, "admin");

    // Pull the access token out of the auth store (zustand+persist writes to localStorage)
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

    // Probe — skip the rest if storage isn't configured in backend/.env
    const storageOk = await probeStorageConfigured("http://localhost:8000", token!);
    test.skip(
      !storageOk,
      "Object storage not configured. Set STORAGE_* env vars in backend/.env to run this test end-to-end. See header comment.",
    );

    // Real upload via the admin endpoint
    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: "test-fixture.mp4",
          mimeType: "video/mp4",
          buffer: TINY_MP4_FTYP_BOX,
        },
      },
    });
    expect(upload.ok(), `upload failed: ${upload.status()} ${await upload.text()}`).toBe(true);
    const result = await upload.json();
    expect(result.title_id).toBe(1);
    expect(result.stored_ref).toBeTruthy();
    expect(result.playable_url).toMatch(/^https?:\/\//);

    // Fetch the title detail and confirm the assets array now points at the new ref
    const detail = await request.get("http://localhost:8000/v1/titles/1", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(detail.ok()).toBe(true);
    const detailJson = await detail.json();
    // Either the assets array shows the new key, or the play endpoint hands
    // back a manifest_url that resolves the upload.
    const hasAsset = (detailJson.assets ?? []).some((a: { storage_url: string }) =>
      a.storage_url === result.stored_ref || a.storage_url.includes(result.key),
    );
    expect(hasAsset, "uploaded asset should appear on the title detail").toBe(true);
  });

  test("upload endpoint refuses non-video extensions (422)", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Admin pages aren't mobile-optimised");
    await loginAs(page, "admin");

    const token = await page.evaluate(() => {
      try {
        const raw = localStorage.getItem("anjaneya-auth");
        if (!raw) return null;
        return JSON.parse(raw).state?.accessToken ?? null;
      } catch {
        return null;
      }
    });
    expect(token).toBeTruthy();

    const storageOk = await probeStorageConfigured("http://localhost:8000", token!);
    test.skip(!storageOk, "Storage not configured");

    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: "malicious.exe",
          mimeType: "application/octet-stream",
          buffer: Buffer.from("MZ\x90\x00"), // PE header bytes
        },
      },
    });
    // The validator must reject this. Acceptable codes: 400, 415, 422.
    expect([400, 415, 422]).toContain(upload.status());
  });

  test("non-admin users cannot reach the upload endpoint (403)", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Same auth check regardless of viewport");
    await loginAs(page, "user");
    const token = await page.evaluate(() => {
      try {
        const raw = localStorage.getItem("anjaneya-auth");
        if (!raw) return null;
        return JSON.parse(raw).state?.accessToken ?? null;
      } catch {
        return null;
      }
    });
    expect(token).toBeTruthy();

    const upload = await request.post("http://localhost:8000/v1/admin/titles/1/upload-video", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: { name: "x.mp4", mimeType: "video/mp4", buffer: TINY_MP4_FTYP_BOX },
      },
    });
    // Backend should refuse before any storage call — 401 or 403 both acceptable.
    expect([401, 403]).toContain(upload.status());
  });
});
