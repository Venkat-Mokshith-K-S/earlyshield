import { Link, NavLink } from "react-router-dom";
import clsx from "clsx";
import { useSystemHealth, useSystemVersion } from "@/domains/system/hooks/useSystemHealth";
import { UserMenuDropdown } from "@/domains/auth/components/UserMenuDropdown";
import { useHasRole } from "@/domains/auth/hooks/useAuth";
import { BrandMark } from "@/shared/components/BrandMark";

const navClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "relative px-5 py-1.5 text-[13px] transition",
    isActive ? "font-medium text-surface-100" : "text-surface-400 hover:text-surface-100"
  );

function NavTabs({ compact = false }: { compact?: boolean }) {
  const isAdmin = useHasRole("admin");
  const links: [string, string][] = [
    ["/dashboard", "Dashboard"],
    ["/files", "Protected files"],
    ...(isAdmin ? ([["/users", "Users"]] as [string, string][]) : []),
    ["/account", "Account"],
  ];
  return (
    <nav className="flex items-center divide-x divide-surface-700 border-x border-surface-700" aria-label="Main">
      {links.map(([to, label]) => (
        <NavLink key={to} to={to} className={navClass}>
          {({ isActive }) => (
            <>
              {label}
              {isActive && <span className={clsx("absolute inset-x-5 h-[2px] rounded-full bg-teal-500", compact ? "bottom-0" : "-bottom-[15px]")} />}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

export function TopStatusBar() {
  const { data: health } = useSystemHealth();
  const { data: version } = useSystemVersion();

  const connected = health?.status === "ok";

  return (
    <header className="sticky top-0 z-40 border-b border-surface-700 bg-surface-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        <Link to="/" title={version?.project_full_title} aria-label="EarlyShield home">
          <BrandMark />
        </Link>
        <div className="hidden md:block">
          <NavTabs />
        </div>
        <div className="flex items-center gap-3">
          {version && <span className="hidden font-mono text-[11px] text-surface-500 lg:inline">v{version.version}</span>}
          <span
            className={clsx(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
              connected ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"
            )}
          >
            <span className={clsx("h-1.5 w-1.5 rounded-full", connected ? "es-pulse bg-emerald-500" : "bg-amber-500")} />
            {connected ? "Connected" : "Degraded"}
          </span>
          <UserMenuDropdown />
        </div>
      </div>
      <div className="overflow-x-auto border-t border-surface-700 px-6 py-2 md:hidden">
        <NavTabs compact />
      </div>
    </header>
  );
}
