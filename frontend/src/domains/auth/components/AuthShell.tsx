import { useState, type InputHTMLAttributes, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { BrandMark } from "@/shared/components/BrandMark";

/**
 * Shared frame for sign-in / sign-up: the blue hero wash behind a soft
 * white card with an icon tile, title and subtitle.
 */
export function AuthShell({
  icon,
  title,
  subtitle,
  children,
  footer,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="bg-hero relative flex min-h-screen flex-col overflow-hidden">
      <div className="grid-lines pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
      <header className="relative mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5">
        <Link to="/" aria-label="EarlyShield home">
          <BrandMark tone="light" />
        </Link>
        <Link to="/" className="text-[13px] text-white/60 transition hover:text-white">
          ← Back to home
        </Link>
      </header>

      <main className="relative flex flex-1 items-center justify-center px-4 pb-16">
        <div className="w-full max-w-[400px] rounded-[28px] bg-gradient-to-b from-[#E4EDFF] via-white to-white p-8 shadow-[0_30px_80px_-20px_rgba(5,6,13,0.55)] ring-1 ring-white/60 sm:p-9">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-surface-100 shadow-[0_6px_20px_-6px_rgba(14,16,32,0.25)] ring-1 ring-surface-700">
            {icon}
          </div>
          <h1 className="mt-5 text-center text-[22px] font-semibold tracking-tight text-surface-100">{title}</h1>
          <p className="mx-auto mt-2 max-w-[290px] text-center text-[14px] leading-snug text-surface-400">{subtitle}</p>
          <div className="mt-7">{children}</div>
          <div className="mt-6 text-center text-[13px] text-surface-400">{footer}</div>
        </div>
      </main>
    </div>
  );
}

const ICONS = {
  mail: (
    <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h11A1.5 1.5 0 0 1 17 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 13.5v-7Zm1.2.3L10 10.6l5.8-3.8" />
  ),
  lock: <path d="M6 9V7a4 4 0 1 1 8 0v2m-9 0h10a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1Z" />,
  user: <path d="M10 10a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Zm-6 6.4c.6-2.9 3-4.6 6-4.6s5.4 1.7 6 4.6" />,
};

/** Text field with a leading icon; password fields get a show/hide toggle. */
export function IconField({
  icon,
  label,
  type = "text",
  ...props
}: { icon: keyof typeof ICONS; label: string } & InputHTMLAttributes<HTMLInputElement>) {
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";

  return (
    <label className="relative block">
      <span className="sr-only">{label}</span>
      <svg
        viewBox="0 0 20 20"
        className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-surface-400"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {ICONS[icon]}
      </svg>
      <input
        {...props}
        type={isPassword && revealed ? "text" : type}
        placeholder={label}
        className="field h-12 pl-11 pr-11"
      />
      {isPassword && (
        <button
          type="button"
          onClick={() => setRevealed((r) => !r)}
          aria-label={revealed ? "Hide password" : "Show password"}
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-surface-400 transition hover:text-surface-200"
        >
          <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
            <path d="M2 10s3-5.5 8-5.5S18 10 18 10s-3 5.5-8 5.5S2 10 2 10Z" />
            <circle cx="10" cy="10" r="2.4" />
            {!revealed && <path d="M3.5 3.5l13 13" />}
          </svg>
        </button>
      )}
    </label>
  );
}

export function FormAlert({ tone, children }: { tone: "error" | "success"; children: ReactNode }) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={
        tone === "error"
          ? "rounded-xl border border-danger-500/25 bg-danger-500/5 px-3.5 py-2.5 text-[13px] text-danger-600"
          : "rounded-xl border border-teal-500/25 bg-teal-500/5 px-3.5 py-2.5 text-[13px] text-teal-300"
      }
    >
      {children}
    </div>
  );
}
