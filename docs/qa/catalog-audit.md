# Catalog & Discovery Audit — 2026-06-04

Audit of /home rows, /browse filters, /search, recommendations, hover reveals,
race conditions, and mobile experience. Conducted in real browser (Playwright
+ headless Chromium) against the locally-running stack (frontend 5173, backend
8000) wired to the dev Neon Postgres DB.

Test users used: `user@anjaneya.app / user1234`, plus a fresh-signup user
`qa-fresh-30731@anjaneya.app`.

---

## Top issues at a glance

| # | Severity | Area | Finding |
|---|----------|------|---------|
| 1 | High | Backend perf | `/v1/home` consistently takes **15–35s** in dev (Neon round-trips); page is unusable without ~25s wait. |
| 2 | High | Recommendations | `recommended_for_you` filters reactions on `kind == "like"` which is **never** a stored value (valid kinds are `thumbs_up` / `double_thumbs_up` / `thumbs_down`). Reactions are silently dropped as recommendation seeds. |
| 3 | Medium | A11y | Card hover-reveal overlay is CSS `:hover` only — keyboard `:focus` does not reveal it. Tab users can never see the Play/+/Info actions. |
| 4 | Medium | UX | Hover-reveal action buttons (Play, +, Info) are `<button>` elements with `stopPropagation()` — they have **no onClick handler**, so clicking them does nothing. The outer `<Link>` is what navigates, only if you click off-button. |
| 5 | Medium | /browse | No **type** dropdown in the filter UI — only genre + sort. Switching between Movies/Series/All requires editing the URL or using top-nav links. |
| 6 | Low | /search | One-character input writes `?q=<x>` to URL but UI message still says "Type at least 2 characters", creating a stale-URL state on refresh. |
| 7 | Low | TitleDetail | "Add to My List" button has no client-side click gate; a double-click fires two POST requests (backend is idempotent, so no data corruption, but two network round-trips happen). |
| 8 | Low | /home | Right-arrow scroll button is never disabled, even when the row is scrolled fully to the right; clicking again is a silent no-op. |

---

## A. Horizontal scroll behaviour on /home rows

Route: `/`
Component under test: `frontend/src/components/title/TitleRow.tsx`

### Mouse-wheel scroll
- Repro: Hover the "New Releases" row, scroll wheel vertically.
- Actual: **No horizontal scroll**. Standard vertical-wheel events do nothing to the row (no `onWheel` handler converts deltaY→scrollLeft).
- Expected: Many SVOD apps translate wheel-Y to scroll-X over a row.
- Fix: Add `onWheel={(e) => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); ref.current?.scrollBy({ left: e.deltaY, behavior: 'smooth' }); } }}` to the row scroller. (Low priority — Netflix.com doesn't do this either.)

### Drag scroll
- Repro: Click-and-drag a card horizontally.
- Actual: Pointer-down on a card initiates a link drag, not a scroll-drag. Touch swipe works (CSS `overflow-x-auto`).
- Expected: Either drag-to-scroll or unambiguous click vs. drag.
- Fix: Either accept native overflow scroll only (current behavior), or implement a pointer-drag-to-scroll shim with a 5px threshold before flipping from click to drag.

### Arrow buttons
- Repro: Hover the row on desktop (>=md). Click left/right chevron.
- Actual: Buttons appear on hover (`group-hover/row:opacity-100`, gated by `useState` hover); clicking right scrolls by `0.85 * clientWidth` smoothly. Confirmed: scrollLeft 60 → 1391 after one right-click on the 1521-wide New Releases row.
- Issue: Right arrow remains visible and clickable when `scrollLeft === scrollWidth - clientWidth`. Clicking again does nothing.
- Fix: In `scrollBy`, compute `canScrollRight` and `canScrollLeft` from a `scroll` listener; disable the button (or hide it) when at the edge.

### Keyboard scroll
- Repro: Tab to a card, press ArrowRight.
- Actual: ArrowRight scrolls the **page** (default page-down behavior), not the row, and focus stays on the same card. There is no roving tabindex pattern.
- Expected: ArrowLeft/Right should move focus to the prev/next card within the row, with smooth scroll-into-view.
- Fix: Add a `onKeyDown` handler on the row that intercepts Arrow keys when focus is inside the scroller and moves focus + scrolls the next sibling card into view.

### Snap behaviour
- Repro: Set `scrollLeft = 150` (mid-card position) on a row with `snap-x snap-mandatory`.
- Actual: Browser snaps back to `scrollLeft = 60` (the first card's snap-start), which matches the left padding.
- Expected: Snaps to card edges. Working as designed.

### Performance — 20 vs 50 items
- Cannot mock — the dataset has **only 9–10 published titles** total. The Browse API caps `page_size` at 100 (`HTTP 422` for >100), so a 50-item row request returns ≤9 items.
- Indirect observation: rendering 10 cards with images is fine; `loading="lazy"` is applied on `<img>`. Largest performance issue is the **backend's 15–35s `/v1/home` response** (see Backend Perf section below), not row rendering.

---

## B. Browse page filters at /browse

Route: `/browse`
Component: `frontend/src/pages/Browse.tsx`

### Genre dropdown
- Populated from `/v1/home/genres` (5 genres: Animation, Comedy, Documentary, Drama, Sci-Fi).
- Selecting `Drama` → URL becomes `?genre=drama&page=1` and grid refetches.
- Working.

### Type filter
- **No type dropdown in the UI.** The component reads `type` from URL but never lets the user set it; only the H1 title changes from "Browse" → "Movies" / "TV Shows" based on URL.
- Fix: Add a third `<select>` for Type, mirroring the genre/sort pattern. Or surface Movie/Series pills next to the H1.

### Sort dropdown
- Five options: Newest first, Oldest first, A→Z, Z→A, Most watched. Selecting any updates URL + refetches.
- Working.

### Filter combinations
- Repro: `/browse?type=movie&genre=drama&sort=-published_at`
- Actual: H1 = "Movies", 3 cards: Cosmos Laundromat, Spring, Sintel. Matches backend `/v1/titles` query.
- Working.

### Pagination
- Repro: There are only 9 published titles; `page_size = 30` → total never exceeds page_size → **Pager is never rendered** (gated by `data.total > data.page_size`).
- Could not exercise Prev/Next button states with the seed dataset.
- Inferred from code: `disabled={page <= 1}` on Prev and `disabled={page >= totalPages}` on Next — correct, with `opacity-40` disabled styling. Needs verification once dataset grows past 30 titles.

### Empty state
- Repro: `/browse?type=series&genre=animation` (no series tagged as animation).
- Actual: Card grid empty + helpful message *"No titles match. Try clearing filters."* in a bordered box. The genre + sort dropdowns remain interactive.
- Working.

### URL deep-linking
- Repro: Navigate to `/browse?type=movie`, then reload (Ctrl+R).
- Actual: URL preserved, "Movies" h1, same 8 movie cards. Working.

---

## C. Search at /search

Route: `/search`
Component: `frontend/src/pages/Search.tsx`

### 1-char input
- Repro: Type "b" into the search box.
- Actual: After 300ms debounce, URL becomes `?q=b` even though the query is NOT fired (`enabled: debounced.length >= 2`). The UI shows "Type at least 2 characters."
- Issue: URL is updated for any non-empty `debounced`, but the rendered "no-search" state contradicts the URL. If a user shares the link, the recipient sees the same dead state.
- Fix: Gate the `setParams({q: debounced})` call on `debounced.length >= 2`.

### 2+ char input (debounce)
- Repro: Type "big".
- Actual: After ~300ms, GET `/v1/titles/search?q=big` fires, returns Big Buck Bunny. Working.

### Special chars — SQL LIKE escape
- Repro: type `%`, then `%%`.
- Actual: Both return zero results ("No matches for "%%""). Confirmed at API: `/v1/titles/search?q=%25%25` → `[]`. Backend properly escapes LIKE wildcards.

### Empty result
- Repro: type a nonsense string like "zzzzz".
- Actual: "No matches for \"zzzzz\"." Working.

### Unicode
- Repro: type Hindi `हनुमान`.
- Actual: After debounce, URL has URL-encoded UTF-8, no matches (no Hindi titles in seed). Working — query is correctly UTF-8 round-tripped.

### Click result then back-nav
- Repro: search "big" → click Big Buck Bunny → browser back.
- Actual: Returns to `/search?q=big` with the input populated and the result still visible. Working.

---

## D. Recommendations row

Route: `/` (home)
Component: backend `app/services/browse.py::recommended_for_you`, frontend pulls via `/v1/home` row `kind=recommended`.

### Anonymous /home — no row
- Confirmed: Anon `/v1/home?country=IN` returns 3 rows (New Releases, Trending Now, Top 10 in IN). No recommended row. Correct.

### Fresh-signup user (no signal) — no row
- Created `qa-fresh-30731@anjaneya.app`, hit `/v1/home`. Rows: New Releases, Trending Now, Top 10 in IN. No recommended/my_list/continue_watching. Correct ("deliberately under-reports rather than hallucinate", per docstring).

### user@anjaneya.app — row appears with 5 items
- Recommended for You: Pioneer One, Hero, Cosmos Laundromat, Spring, Caminandes: Llamigos. Row rendered.

### **Are titles actually similar to what user reacted to? — BUG**
- `user@anjaneya.app`'s reactions are: `Big Buck Bunny: thumbs_up`, `The Anjaneya Chronicles: double_thumbs_up`.
- File `backend/app/services/browse.py:158` reads `Reaction.kind == "like"`. Valid kinds (per `backend/app/services/reactions.py:11`) are `{"thumbs_down", "thumbs_up", "double_thumbs_up"}`. No row ever has `kind == "like"`.
- **Consequence:** reactions are NEVER used as recommendation seeds. The row only fires from watchlist + watch_progress signals. End-user impact is partial (other seeds compensate when present), but a user whose only signal is a thumbs-up will see zero recommendations.
- Fix: change line 158 to `Reaction.kind.in_(("thumbs_up", "double_thumbs_up"))` (exclude thumbs_down as a negative signal).

---

## E. Title card hover reveal

Component: `frontend/src/components/title/TitleCard.tsx`

### Hover (>=400ms) → overlay
- Repro: Hover a card on desktop, wait ~1s.
- Actual: After 400ms transition-delay, `.hover-reveal` overlay fades in (`opacity 0→1`, 200ms ease-out). Buttons: Play (filled white), Plus, Info. Working.

### Quick scroll-past
- Repro: Move mouse quickly across the row without dwelling.
- Actual: The 400ms delay prevents flash — overlay opacity stays at 0 because mouse leaves before the delay elapses. Working as designed.

### Clicking Play in the hover overlay
- Repro: Hover card, click the Play button inside the overlay.
- Actual: Nothing happens. `CardActionButton` has `onClick={(e) => e.stopPropagation()}` and **no other handler** — explicit comment in source says "Stops link propagation so clicking Play doesn't bubble up into the card's outer `<Link>` twice." Result: Play button is a dead button. Same for `+` and `Info`.
- Expected: Play should navigate to `/watch/title/{id}` (movies) or `/title/{id}` (series). `+` should add to list. `Info` should navigate to `/title/{id}`.
- Fix: Each button should have a real handler — e.g. `onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigate(playPath); }}` using `useNavigate()` from react-router.

### Keyboard focus → overlay
- Repro: Tab to the card.
- Actual: Card receives `:focus-visible` (white outline), but **`.hover-reveal` overlay stays at `opacity: 0`**. The overlay uses `group-hover/card:opacity-100` only (CSS hover). Keyboard users cannot see the Play/+/Info actions.
- Fix: Add a focus variant: `group-focus-within/card:opacity-100 group-focus-within/card:pointer-events-auto`. Or always render at opacity 1 when `:focus-within` matches.

---

## F. Click-fast / load-race

### Double-click Subscribe
- Code review: `frontend/src/pages/Subscribe.tsx:120` uses `busyCode` state + `disabled={busyCode === p.code}` + button label flip to "Starting…" — double-click is suppressed. Correct.

### Double-click "Add to my list"
- Repro: Open `/title/1` while logged in, rapid-double-click the `+` button.
- Code review: `TitleDetail.tsx:122` button has NO `disabled` gating. Both clicks fire `addM.mutate()`.
- Backend behavior: POST `/v1/me/list/1` twice → `{added: true}` then `{added: false}` (idempotent INSERT IGNORE). No duplicate row, no error, but two HTTP requests.
- Fix: `disabled={addM.isPending || rmM.isPending}` on the button to gate the second click.

### Rapid back-nav (Home → Browse → Home → /title/4 → back back back)
- Repro: Navigated through the chain, then 3× browser-back.
- Actual: Each back transition completed cleanly. Final URL `/search?q=…` (the original starting page). No blank pages, no 404s, no JS errors. Working.

### Click a card while row is mid-scroll
- Repro: Click chevron to start a smooth-scroll, then immediately click a visible card.
- Actual: The Link's click handler fires on the original card position — but `scroll-smooth` doesn't move the card under the cursor (smooth-scroll happens on the scroller, not via transform). Click goes to whichever card was actually under the mouse at click time.
- Working, but not perfect: if the user starts at scrollLeft=60 and the card moves under their cursor mid-animation, they could land on the "wrong" card. The animation is short (~300ms via `scroll-smooth`) so impact is minor.

---

## G. Mobile (375x667)

### Tap a card opens detail
- Repro: 375x667 viewport, tap any card on /home.
- Actual: Navigates to `/title/{id}`. Working.

### Horizontal swipe scrolls
- Confirmed via `scrollBy({left: 200})` programmatic: `scrollLeft 16 → 180`. CSS `overflow-x-auto` + `snap-x snap-mandatory` makes touch swipe work natively. Working.

### Hamburger drawer
- Repro: Tap top-right Menu icon.
- Actual: Right-side drawer slides in with Home / TV Shows / Movies / New & Popular / My List / Search / (divider) / My List / History / Subscription / Sign out.
- Issue: **"My List" appears twice** in the drawer — once in the `navLinks` array (because `authOnly` shows it) and again in the logged-in section below the divider. Minor visual repetition.
- Fix: Drop the duplicate `My List` link from the logged-in section, OR filter it out of `navLinks` when also rendered below.

---

## Backend performance (out-of-scope but blocking)

Every request to `/v1/home?country=IN` in this audit took **15–35 seconds**. Direct `curl` reproduces:
- `/v1/home?country=IN`: 17–35 s
- `/v1/home` (no country): 13 s
- `/v1/titles`: 8 s
- `/v1/titles/search?q=big`: <1 s
- `/v1/home/genres`: 1.7–2.4 s

Root cause: `backend/.env` `DATABASE_URL` points to a Neon Postgres in **us-east-1** (`ep-cool-dust-ap0zn5d8-pooler.c-7.us-east-1.aws.neon.tech`). Each query that the home service issues serially (continue_watching → my_list → recommended_for_you → new_releases → trending → top_in_country → because_you_watched ×2 → genre rows) pays a full transatlantic round-trip per await.

Impact on UX during this audit: home page sat on the skeleton for 25+ seconds before rendering. A real user on a slow connection would assume the app is broken.

Suggested fixes (not blocking the audit):
1. Run a local Postgres for dev (docker compose was likely already configured, just unused).
2. Or: parallelize the row queries with `asyncio.gather()` in `build_home` — currently they execute serially due to `await`-per-row.
3. Or: add a server-side cache (60s) keyed on `(user_id, country)` for home rows.

---

## Audit env

- Frontend: Vite 5 dev server on http://localhost:5173
- Backend: FastAPI dev on http://localhost:8000 (gunicorn — see /healthz)
- Database: Neon Postgres us-east-1 (dev pool)
- Browser: Playwright-driven Chromium, viewport 1440x900 (and 375x667 for mobile)
- Date: 2026-06-04
