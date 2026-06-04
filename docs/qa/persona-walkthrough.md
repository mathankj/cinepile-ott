# Persona Walkthrough QA — Anjaneya OTT

**Date:** 2026-06-04
**Method:** Playwright drove a real desktop-chromium against http://localhost:5173 backed by a live FastAPI on :8000 and Neon Postgres. Personas were walked end-to-end in order (anonymous → new signup → signed-in non-subscriber → subscribed user → admin), with screenshots written to `frontend/test-results/personas/` and machine-readable findings dumped to `frontend/test-results/persona-findings.json`. The temporary driver spec lived at `frontend/tests/e2e/_persona-walk.spec.ts` and has been removed after the run.

**Result summary (per persona):**

| Persona | OK | Warn | Broken |
| --- | --- | --- | --- |
| Anonymous user | 7 | 3 | 1 |
| New signup | 1 | 2 | 0 |
| Signed-in non-subscriber | 5 | 1 | 0 |
| Subscribed (after DB-mark active) | 3 | 0 | 0 |
| Admin | 3 | 1 | 0 |

Legend: ✅ ok · ⚠️ polish / confusing · ❌ broken / dead-end · ✏️ suggested fix

---

## Findings table (top 22, ordered by severity then persona)

| # | Persona | Route / Action | Status | Observation | ✏️ Suggested fix |
| --- | --- | --- | --- | --- | --- |
| 1 | anonymous | Click `Play` on a paid title (`/title/1`) | ❌ | Anonymous user is sent straight to `/watch/title/1`. `/watch/:kind/:id` is **outside** `ProtectedRoute` in `routes/index.tsx`, so the Watch page renders, fires the playback API, gets back 401 from the backend, and shows a generic "Couldn't start playback" with **no** Sign-In CTA and **no** "View Plans" button (the View-Plans branch only fires on HTTP 402, not on 401). Dead-end. | Wrap `/watch/:kind/:id` in `<ProtectedRoute>` so anonymous Play attempts route through `/login?from=/watch/title/1`, then once logged-in the existing 402-path takes over. |
| 2 | anonymous | `/login` → "Need help?" link | ⚠️ | The `Need help?` link points back to `/login` itself (`<Link to="/login">` in `Login.tsx`). Clicking it does nothing visible. | Either remove the link or wire it to a real `/help` or `/forgot-password` route. Right now it's a tease. |
| 3 | anonymous | `/login` → cross-link to signup | ⚠️ | Test couldn't find an `a[href="/signup"]` selector but the footer DOES render `<Link to="/signup">`. Acceptable; flagged only because the link styling (`text-white hover:underline`) is muted enough that QA's selector missed it. | Make the "Sign up now" link visually heavier (brand red, or `font-semibold`) so new users notice it. |
| 4 | anonymous | `/signup` → cross-link to login | ⚠️ | Same as above — link exists but is hard to find. | Match Netflix: bold the "Sign in" link or add a separator/icon. |
| 5 | anonymous | Navbar | ✅ | Sign-In CTA visible top-right; Home / TV Shows / Movies / New & Popular all clickable for anonymous users. | — |
| 6 | anonymous | `/browse?type=movie`, `/browse?type=series`, `/title/:id`, `/search` | ✅ | All four browse/search routes render for anonymous users (8 movie cards, 2 series cards). | — |
| 7 | anonymous | `/me/list`, `/admin` | ✅ | Both correctly redirect to `/login` via `ProtectedRoute`. | — |
| 8 | new-signup | `/signup` with RFC 6761 reserved TLD (`@anjaneya.test`) | ⚠️ | Pydantic-email rejects `.test` / `.example` / `.localhost` TLDs as "special-use or reserved". Backend returns 422; the frontend just shows axios's raw `"Request failed with status code 422"` text. Cryptic for users who naturally type `@example.com`. | Catch `RequestValidationError` in the FastAPI auth router and map the email-validator error to a friendly per-field message ("Please enter a valid email address."). Also surface field-level errors in `Signup.tsx` instead of one generic banner. |
| 9 | new-signup | `/signup` → `/profiles` redirect | ✅ | After successful signup the ProfileGate redirects to the picker correctly. Backend auto-creates a primary profile (verified via `GET /v1/me/profiles` returning one tile named after `full_name`). | — |
| 10 | new-signup | `/profiles` first paint | ⚠️ | The picker shows only "Loading profiles…" plain text while `GET /v1/me/profiles` is in flight (≥1.5 s on cold Neon). For a brand-new signup the user has no idea what's happening — no skeleton, no avatar placeholder, no clue what comes next. The QA spec mistakenly flagged this as "broken" (it isn't), but the empty/loading UX is genuinely bad. | Render a 1-tile skeleton placeholder (gradient square + shimmer + "Loading your profile…" subtitle) while the query is pending. Match the Netflix-style picker frame. |
| 11 | non-subscriber | `/login` → `/` → ProfileGate bounce | ⚠️ | On a `page.goto("/title/1")` *immediately after* picking a profile, ~30% of runs bounced back to `/profiles` because `ProfileGate` checks Zustand persist hydration on the new route's first render and races the navigation. Reproduces deterministically on fresh contexts. | The gate already uses `persist.hasHydrated()`; also subscribe to `useAuthStore.persist.onFinishHydration` so the redirect is gated on **both** stores being hydrated, not just profile. Or render a 1-frame loader instead of immediately redirecting. |
| 12 | non-subscriber | Play paid title → `/watch/title/1` | ✅ | Backend returns 402; Watch page renders "An active subscription is required…" with the **View Plans** button. Snippet from page body: `"An active subscription is required to play this title. View Plans Go back"`. The CTA is the brand-red primary button — prominent and obvious. | — |
| 13 | non-subscriber | Back-button from `/watch` | ✅ | Browser back returns to `/title/1` as expected. The in-page "Go back" button uses `nav(-1)` so it also works. | — |
| 14 | non-subscriber | `/subscribe` page | ✅ | Both plans render (Monthly ₹199, Annual ₹1990); the active-or-pending banner appears at the top with the correct "Complete checkout" or "Cancel subscription" CTA. | — |
| 15 | non-subscriber | `/me/list` empty state | ⚠️ | Page shows only `"My List"` heading + `"Loading…"` then resolves to a blank list. There's no empty-state message ("You haven't added anything yet — browse to add titles"). For a logged-in user with no watchlist this is a dead-end. | Add an empty-state component for `/me/list` with copy + a CTA back to `/browse`. |
| 16 | non-subscriber | Navbar after login | ✅ | Sign-In link gone; avatar dropdown rendered (profile avatar + ChevronDown). Drawer's mobile equivalent also has Sign-out. | — |
| 17 | subscribed | `POST /v1/subscriptions` then DB-mark active | ✅ | Subscribe POST returns 201 (or 409 if a pending row already exists). Manual SQL `update subscriptions set status='active', current_period_end=now()+interval '1 month' where user_id=6` (note: user_id is **6** for `user@anjaneya.app`, not 3 as the prompt assumed) flips the sub correctly. | Wherever the prompt is documented, fix the user_id from 3 → 6 (or fetch by email). |
| 18 | subscribed | Play paid title `/watch/title/1` after activation | ✅ | `<video>` element mounted; backend returned a valid Backblaze B2 presigned MP4 manifest URL (`master.mp4?X-Amz-…`); player initialised. Note: the manifest is MP4, **not** HLS — `VideoPlayer.tsx` correctly falls through to `<video src=...>` without hls.js. | — |
| 19 | admin | `/admin` dashboard | ✅ | Dashboard h1 = "Dashboard"; left rail (Dashboard / Titles / Users / Audit log) renders. | — |
| 20 | admin | `/admin/titles` | ✅ | 10 rows rendered (matches 9 seeded titles + 1 draft / "all" includes drafts). Took ~3-4 s on first paint while the admin titles query loaded. | Consider a skeleton row state so the table doesn't look empty during the cold-Neon round trip. |
| 21 | admin | `/admin/users` | ⚠️ | The Users table sometimes still shows "Loading…" after 5 s due to slow `GET /v1/admin/users` on cold Neon. Eventually populates but the wait without skeleton is noticeable. | Skeleton row state + a 10s timeout fallback ("Couldn't load users — retry?"). |
| 22 | admin | `/admin/audit` | ✅ | Renders the audit log with WHEN / ACTOR / ACTION / ENTITY columns; sample row: `6/4/2026, 6:54:10 AM #4 (admin) title.upload_video title#10`. | — |

---

## Cross-cutting observations (not new rows, but worth noting)

- **Loading state inconsistency.** Home uses a polished shimmer skeleton (`HomeSkeleton`), but `/me/list`, `/admin/titles`, `/admin/users`, and `/profiles` all show plain text like "Loading…" or "Loading profiles…". Pick one (the shimmer pattern) and apply it everywhere.
- **Error message inconsistency.** Watch shows a clear "An active subscription is required to play this title." for 402, but the same Watch page on 401 just shows "Couldn't start playback" (no CTA). Signup shows raw axios text on 422. Standardise via the existing `apiErrorMessage` helper + add field-level error rendering for 422.
- **Razorpay test-checkout is a separate HTML page (not the React app).** Anyone debugging payments needs to know that `/test-checkout` is a backend-served helper, **not** a route in the React router. Tooltip-worthy.
- **Profile picker has no "no profile yet" empty state** — relies entirely on the backend auto-creating one on signup. If that ever fails or the user manually deletes the primary, the picker would just show "Loading…" forever then "" empty. Defensive: render a "Create your first profile" tile if `items.length === 0`.

---

## Top-5 critical issues (action list)

1. **Anonymous click on Play is a dead-end.** Wrap `/watch/:kind/:id` in `<ProtectedRoute>`. **(❌ broken)**
2. **422 signup errors are cryptic.** Map pydantic-email validation errors to per-field user-friendly messages — `@example.com` / `@anjaneya.test` / `.localhost` users get nowhere right now. **(⚠️ blocks demo "type any email and try it")**
3. **ProfileGate hydration race occasionally bounces users back to `/profiles`** on the first hard nav after picking a profile. Gate the redirect on auth-store hydration too, or render a one-frame loader. **(⚠️)**
4. **Inconsistent loading states.** Add proper skeletons to `/profiles`, `/me/list`, `/admin/titles`, `/admin/users` — Home's shimmer pattern is the template. **(⚠️ polish)**
5. **`/me/list` empty state is just a blank screen.** Add empty-state copy + a "Browse titles" CTA. Same for the Watch 401 case — give users a Sign-In button instead of a generic error. **(⚠️ polish)**

---

## Evidence

- Screenshots: `frontend/test-results/personas/*.png` (anon-home, anon-browse-movies, anon-title-1, anon-after-play-click, new-signup-profiles, new-signup-home, nosub-watch-blocked, nosub-subscribe, sub-watch-attempt, admin-dashboard)
- Raw findings JSON: `frontend/test-results/persona-findings.json`
- Spec file: removed (lived at `frontend/tests/e2e/_persona-walk.spec.ts`)
