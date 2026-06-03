import { createBrowserRouter, RouterProvider } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import ProtectedRoute from "../components/ProtectedRoute";
import Home from "../pages/Home";
import Browse from "../pages/Browse";
import Search from "../pages/Search";
import TitleDetail from "../pages/TitleDetail";
import SeasonPage from "../pages/Season";
import Watch from "../pages/Watch";
import MyList from "../pages/MyList";
import History from "../pages/History";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import Subscribe from "../pages/Subscribe";
import AdminLayout from "../pages/admin/AdminLayout";
import AdminDashboard from "../pages/admin/Dashboard";
import AdminTitlesList from "../pages/admin/TitlesList";
import TitleEditor from "../pages/admin/TitleEditor";
import AuditLog from "../pages/admin/AuditLog";
import AdminUsers from "../pages/admin/Users";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/browse", element: <Browse /> },
      { path: "/search", element: <Search /> },
      { path: "/title/:id", element: <TitleDetail /> },
      { path: "/title/:titleId/season/:seasonNumber", element: <SeasonPage /> },
      { path: "/watch/:kind/:id", element: <Watch /> },
      { path: "/login", element: <Login /> },
      { path: "/signup", element: <Signup /> },
      {
        path: "/subscribe",
        element: (
          <ProtectedRoute>
            <Subscribe />
          </ProtectedRoute>
        ),
      },
      {
        path: "/me/list",
        element: (
          <ProtectedRoute>
            <MyList />
          </ProtectedRoute>
        ),
      },
      {
        path: "/me/history",
        element: (
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        ),
      },
      {
        path: "/admin",
        element: (
          <ProtectedRoute roles={["admin", "content_manager"]}>
            <AdminLayout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <AdminDashboard /> },
          { path: "titles", element: <AdminTitlesList /> },
          { path: "titles/new", element: <TitleEditor /> },
          { path: "titles/:id", element: <TitleEditor /> },
          {
            path: "users",
            element: (
              <ProtectedRoute roles={["admin"]}>
                <AdminUsers />
              </ProtectedRoute>
            ),
          },
          {
            path: "audit",
            element: (
              <ProtectedRoute roles={["admin"]}>
                <AuditLog />
              </ProtectedRoute>
            ),
          },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
