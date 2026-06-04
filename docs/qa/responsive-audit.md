# Responsive audit — Anjaneya OTT

Audit date: 2026-06-04
Build: dev (frontend at :5173, backend at :8000, Neon dev DB)
Viewports covered: 360x640, 414x896, 768x1024, 1280x800, 1920x1080
Screenshots: `docs/qa/screenshots/<viewport>/<route>.png`

Known issues already reported (NOT re-listed below):
1. `/watch/title/:id` stuck on "Loading playback…" indefinitely across all viewports.
2. `/title/1` primary CTAs (Play / My List / Like) wrap awkwardly onto multiple rows on narrow widths.
3. `/me/list` card hover-overlay (title + actions) renders permanently on every tile instead of on hover.

The 360 and 414 sections are covered by the prior agent. Findings below add 768/1280/1920.

---

## 768x1024 tablet

Routes captured: home-anon, home-authed, browse, search, title-1, title-4, title-4-season-1, watch-title-1, me-list, me-history, subscribe, profiles, login, admin-titles, admin-titles-new, admin-users, admin-audit, and a few derived states (25 PNGs total).

New findings:

- **No hamburger / collapsed nav.** The desktop nav (`Home`, `TV Shows`, `Movies`, `New & Popular`, `My List`) renders inline at 768 and the labels wrap to 2 lines. `TV Shows`, `New & Popular`, and `My List` each break across lines, creating a 2-row header that pushes the billboard down. A hamburger / drawer should kick in at this breakpoint.
- **`/browse` "FREE" badge overlaps card title.** On the "QA Walkthrough Demo" card (the free-tier title), the red `FREE` pill is positioned over the title text instead of above/beside it. Reproducible at 768, 1280 and 1920 — flagging here because 768 is where the card width is tightest and the overlap is most obvious.
- **`/browse` filter row drops the "type" select.** At 768 only `All genres` and `Newest first` show; the third filter (presumably `All types` / movie-vs-series) is hidden. It also stays hidden up to 1280 and only appears at 1920.
- **`/admin/audit` sidebar low contrast.** Inactive sidebar links (`Dashboard`, `Titles`, `Users`) on the admin shell are rendered at very low opacity — they read as disabled rather than as available navigation. Active item (`Audit log`) is fine.
- **`/admin/titles/new` form is cramped.** The "Year / Runtime / Age" 3-column row clips the `Age rating` placeholder text to `U / L` (truncated from "U / U/A / A / 18+"). The form fields need to stack or the columns need to be 2-up at this width.
- **`/admin/users` blank.** Renders the page chrome, briefly flashes `Loading…`, then leaves the table area empty. Root cause is a backend 500 from `GET /v1/admin/users?page=1&page_size=100` — see 1280 section for details. Visible at every viewport, called out here as the first place noticed.
- **Billboard CTAs above the fold.** Confirmed OK at 768 for `/` (home-authed) and `/title/4` — buttons remain in the visible viewport. `/title/1` is still affected by known issue #2.
- **`/profiles` grid layout.** 4 profile tiles render in a single row at 768 with comfortable spacing — no issue.
- **Home page footer "bleeds" under the header.** On `/` (anon and authed), the footer link grid renders at very low opacity behind / under the top of the page, before the billboard skeleton. Looks like the footer is positioned absolutely or the page is in a loading state where the billboard fails to mask it. Visible at 1280 and 1920 too; called out here because the effect is most noticeable on tablet.

---

## 1280x800 laptop

Routes captured: 16 PNGs covering all required routes.

New findings:

- **`/admin/users` 500 — silent failure.** `GET /v1/admin/users?page=1&page_size=100` returns `500 Internal Server Error`. The frontend never surfaces an error toast, retry button, or empty state — it just renders the page header + filter bar with a blank table region. This is the highest-severity new finding because it looks like the page loaded successfully. Reproducible at every viewport; backend bug, not a layout bug, but visible only because the UI swallows it.
- **`/title/1` and `/title/4` hero contrast.** The billboard backdrop image either doesn't load or doesn't extend to cover the full hero area — title, metadata, and synopsis sit against a near-solid black panel, which makes the metadata row (`2026 · 1h 42m · PG-13`) almost invisible. At 1920 the backdrop fills better, so this is a sizing / object-fit issue at intermediate widths.
- **`/browse` filter row still missing the "type" select.** Only genres + sort are shown; the type filter doesn't appear until 1920. Either the filter shouldn't be width-gated or the breakpoint is wrong.
- **`/browse` FREE-badge overlap.** Same QA Walkthrough Demo overlap as at 768 — the badge is positioned with `left: 0; top: 0` against the title block instead of the poster.
- **`/watch/title/1` intermittent React Router 404.** On one of two captures, the route rendered "Unexpected Application Error — 404 Not Found" instead of the player shell. Looks like an auth-race after viewport resize: the loader fires before the auth context rehydrates, returns null, and React Router treats the empty match as a 404. Repro by resizing then immediately navigating; clear after a hard reload. Worth a real fix because users will resize / rotate.
- **`/admin/titles` first paint blank.** On a cold navigation, the table area paints empty for ~2-3 seconds while `/v1/admin/titles` loads. Adding a skeleton or `Loading…` placeholder would match the rest of the admin shell.

---

## 1920x1080 desktop

Routes captured: 16 PNGs covering all required routes.

New findings:

- **Player aspect ratio unverifiable.** `/watch/title/:id` is stuck on "Loading playback…" (known issue #1), so the player surface never renders at 1920. Once issue #1 is fixed the 1920 surface should be re-audited for letterboxing and control-bar density.
- **Watch-page footer bleed.** While stuck on "Loading playback…", the full marketing footer (FAQ, Help Centre, Investor Relations, Privacy, Cookie Preferences, Corporate Information, Contact Us, © 2026 Anjaneya OTT) is rendered below the loading state. The watch surface should suppress the global footer; seeing the marketing footer below a player is jarring.
- **`/browse` filter row finally shows the "type" select.** Three filters render in a row, confirming the missing filter at 768/1280 is a layout / breakpoint bug, not a missing feature.
- **`/admin/users` 500 — same silent failure.** Same as 1280 — UI shows page chrome with no error and no retry. No layout difference at 1920.
- **`/browse` FREE-badge overlap persists** on the QA Walkthrough Demo card. With more horizontal space the card is wider but the badge still sits inside / over the title area instead of on the poster.
- **`/me/list` and `/me/history` hover-overlay** still permanently on (known issue #3). At 1920 the cards are large enough that the overlay obscures most of the poster art.
- **`/admin/titles/new` form is comfortable** at 1920 — the 3-column row that clipped at 768 fits cleanly here. Confirms the 768 issue is purely a width-vs-padding bug.
- **`/profiles` tile grid** has very wide gaps at 1920 — the 4 tiles spread to the page edges with ~25vw between them. A `max-width` on the grid container would tighten this.

---

## Summary — 5 new issues worth fixing first

1. **`/admin/users` returns 500 and the UI silently renders blank** (no error, no retry). Looks like a successful empty state to operators. Fix backend handler and add an error boundary / empty state in the admin table component.
2. **No hamburger / collapsed nav at 768.** Desktop nav text wraps to two lines on iPad-portrait, breaking the header. Introduce a tablet breakpoint with a drawer.
3. **`/browse` "All types" filter hidden until 1920.** Either drop the breakpoint or include the filter in the same row at 768+.
4. **`/browse` FREE-badge overlaps the card title** on the free-tier card across every viewport. Reposition badge to a corner of the poster, not the title block.
5. **`/admin/titles/new` form clips field labels at 768** ("Age rating" placeholder collapses to "U / L"). Stack or 2-up the Year/Runtime/Age row below 1280.
