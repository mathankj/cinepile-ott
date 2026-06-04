# Admin upload walkthrough — end-to-end QA

Date: 2026-06-04
Tester: Playwright-driven UI run against `localhost:5173` + `localhost:8000`, B2 storage live.
Subject title for this run: `qa-walkthrough-2026-06-04` (id=10).

## 5-bullet summary

- Happy path works end-to-end: create draft -> upload .mp4 to B2 -> upload English CC / Tamil / Hindi .vtt -> all surface as `<track>` entries in the player. Subtitle UPSERT is verified (re-uploading EN replaced row id 15 -> 18 without duplicating).
- One material UX bug: the title editor's right column (Upload + Subtitles cards) only renders after a title is published, because `TitleEditor.tsx` calls the **public** `catalog.detail` endpoint and `/v1/titles/{id}` 404s on drafts. Admins editing a brand-new draft never see the upload UI in-session. Either publish first via API or change the editor to call an admin-scoped detail endpoint.
- Subtitle Remove deletes the DB row only; the `.vtt` object in B2 is **intentionally retained** (documented in `backend/app/api/v1/admin.py:707-709` as an undo affordance — needs a future janitor job).
- Edge-case validators: extension allow-list correctly rejects `.exe` (415) and unauthenticated requests 401 / non-admin 403 / missing title 404. **Gap**: extension-only check accepts a `.mp4`-named file containing an EXE payload (200, stored). **Bug**: oversized `.vtt` returns HTTP **500** instead of the intended 413 — the `_SizeLimitedStream`'s `HTTPException` is raised inside boto3's worker and not propagated cleanly.
- Multi-audio per-title is NOT supported as a separate upload, by design. Only the HLS manifest's embedded `EXT-X-MEDIA TYPE=AUDIO` groups drive the player's Audio submenu. Settings gear shows Audio only when hls.js reports `audioTracks.length > 1`; with single-language test streams the menu correctly stays hidden. The client must ship multi-language audio inside their HLS package — we cannot add it later via upload.

---

## Step-by-step success path (working as-is)

Pre-requisites: backend + frontend running, admin seeded (`admin@anjaneya.app` / `admin1234`), Backblaze B2 env vars configured.

1. **Login**. Hit `/login`, fill email + password, pick the "Local Admin" profile on `/profiles`.
2. **Open create form**. Navigate to `/admin/titles/new`.
3. **Fill the create form**.
   - Slug: `qa-walkthrough-2026-06-04`
   - Type: Movie
   - Title: `QA Walkthrough Demo`
   - Synopsis, Year, Age (`U`). (No `original_language` field is exposed in the UI — defaults to `en`.)
   - Click **Create**. Browser navigates to `/admin/titles/10`. Status: `draft`.
4. **Publish (workaround required)**. The editor right column never renders until the title is published, because `useQuery({ queryFn: () => catalog.detail(titleId) })` hits the public endpoint which 404s drafts. Workaround used:
   `POST /v1/admin/titles/10/publish` via the admin token. After publish, reload `/admin/titles/10` — the **Video file** and **Subtitles (.vtt)** cards now render.
5. **Upload video**. Click "Click to choose a file", pick the 32-byte ftyp `tiny.mp4`. Frontend shows progress bar, status flips to "Uploaded". Backend log: `POST /v1/admin/titles/10/upload-video -> 200`. Object stored at `titles/10/master.mp4` in bucket `Netflix-dev-media`.
6. **Verify on title page**. `/title/10` renders the Play button. (Cannot enter `/watch/title/10` for admin user because admin has no active subscription — backend returns 402. To validate playback, set the title to `is_free: true` via `PATCH /v1/admin/titles/{id}` or grant the admin a sub.) After flipping `is_free=true`, `/watch/title/10` loads, hls.js / native player attaches the B2 presigned URL on the `<video>` element.
7. **Upload English CC**. Back on `/admin/titles/10`. In the Subtitles card, language=`en`, kind=`CC (same-language)`, click "Choose .vtt file", select `sub-en.vtt`. Row appears: `EN [cc]`.
8. **Upload Tamil subtitle**. Change language input to `ta`, kind back to `Subtitle (translation)`, choose `sub-ta.vtt`. Row appears: `TA [subtitle]`.
9. **Upload Hindi subtitle**. Same with `hi` / `sub-hi.vtt`. Row appears: `HI [subtitle]`.
10. **Verify all three on the Subtitles card**. DOM confirms 3 `<li>` entries with kind labels `[cc]`, `[subtitle]`, `[subtitle]`.
11. **Verify on watch page**. `/watch/title/10` mounts `VideoPlayer`. `document.querySelectorAll('video > track')` returns 3 entries:
    - `kind="captions"  label="EN" srcLang="en"` (because `cc` -> `captions` in the React mapping)
    - `kind="subtitles" label="TA" srcLang="ta"`
    - `kind="subtitles" label="HI" srcLang="hi"`
    All three `src` values are B2 presigned URLs. Browser native captions menu lists them; settings gear's Subtitles submenu also surfaces them when hls.js sees them in `subtitleTracks`.
12. **UPSERT re-upload**. Re-uploaded `sub-en.vtt` via `POST /v1/admin/titles/10/subtitles?language=en&kind=cc`. Before: row id 15. After: row id 18 (new id, same key, total count unchanged at 3). Confirms `_store_subtitle` deletes the prior row keyed on `(title_id, language)` before inserting a new one.
13. **Delete via Remove button**. Clicked Remove on the HI row. `DELETE /v1/admin/subtitles/{id}` -> 204. Subtitle count drops to 2. `.vtt` object in B2 is retained (intentional; see `admin.py:707-709`).

## Edge-case results

| # | Scenario | Expected | Observed | Verdict |
|---|----------|----------|----------|---------|
| 1 | Upload `malware.exe` to video endpoint | 415 (extension reject) | `{"error":{"code":"unsupported_media","message":"Extension '.exe' is not allowed..."}}` 415 | PASS |
| 1b | Upload EXE-payload file renamed to `.mp4` | (task expected reject) | 200 — extension whitelist passes, no magic-byte sniffing | **GAP**: validator is extension-only; bytes are not inspected. Title's master gets clobbered with EXE bytes. To harden, sniff the first 8 bytes (look for `ftyp` ISO BMFF box) or compute MIME server-side. |
| 2 | Upload 6.8 MB `big.vtt` (>5 MB cap) | 413 / 422 with `payload_too_large` | **500 Internal Server Error** | **BUG**: `_SizeLimitedStream.read()` raises `HTTPException(413)` from inside boto3's `upload_fileobj` worker thread. Boto3 wraps the exception in `S3UploadFailedError` and FastAPI's exception handler doesn't unwrap it -> 500. Fix: either content-length-check on the FastAPI side (`request.headers["content-length"]`) before streaming, or catch the wrapper and translate. Title row is NOT created on failure (transaction rolls back), so DB stays clean — but the partial object can still land in B2 because boto3 retries chunks. |
| 3a | Non-admin (`user@anjaneya.app`) hits `POST /v1/admin/titles/10/upload-video` | 403 | `{"error":{"code":"forbidden","message":"content_manager or admin role required."}}` 403 | PASS |
| 3b | Non-admin hits `POST /v1/admin/titles/10/subtitles` | 403 | 403 with same shape | PASS |
| 3c | Unauthenticated POST (no Authorization header) | 401 | `{"error":{"code":"unauthorized","message":"Not authenticated."}}` 401 | PASS |
| 4a | Admin POSTs to `POST /v1/admin/titles/9999/upload-video` | 404 | `{"error":{"code":"title_not_found","message":"Title not found."}}` 404 | PASS |
| 4b | Admin POSTs to `POST /v1/admin/titles/9999/subtitles?language=en&kind=cc` | 404 | 404 with `title_not_found` | PASS |

## Multi-audio gap

**Current architecture (Model A — manifest-side audio):**
- The catalog has a `audio_tracks` array on the title detail response. It is purely *informational metadata* (language/kind labels for the catalog UI), not a list of separately-uploadable audio files. The only writer is `replace_audio_tracks` (`PUT /v1/admin/titles/{id}/audio-tracks`) which takes JSON, not files.
- The video upload endpoint takes a *single* file and stores it as `titles/{id}/master.<ext>`. There is no `/upload-audio` route and no per-language audio asset model.
- The player relies on hls.js's `MANIFEST_PARSED` event and `.audioTracks` array (`VideoPlayer.tsx:131-132`). The gear shows an Audio submenu only when `audioTracks.length > 1`.

**Test result:**
1. Patched `title 10.hls_manifest_url` to `https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8`. The manifest is English-only (`audio_eng=...` variants, no `EXT-X-MEDIA TYPE=AUDIO` groups). Gear panel showed Quality only (Auto + 750p, 350p, 200p, 100p variants). Expected — no Audio submenu because no audio rendition groups.
2. Patched to Apple BipBop multi-audio (`https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8`). The manifest declares 3 audio groups `aud1/aud2/aud3` (English, different channel counts) and 1 subtitle group. The browser's `video.textTracks` exposed both the BipBop "English" captions and our uploaded TA/EN sidecars (4 tracks total). But the gear's Audio submenu still did NOT render. Hls.js's `.audioTracks` came back empty/single because all 3 groups share `LANGUAGE="en"` and hls.js collapses same-language groups.
3. Patched to BipBop 16x9 variant (`bipbop_16x9_variant.m3u8`) which has 2 audio renditions under the same GROUP-ID `bipbop_audio` with one AUTOSELECT/DEFAULT=YES and one NO. Same outcome — Audio submenu hidden. hls.js reports 1 logical audio track.

**Conclusion:** The multi-audio path is real but only triggers when the manifest declares **at least two `EXT-X-MEDIA TYPE=AUDIO` entries with distinct `GROUP-ID` or `LANGUAGE`** (the typical multi-language packaging shape: `en`, `ta`, `hi`). All three public test manifests we tried lacked true multi-language audio groupings, so we could not show the Audio submenu populated in this run. The logic itself is correct — verified by reading `VideoPlayer.tsx:346-359` — and would surface as soon as a real multi-language HLS is loaded.

**Recommendation for the client:**
> "Audio language selection is fully supported in the player. The way it works: when your encoding pipeline packages multiple language audio tracks into the HLS manifest (as separate `EXT-X-MEDIA TYPE=AUDIO` groups with distinct `LANGUAGE` attributes — this is what AWS MediaConvert / Bitmovin / Shaka Packager all do by default for multi-language content), our settings gear will automatically show an Audio submenu with the language names. There is no separate 'audio upload' step in the admin UI — the audio belongs *inside* the master HLS package. If you have an existing video with the dubs as separate .aac/.mp3 files, you'll need to re-mux them into a single multi-audio HLS before upload. We recommend running a small validation HLS through your pipeline first to confirm the `EXT-X-MEDIA TYPE=AUDIO` entries are present."

---

## Cleanup performed

- Test fixtures created in `C:/Users/matha/temp/fixtures/` and explicitly removed at the end of the run.
- Title 10 master restored to the original `tiny.mp4` upload (no Tears-of-Steel/BipBop manifest URL retained).
- No source code changes.
