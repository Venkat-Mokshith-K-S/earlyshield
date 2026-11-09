import { useOAuthProviders } from "@/domains/auth/hooks/useAuth";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" aria-hidden="true">
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.7Z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z" />
      <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="#0E1020" aria-hidden="true">
      <path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2.1c-3.2.7-3.9-1.4-3.9-1.4-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.9 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

const PROVIDERS = [
  { id: "google", label: "Google", Icon: GoogleIcon },
  { id: "github", label: "GitHub", Icon: GitHubIcon },
] as const;

/**
 * "Or sign in with" Google / GitHub. These are plain links, not API calls:
 * the browser itself has to travel to the provider and back.
 */
export function SocialSignIn() {
  const { data: enabled } = useOAuthProviders();

  return (
    <div>
      <div className="my-6 flex items-center gap-3 text-xs text-surface-400">
        <span className="h-px flex-1 border-t border-dashed border-surface-600" />
        Or sign in with
        <span className="h-px flex-1 border-t border-dashed border-surface-600" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {PROVIDERS.map(({ id, label, Icon }) => {
          const ready = enabled?.[id] ?? false;
          const common =
            "flex h-12 items-center justify-center gap-2 rounded-xl border border-surface-700 bg-white text-sm font-medium text-surface-200 shadow-[0_1px_2px_rgba(14,16,32,0.05)] transition";
          return ready ? (
            <a key={id} href={`/api/v1/auth/oauth/${id}/login`} className={`${common} hover:border-surface-600 hover:bg-surface-900`}>
              <Icon />
              {label}
            </a>
          ) : (
            <span
              key={id}
              aria-disabled="true"
              title={`${label} sign-in isn't configured on this server yet`}
              className={`${common} cursor-not-allowed opacity-50`}
            >
              <Icon />
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

const OAUTH_ERRORS: Record<string, string> = {
  cancelled: "Sign-in was cancelled.",
  not_configured: "That sign-in option isn't set up on this server yet.",
  email_not_verified: "Your account there has no verified email address, so we can't sign you in with it.",
  account_deactivated: "This account has been deactivated. Ask an administrator to re-enable it.",
  invalid_state: "That sign-in link expired or was opened in a different browser. Please try again.",
  provider_error: "We couldn't reach the sign-in provider. Please try again.",
};

export function oauthErrorMessage(code: string | null): string | null {
  if (!code) return null;
  return OAUTH_ERRORS[code] ?? "Sign-in failed. Please try again.";
}
