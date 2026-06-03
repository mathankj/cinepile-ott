/**
 * Admin subtitle (.vtt) upload e2e.
 *
 * Flow under test:
 *   1. Admin uploads en.vtt to title 1 → backend stores in B2 + DB row
 *   2. Subtitle appears in /v1/titles/1 detail's subtitle_tracks
 *   3. The presigned URL the upload returned actually serves the .vtt bytes
 *   4. Re-uploading the same language replaces (upsert by lang)
 *   5. DELETE /v1/admin/subtitles/:id removes the track
 *   6. Auth: non-admin gets 401/403
 *   7. Validator: non-.vtt extension is rejected
 */
import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

const SAMPLE_VTT = Buffer.from(
  "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nE2E sample subtitle\n",
  "utf-8",
);

async function getToken(page: import("@playwright/test").Page): Promise<string> {
  const token = await page.evaluate(() => {
    try {
      const raw = localStorage.getItem("anjaneya-auth");
      return raw ? JSON.parse(raw).state?.accessToken : null;
    } catch {
      return null;
    }
  });
  expect(token, "auth token must be present after login").toBeTruthy();
  return token!;
}

async function deleteAllSubtitlesForTitle(
  request: import("@playwright/test").APIRequestContext,
  token: string,
  titleId: number,
) {
  const r = await request.get(`http://localhost:8000/v1/titles/${titleId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok()) return;
  const detail = await r.json();
  for (const t of detail.subtitle_tracks ?? []) {
    if (t.id) {
      await request.delete(`http://localhost:8000/v1/admin/subtitles/${t.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  }
}

test.describe("Admin subtitle upload", () => {
  test("upload .vtt → appears on title detail → presigned URL serves the bytes", async ({
    page,
    request,
  }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "Admin pages are desktop-only");
    await loginAs(page, "admin");
    const token = await getToken(page);

    // Start clean — remove any previously-uploaded EN sub on title 1.
    await deleteAllSubtitlesForTitle(request, token, 1);

    const res = await request.post("http://localhost:8000/v1/admin/titles/1/subtitles", {
      headers: { Authorization: `Bearer ${token}` },
      params: { language: "en", kind: "cc", label: "English [CC]" },
      multipart: {
        file: { name: "en.vtt", mimeType: "text/vtt", buffer: SAMPLE_VTT },
      },
      timeout: 60_000,
    });
    expect(res.ok(), `upload failed: ${res.status()} ${await res.text()}`).toBe(true);
    const result = await res.json();
    expect(result.language).toBe("en");
    expect(result.kind).toBe("cc");
    expect(result.label).toBe("English [CC]");
    expect(result.playable_url).toMatch(/^https?:\/\//);

    // The playable URL serves the bytes we uploaded.
    const fetched = await request.get(result.playable_url, { timeout: 30_000 });
    expect(fetched.ok()).toBe(true);
    const body = await fetched.body();
    expect(body.length).toBe(SAMPLE_VTT.length);
    expect(body.toString("utf-8")).toContain("E2E sample subtitle");

    // Title detail now reflects the track.
    const detail = await request.get("http://localhost:8000/v1/titles/1", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const detailJson = await detail.json();
    const tracks = detailJson.subtitle_tracks ?? [];
    expect(tracks.some((t: { language: string }) => t.language === "en")).toBe(true);

    // Cleanup so the next run starts clean.
    await deleteAllSubtitlesForTitle(request, token, 1);
  });

  test("re-uploading same language replaces previous (upsert behaviour)", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "API-only test");
    await loginAs(page, "admin");
    const token = await getToken(page);
    await deleteAllSubtitlesForTitle(request, token, 1);

    // First upload
    const a = await request.post("http://localhost:8000/v1/admin/titles/1/subtitles", {
      headers: { Authorization: `Bearer ${token}` },
      params: { language: "en", kind: "cc", label: "v1" },
      multipart: { file: { name: "en.vtt", mimeType: "text/vtt", buffer: SAMPLE_VTT } },
    });
    expect(a.ok()).toBe(true);

    // Second upload — same language — should replace the first
    const b = await request.post("http://localhost:8000/v1/admin/titles/1/subtitles", {
      headers: { Authorization: `Bearer ${token}` },
      params: { language: "en", kind: "subtitle", label: "v2" },
      multipart: { file: { name: "en.vtt", mimeType: "text/vtt", buffer: SAMPLE_VTT } },
    });
    expect(b.ok()).toBe(true);

    // After the upsert, exactly ONE EN subtitle remains, with the v2 label.
    const detail = await request.get("http://localhost:8000/v1/titles/1", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tracks: { language: string; label: string | null; kind: string }[] = (await detail.json()).subtitle_tracks ?? [];
    const en = tracks.filter((t) => t.language === "en");
    expect(en).toHaveLength(1);
    expect(en[0].label).toBe("v2");
    expect(en[0].kind).toBe("subtitle");

    await deleteAllSubtitlesForTitle(request, token, 1);
  });

  test("rejects non-.vtt files", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "API-only test");
    await loginAs(page, "admin");
    const token = await getToken(page);

    const res = await request.post("http://localhost:8000/v1/admin/titles/1/subtitles", {
      headers: { Authorization: `Bearer ${token}` },
      params: { language: "en", kind: "cc" },
      multipart: { file: { name: "evil.srt", mimeType: "text/plain", buffer: Buffer.from("1\n00:00:00,000\n") } },
    });
    expect([400, 415, 422]).toContain(res.status());
  });

  test("non-admin user is rejected", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name === "mobile-chromium", "API-only test");
    await loginAs(page, "user");
    const token = await getToken(page);

    const res = await request.post("http://localhost:8000/v1/admin/titles/1/subtitles", {
      headers: { Authorization: `Bearer ${token}` },
      params: { language: "en", kind: "cc" },
      multipart: { file: { name: "en.vtt", mimeType: "text/vtt", buffer: SAMPLE_VTT } },
    });
    expect([401, 403]).toContain(res.status());
  });
});
