import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useLogin } from "@/domains/auth/hooks/useAuth";
import { AuthShell, FormAlert, IconField } from "@/domains/auth/components/AuthShell";
import { SocialSignIn, oauthErrorMessage } from "@/domains/auth/components/SocialSignIn";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const state = location.state as { from?: string; registered?: boolean } | null;
  const oauthError = oauthErrorMessage(params.get("oauth_error"));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate(
      { email, password },
      { onSuccess: () => navigate(state?.from ?? "/dashboard", { replace: true }) }
    );
  };

  return (
    <AuthShell
      icon={
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M4 12h11m-4-4 4 4-4 4" />
        </svg>
      }
      title="Sign in with email"
      subtitle="Watch your files, see why every alert fired, and restore in one click."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link to="/register" className="font-medium text-surface-100 underline-offset-4 hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        {state?.registered && !login.isError && <FormAlert tone="success">Account created. Sign in to continue.</FormAlert>}
        {oauthError && !login.isError && <FormAlert tone="error">{oauthError}</FormAlert>}
        {login.isError && (
          <FormAlert tone="error">{(login.error as { message?: string })?.message || "Login failed. Please try again."}</FormAlert>
        )}

        <IconField icon="mail" label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <IconField
          icon="lock"
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button type="submit" disabled={login.isPending} className="btn-ink mt-2 h-12 w-full rounded-xl bg-gradient-to-b from-[#2A2D3A] to-[#0E1020] text-[15px] shadow-[0_8px_20px_-8px_rgba(14,16,32,0.6)]">
          {login.isPending ? "Signing in…" : "Get Started"}
        </button>
      </form>

      <SocialSignIn />
    </AuthShell>
  );
}
