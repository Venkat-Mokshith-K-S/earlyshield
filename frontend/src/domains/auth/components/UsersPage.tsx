import clsx from "clsx";
import { useAdminUpdateUser, useCurrentUser, useUsers } from "@/domains/auth/hooks/useAuth";
import type { UserProfile } from "@/domains/auth/api/authApi";

const ROLES: UserProfile["role"][] = ["admin", "analyst", "viewer"];

const ROLE_HELP: Record<UserProfile["role"], string> = {
  admin: "everything, including these settings",
  analyst: "start/stop monitoring, snapshot, restore, resume",
  viewer: "read-only",
};

export function UsersPage() {
  const { data: me } = useCurrentUser();
  const { data: users = [], isLoading, isError, error } = useUsers(me?.role === "admin");
  const update = useAdminUpdateUser();

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-6 py-10">
      <div>
        <h2 className="headline text-[2.5rem]"><span className="text-surface-100">People with access,</span>{" "}<span className="bg-gradient-to-r from-electric-500 to-electric-300 bg-clip-text text-transparent">who can do what</span></h2>
        <p className="mt-1 text-sm text-surface-400">
          Change roles or deactivate accounts. Changes apply on the user's next request; a deactivated user is signed
          out immediately. You can't demote or deactivate yourself, so the system always keeps an admin.
        </p>
      </div>

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {ROLES.map((r) => (
          <div key={r} className="card px-4 py-3">
            <dt className="text-sm font-medium capitalize text-surface-100">{r}</dt>
            <dd className="text-xs text-surface-400">{ROLE_HELP[r]}</dd>
          </div>
        ))}
      </dl>

      {update.isError && (
        <p className="rounded-md border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-400">
          {(update.error as { message?: string })?.message ?? "Update failed."}
        </p>
      )}

      <div className="overflow-x-auto card">
        {isLoading ? (
          <p className="px-4 py-6 text-sm text-surface-400">Loading…</p>
        ) : isError ? (
          <p className="px-4 py-6 text-sm text-danger-400">{(error as { message?: string })?.message}</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-surface-400">
              <tr className="border-b border-surface-700">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-2 py-3 font-medium">Email</th>
                <th className="px-2 py-3 font-medium">Role</th>
                <th className="px-2 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Last login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {users.map((u) => {
                const isMe = u.id === me?.id;
                return (
                  <tr key={u.id}>
                    <td className="px-4 py-3 text-surface-100">
                      {u.full_name}
                      {isMe && <span className="ml-2 text-xs text-surface-400">(you)</span>}
                    </td>
                    <td className="px-2 py-3 font-mono text-xs text-surface-200">{u.email}</td>
                    <td className="px-2 py-3">
                      <select
                        value={u.role}
                        disabled={isMe || update.isPending}
                        onChange={(e) => update.mutate({ id: u.id, role: e.target.value as UserProfile["role"] })}
                        aria-label={`Role for ${u.full_name}`}
                        className="rounded-md border border-surface-700 bg-surface-900 px-2 py-1 text-sm capitalize text-surface-100 disabled:opacity-60"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-3">
                      <button
                        onClick={() => update.mutate({ id: u.id, is_active: !u.is_active })}
                        disabled={isMe || update.isPending}
                        className={clsx(
                          "rounded-full px-2.5 py-1 text-xs font-medium disabled:opacity-60",
                          u.is_active ? "bg-teal-500/10 text-teal-400" : "bg-surface-700 text-surface-400"
                        )}
                        title={isMe ? "You can't deactivate yourself" : u.is_active ? "Click to deactivate" : "Click to activate"}
                      >
                        {u.is_active ? "Active" : "Deactivated"}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-surface-200">
                      {u.last_login ? new Date(u.last_login).toLocaleString() : "never"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
