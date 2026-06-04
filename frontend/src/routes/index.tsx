import { lazy, Suspense, useEffect, useState } from "react";
import { createBrowserRouter, Navigate, RouterProvider, useLocation } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import ProtectedRoute from "../components/ProtectedRoute";
import { useAuthStore } from "../stores/auth";
import { useProfileStore } from "../stores/profile";

/**
 * Route-level code-splitting via React.lazy().
 *
 * Each page becomes its own chunk that's only fetched when the user navigates
 * to it. The initial bundle now contains only AppLayout + Navbar + the auth
 * store + a small router shell — typically 30-60 KB gzipped instead of 330.
 *
 * Heavy dependencies (hls.js for /watch, the player code, framer-motion's
 * full animation suite) all move out of the critical path.
 */
const Home = lazy(() => import("../pages/Home"));
const Browse = lazy(() => import("../pages/Browse"));
const Search = lazy(() => import("../pages/Search"));
const TitleDetail = lazy(() => import("../pages/TitleDetail"));
const SeasonPage = lazy(() => import("../pages/Season"));
const Watch = lazy(() => import("../pages/Watch"));
const MyList = lazy(() => import("../pages/MyList"));
const History = lazy(() => import("../pages/History"));
const Login = lazy(() => import("../pages/Login"));
const Signup = lazy(() => import("../pages/Signup"));
const Subscribe = lazy(() => import("../pages/Subscribe"));
const ProfilesPage = lazy(() => import("../pages/Profiles"));

// Admin pages are also lazy-loaded — they only ever load when an admin actually
// navigates to /admin, which is rare for regular users. Big win for general traffic.
const AdminLayout = lazy(() => import("../pages/admin/AdminLayout"));
const AdminDashboard = lazy(() => import("../pages/admin/Dashboard"));
const AdminTitlesList = lazy(() => import("../pages/admin/TitlesList"));
const TitleEditor = lazy(() => import("../pages/admin/TitleEditor"));
const AuditLog = lazy(() => import("../pages/admin/AuditLog"));
const AdminUsers = lazy(() => import("../pages/admin/Users"));

/**
 * Suspense fallback — a minimal black surface to avoid flash-of-white during
 * chunk load. Real shimmer skeletons live in each page's own loading state.
 */
function PageLoader() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-[var(--color-brand)]"
        aria-label="Loading"
      />
    </div>
  );
}

function lazyRoute(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

/**
 * Wraps a route so that authed users without an active profile are bounced to
 * /profiles first. Anonymous users pass through (they hit the existing
 * ProtectedRoute / login redirect). Once a profile is picked, the active row
 * lives in the profile store and this gate becomes a no-op.
 *
 * Hydration race: Zustand v5's persist middleware rehydrates from localStorage
 * asynchronously. On the first render after a hard reload (page.goto in tests,
 * F5 in browser), `active` is null even when localStorage has a saved profile.
 * If we redirected then, the URL would briefly flip to /profiles and the user
 * would have to re-pick. We use `persist.hasHydrated()` to defer the redirect
 * decision until the store has loaded its persisted state.
 */
function ProfileGate({ children }: { children: React.ReactNode }) {
  const loc = useLocation();
  const isLoggedIn = useAuthStore((s) => !!s.accessToken);
  const active = useProfileStore((s) => s.active);
  // Wait for BOTH stores to finish persist-hydration before deciding. If we
  // only checked the profile store, a hard navigation that hits this gate
  // before the auth store rehydrates would see isLoggedIn=false (no token
  // yet) → no redirect → then the redirect would fire one tick later, AFTER
  // the page rendered, causing a visible URL flip and lost user state.
  const [profileHydrated, setProfileHydrated] = useState(() =>
    useProfileStore.persist.hasHydrated(),
  );
  const [authHydrated, setAuthHydrated] = useState(() => useAuthStore.persist.hasHydrated());
  useEffect(() => {
    if (profileHydrated) return;
    return useProfileStore.persist.onFinishHydration(() => setProfileHydrated(true));
  }, [profileHydrated]);
  useEffect(() => {
    if (authHydrated) return;
    return useAuthStore.persist.onFinishHydration(() => setAuthHydrated(true));
  }, [authHydrated]);
  const hydrated = profileHydrated && authHydrated;

  // Don't gate the picker itself, and don't gate auth pages.
  const exempt =
    loc.pathname === "/profiles" ||
    loc.pathname === "/login" ||
    loc.pathname === "/signup";
  if (hydrated && isLoggedIn && !active && !exempt) {
    return <Navigate to="/profiles" replace />;
  }
  return <>{children}</>;
}

export const router = createBrowserRouter([
  // Auth routes — rendered WITHOUT AppLayout so the Netflix-style full-bleed
  // hero card has no navbar/footer chrome around it.
  { path: "/login", element: lazyRoute(Login) },
  { path: "/signup", element: lazyRoute(Signup) },
  // Profile picker — protected, but also lives outside AppLayout (Netflix has
  // no nav on "Who's watching?").
  {
    path: "/profiles",
    element: <ProtectedRoute>{lazyRoute(ProfilesPage)}</ProtectedRoute>,
  },
  {
    element: (
      <ProfileGate>
        <AppLayout />
      </ProfileGate>
    ),
    children: [
      { path: "/", element: lazyRoute(Home) },
      { path: "/browse", element: lazyRoute(Browse) },
      { path: "/search", element: lazyRoute(Search) },
      { path: "/title/:id", element: lazyRoute(TitleDetail) },
      { path: "/title/:titleId/season/:seasonNumber", element: lazyRoute(SeasonPage) },
      // /watch needs auth — anonymous users get redirected to /login with
      // ?from=/watch/... so they return to playback after login. Previously
      // anonymous click-Play landed here and surfaced a 401 with no Sign-In
      // CTA. ProtectedRoute now bounces them cleanly.
      {
        path: "/watch/:kind/:id",
        element: <ProtectedRoute>{lazyRoute(Watch)}</ProtectedRoute>,
      },
      {
        path: "/subscribe",
        element: <ProtectedRoute>{lazyRoute(Subscribe)}</ProtectedRoute>,
      },
      {
        path: "/me/list",
        element: <ProtectedRoute>{lazyRoute(MyList)}</ProtectedRoute>,
      },
      {
        path: "/me/history",
        element: <ProtectedRoute>{lazyRoute(History)}</ProtectedRoute>,
      },
      {
        path: "/admin",
        element: (
          <ProtectedRoute roles={["admin", "content_manager"]}>
            {lazyRoute(AdminLayout)}
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: lazyRoute(AdminDashboard) },
          { path: "titles", element: lazyRoute(AdminTitlesList) },
          { path: "titles/new", element: lazyRoute(TitleEditor) },
          { path: "titles/:id", element: lazyRoute(TitleEditor) },
          {
            path: "users",
            element: <ProtectedRoute roles={["admin"]}>{lazyRoute(AdminUsers)}</ProtectedRoute>,
          },
          {
            path: "audit",
            element: <ProtectedRoute roles={["admin"]}>{lazyRoute(AuditLog)}</ProtectedRoute>,
          },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
