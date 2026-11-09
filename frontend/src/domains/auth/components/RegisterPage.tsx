import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegister } from "@/domains/auth/hooks/useAuth";
import { AuthShell, FormAlert, IconField } from "@/domains/auth/components/AuthShell";
import { SocialSignIn } from "@/domains/auth/components/SocialSignIn";

export function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const register = useRegister();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);
    if (password !== confirmPassword) {
      setClientError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setClientError("Password must be at least 8 characters");
      return;
    }
    register.mutate(
      { email, password, full_name: fullName },
      { onSuccess: () => navigate("/login", { state: { registered: true } }) }
    );
  };

  const errorMessage = clientError || (register.isError ? ((register.error as { message?: string })?.message || "Registration failed") : null);

  return (
    <AuthShell
      icon={
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 3 5 5.8v5.6c0 4.3 3 7.7 7 8.8 4-1.1 7-4.5 7-8.8V5.8L12 3Zm0 6v6m-3-3h6" />
        </svg>
      }
      title="Create your account"
      subtitle="Protect a folder in minutes. The first account on a new install becomes the admin."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-surface-100 underline-offset-4 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        {errorMessage && <FormAlert tone="error">{errorMessage}</FormAlert>}
        <IconField icon="user" label="Full name" autoComplete="name" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <IconField icon="mail" label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <IconField
          icon="lock"
          label="Password (min. 8 characters)"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <IconField
          icon="lock"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
        <button type="submit" disabled={register.isPending} className="btn-ink mt-2 h-12 w-full rounded-xl bg-gradient-to-b from-[#2A2D3A] to-[#0E1020] text-[15px] shadow-[0_8px_20px_-8px_rgba(14,16,32,0.6)]">
          {register.isPending ? "Creating account…" : "Create account"}
        </button>
      </form>

      <SocialSignIn />
    </AuthShell>
  );
}
