import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import type { AuthUser } from "../stores/auth";

/**
 * Wrap any element to require auth + optional roles.
 * Unauthed users redirect to /login with ?from= so they return after.
 */
export default function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: AuthUser["role"][];
}) {
  const loc = useLocation();
  const { isLoggedIn, hasRole } = useAuthStore();
  if (!isLoggedIn()) {
    return <Navigate to="/login" state={{ from: loc.pathname + loc.search }} replace />;
  }
  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
