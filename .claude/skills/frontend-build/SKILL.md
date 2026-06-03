---
name: frontend-build
description: Use when adding or modifying React components in the frontend/ folder. Codifies our design system, file layout, API integration pattern, and responsive rules so every new screen feels like the same product.
---

# frontend-build — conventions for the Anjaneya OTT React app

The frontend lives in `frontend/`. Stack: **React 19 + Vite + TypeScript + Tailwind v4 + React Router + TanStack Query + Zustand + Framer Motion + hls.js + lucide-react**.

If you're adding a new page or component, follow this. If you find yourself fighting these rules, raise it — they exist for consistency, not as ceremony.

## File layout

```
frontend/src/
├── api/             # one file per resource group (titles, me, billing, admin)
│   ├── client.ts    # axios + auth interceptor + refresh-on-401
│   ├── types.ts     # mirrors backend Pydantic schemas
│   └── index.ts     # exported method namespaces (auth, catalog, playback, …)
├── stores/          # Zustand stores (auth, ...)
├── components/
│   ├── layout/      # AppLayout, Navbar, Footer
│   ├── title/       # TitleCard, TitleRow, Billboard
│   ├── player/      # VideoPlayer
│   ├── ui/          # generic buttons / inputs / modals (only what's reused)
│   └── ProtectedRoute.tsx
├── pages/           # one folder per top-level concept
│   └── admin/       # admin pages live under here
├── routes/          # createBrowserRouter setup
├── index.css        # Tailwind @theme + base reset
├── App.tsx          # QueryClient + Router
└── main.tsx
```

**Pages are dumb-ish; logic lives in hooks/api.** A page calls `useQuery({ queryFn: ... })`, renders. Side-effects (mutations) use `useMutation`. No hand-rolled fetch.

## Design tokens

Never hard-code Netflix colors / radii / spacings in JSX classes. The tokens live in `src/index.css` under `@theme`. Use:

- `bg-[var(--color-bg)]` / `text-[var(--color-text-primary)]` for surfaces & text
- `text-[var(--color-brand)]` / `bg-[var(--color-brand)]` for accents
- `rounded-[4px]` for cards/buttons (Netflix uses 4px, NOT `rounded-lg`)
- `transition-colors duration-200` for hover state changes
- `transition-transform duration-300 ease-[cubic-bezier(0.5,0,0.1,1)]` for card hover scale

Reusable utilities live in `index.css` under `@layer components`:
- `.btn-primary` (red CTA)
- `.btn-secondary` (translucent white)
- `.btn-ghost` (border-only)
- `.input-base` (form inputs)

If you need a NEW token, add it to `@theme` in `index.css` — do not sprinkle one-off hexes in components.

## Responsive rules — mobile-first

Every component must work at 375px width. Breakpoint ladder matches our Tailwind config:

```
default: ≤ 480px (small phones)
xs:      480 (large phones)
sm:      640 (tailwind default; tablet portrait)
md:      768 (tablet landscape)
lg:      1024 (small laptop)
xl:      1280 (desktop)
2xl:     1536
3xl:     1920 (Netflix scales to here)
```

**Rules:**
- Side gutters: `px-4 md:px-8 lg:px-[60px]` (16/32/60px — Netflix's exact ladder)
- Cards on mobile rows: `flex overflow-x-auto snap-x snap-mandatory no-scrollbar` — peek of next card encouraged, no arrow buttons
- Cards on desktop rows: same flex layout but arrow buttons fade in on `group/row:hover`
- Hero: `h-[50vh] min-h-[400px] md:h-[60vh] lg:h-[85vh]`
- Type: hero `text-[2.25rem] md:text-[3.5rem]`; row header `text-[1.125rem] md:text-[1.4rem]`

## API integration pattern

1. Add the endpoint to `src/api/index.ts` under the right namespace
2. Add a Pydantic-equivalent type to `src/api/types.ts`
3. In the component, call via TanStack Query:
   ```tsx
   const { data, isLoading } = useQuery({
     queryKey: ["titles", filters],
     queryFn: () => catalog.listTitles(filters),
     staleTime: 60_000,
   });
   ```
4. For writes, use `useMutation` + invalidate the relevant queryKey on success.

**Auth headers are automatic** — the axios interceptor reads the access token from `useAuthStore`. On 401, the interceptor refreshes once and retries; on second 401, it clears auth (frontend redirects on next navigation).

## Protected routes

Wrap any auth-required page with `<ProtectedRoute>` in `routes/index.tsx`. For role-gated routes, pass `roles={["admin"]}` or `roles={["admin", "content_manager"]}`.

```tsx
{
  path: "/admin",
  element: <ProtectedRoute roles={["admin", "content_manager"]}><AdminLayout /></ProtectedRoute>,
  children: [...]
}
```

## Animations — Framer Motion or CSS?

- **CSS** for hover (`hover:scale-105 transition-transform`), entrance keyframes (`animate-fade-in`)
- **Framer Motion** for page transitions, AnimatePresence for modal in/out, anything needing exit animation

Netflix's curves: `cubic-bezier(0.5, 0, 0.1, 1)` (defined as `--ease-netflix` in tokens). Durations 200–300ms. Never go above 400ms.

## Anti-patterns

- ❌ Hard-coded `#E50914` or `#141414` in JSX classes — use tokens
- ❌ `rounded-lg` (8px) or `rounded-xl` (12px) on title cards — Netflix is 4px
- ❌ Drop shadows on cards — Netflix doesn't use them
- ❌ Centered nav — Netflix is left-aligned after logo
- ❌ `hover:scale-150` without sibling translate — neighbors clip
- ❌ Multi-aspect-ratio cards in one row
- ❌ Hover preview that starts at 0ms — needs ~750ms dwell delay
- ❌ Sticky+auto-hide navbar — Netflix's nav just sits there

See `docs/research/2026-06-03-netflix-design-system.md` (if added) or the in-line research notes for the full anti-pattern list.

## Adding a new page — checklist

1. Create `src/pages/MyPage.tsx`
2. Add route in `src/routes/index.tsx`
3. Add nav link in `src/components/layout/Navbar.tsx` (if user-facing) or `AdminLayout.tsx`
4. Use the design tokens — `bg`, `text`, `brand`, etc.
5. Mobile-test at 375px before committing
6. Run `npm run build` — type errors must pass
7. Commit

## Running the dev environment

```bash
# Two terminals.
# Backend (port 8000):
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# Frontend (port 5173 — proxies /v1/* to 8000 via vite.config.ts):
cd frontend && npm run dev
```

Open http://localhost:5173 — login with `admin@anjaneya.app` / `admin1234` for full access (assumes seed has run).

## When something doesn't look right

Use the `/browse` skill from gstack (or the `mcp__plugin_playwright_playwright__*` tools) to:
- Take a screenshot at 375 / 768 / 1024 / 1440
- Compare to the equivalent Netflix screen
- Adjust spacing / radius / font-size / hover state until they match

The `docs/runbooks/responsive-qa.md` file (when written) logs each comparison pass.
