import { useEffect, useState } from "react";
import { useChangePassword, useCurrentUser, useUpdateProfile } from "@/domains/auth/hooks/useAuth";

const inputClass =
  "w-full rounded-md border border-surface-600 bg-surface-900 px-3 py-2 text-sm text-surface-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500";

export function AccountPage() {
  const { data: user } = useCurrentUser();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();

  const [fullName, setFullName] = useState("");
  useEffect(() => setFullName(user?.full_name ?? ""), [user?.full_name]);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);

  const submitPassword = (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    if (next !== confirm) return setPwError("New passwords do not match");
    if (next.length < 8) return setPwError("New password must be at least 8 characters");
    changePassword.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setCurrent("");
          setNext("");
          setConfirm("");
        },
      }
    );
  };

  if (!user) return null;

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-10">
      <h2 className="headline text-[2.5rem]"><span className="text-surface-100">Your account,</span>{" "}<span className="bg-gradient-to-r from-electric-500 to-electric-300 bg-clip-text text-transparent">your sign-in</span></h2>

      <section className="space-y-4 card p-6">
        <h3 className="text-sm font-medium text-surface-100">Profile</h3>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-xs text-surface-400">Email</dt>
            <dd className="font-mono text-surface-100">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-surface-400">Role</dt>
            <dd className="capitalize text-surface-100">{user.role}</dd>
          </div>
        </dl>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateProfile.mutate({ full_name: fullName.trim() });
          }}
          className="space-y-3"
        >
          <label htmlFor="full-name" className="block text-xs text-surface-400">
            Full name
          </label>
          <input id="full-name" value={fullName} onChange={(e) => setFullName(e.target.value)} required className={inputClass} />
          <button
            type="submit"
            disabled={updateProfile.isPending || !fullName.trim() || fullName.trim() === user.full_name}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
          >
            {updateProfile.isPending ? "Saving…" : "Save name"}
          </button>
          {updateProfile.isSuccess && <p className="text-xs text-teal-400">Saved.</p>}
        </form>
      </section>

      <section className="card p-6">
        <h3 className="text-sm font-medium text-surface-100">Change password</h3>
        <p className="mt-1 text-xs text-surface-400">
          Changing your password signs you out on every other device; this browser stays signed in.
        </p>
        <form onSubmit={submitPassword} className="mt-4 space-y-3">
          <input type="password" placeholder="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} required className={inputClass} aria-label="Current password" />
          <input type="password" placeholder="New password (min. 8 characters)" value={next} onChange={(e) => setNext(e.target.value)} required className={inputClass} aria-label="New password" />
          <input type="password" placeholder="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required className={inputClass} aria-label="Confirm new password" />
          {(pwError || changePassword.isError) && (
            <p className="text-xs text-danger-400">
              {pwError ?? (changePassword.error as { message?: string })?.message ?? "Could not change password."}
            </p>
          )}
          {changePassword.isSuccess && <p className="text-xs text-teal-400">Password changed. Other sessions were signed out.</p>}
          <button
            type="submit"
            disabled={changePassword.isPending}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
          >
            {changePassword.isPending ? "Changing…" : "Change password"}
          </button>
        </form>
      </section>
    </main>
  );
}
