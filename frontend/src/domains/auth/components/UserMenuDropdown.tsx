import { useState, useRef, useEffect } from "react";
import { useCurrentUser, useLogout } from "@/domains/auth/hooks/useAuth";

const roleBadgeColors: Record<string, string> = {
  admin: "bg-danger-500/10 text-danger-600",
  analyst: "bg-teal-500/10 text-teal-300",
  viewer: "bg-surface-900 text-surface-300",
};

export function UserMenuDropdown() {
  const { data: user } = useCurrentUser();
  const { logout } = useLogout();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!user) return null;

  const initials = user.full_name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-xl bg-surface-100 py-1 pl-1 pr-3 text-[13px] font-medium text-white transition hover:bg-surface-200"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-b from-electric-400 to-electric-600 text-[11px] font-semibold text-white">
          {initials}
        </span>
        <span className="hidden sm:inline">{user.full_name}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-2xl border border-surface-700 bg-surface-800 py-2 shadow-card z-50">
          <div className="px-4 py-2 border-b border-surface-700">
            <p className="text-sm font-medium text-surface-100">{user.full_name}</p>
            <p className="text-xs text-surface-400 truncate">{user.email}</p>
            <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeColors[user.role] || roleBadgeColors.viewer}`}>
              {user.role}
            </span>
          </div>
          <button
            onClick={() => { logout(); setOpen(false); }}
            className="w-full px-4 py-2 text-left text-sm text-surface-300 hover:bg-surface-900 hover:text-surface-100 transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
