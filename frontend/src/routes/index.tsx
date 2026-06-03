import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import ProtectedRoute from "../components/ProtectedRoute";

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

export const router = createBrowserRouter([
  // Auth routes — rendered WITHOUT AppLayout so the Netflix-style full-bleed
  // hero card has no navbar/footer chrome around it.
  { path: "/login", element: lazyRoute(Login) },
  { path: "/signup", element: lazyRoute(Signup) },
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: lazyRoute(Home) },
      { path: "/browse", element: lazyRoute(Browse) },
      { path: "/search", element: lazyRoute(Search) },
      { path: "/title/:id", element: lazyRoute(TitleDetail) },
      { path: "/title/:titleId/season/:seasonNumber", element: lazyRoute(SeasonPage) },
      { path: "/watch/:kind/:id", element: lazyRoute(Watch) },
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
