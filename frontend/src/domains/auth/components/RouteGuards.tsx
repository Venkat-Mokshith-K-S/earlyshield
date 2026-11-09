import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useCurrentUser, useHasRole, useHasToken, useLogout } from "@/domains/auth/hooks/useAuth";

/** Only renders `children` for a signed-in user; otherwise sends them to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const hasToken = useHasToken();
  const { data: user, isError, error, refetch } = useCurrentUser();
  const { logout } = useLogout();
  const location = useLocation();

  if (!hasToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // An expired session clears the token (and lands in the branch above), so
  // an error here is something else: backend down, or account deactivated.
  if (isError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-950 px-4">
        <div className="w-full max-w-sm space-y-4 card p-6 text-center">
          <p className="text-sm text-surface-200">
            {(error as { message?: string })?.message ?? "Could not load your account."}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => refetch()}
              className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500"
            >
              Retry
            </button>
            <button
              onClick={logout}
              className="rounded-md border border-surface-600 px-4 py-2 text-sm text-surface-300 hover:bg-surface-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-950">
        <span className="text-sm text-surface-400">Loading…</span>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Hides a page from roles that can't use it. Only a convenience: the API
 * enforces the same rule and answers 403 regardless.
 */
export function RequireRole({ role, children }: { role: "admin" | "analyst"; children: ReactNode }) {
  const allowed = useHasRole(...(role === "admin" ? (["admin"] as const) : (["admin", "analyst"] as const)));
  if (!allowed) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

/** Login/register pages: a signed-in user has no business there. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const hasToken = useHasToken();
  if (hasToken) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
