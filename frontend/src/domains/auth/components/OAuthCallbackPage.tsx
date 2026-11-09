import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAcceptTokens } from "@/domains/auth/hooks/useAuth";

/**
 * Landing spot after Google/GitHub sign-in. The backend puts our tokens in
 * the URL fragment (never sent to any server); we store them, wipe them
 * from the address bar and history, and go to the dashboard.
 */
export function OAuthCallbackPage() {
  const accept = useAcceptTokens();
  const navigate = useNavigate();
  // Read once: the fragment is wiped below, and later renders must not see it as missing.
  const [{ access, refresh }] = useState(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    return { access: params.get("access_token"), refresh: params.get("refresh_token") };
  });
  const done = useRef(false);

  useEffect(() => {
    if (done.current || !access || !refresh) return;
    done.current = true;
    window.history.replaceState(null, "", window.location.pathname);
    accept({ access_token: access, refresh_token: refresh });
    navigate("/dashboard", { replace: true });
  }, [access, refresh, accept, navigate]);

  if (!access || !refresh) return <Navigate to="/login?oauth_error=provider_error" replace />;
  return (
    <div className="bg-hero flex min-h-screen items-center justify-center">
      <span className="text-sm text-white/70">Signing you in…</span>
    </div>
  );
}
