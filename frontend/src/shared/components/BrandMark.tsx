import clsx from "clsx";

/** The EarlyShield logo: a shield cut by a pulse line, plus the wordmark. */
export function BrandMark({ tone = "dark", className }: { tone?: "dark" | "light"; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true">
        <path
          d="M12 2.5 4 5.6v6.1c0 4.8 3.3 8.6 8 9.8 4.7-1.2 8-5 8-9.8V5.6L12 2.5Z"
          fill={tone === "light" ? "#ffffff" : "#0E1020"}
        />
        <path
          d="M6.5 12.2h3l1.4-3 2.2 6 1.5-3h2.9"
          fill="none"
          stroke={tone === "light" ? "#3B5BFD" : "#8FA2FF"}
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span
        className={clsx(
          "text-[17px] font-medium tracking-tight",
          tone === "light" ? "text-white" : "text-surface-100"
        )}
      >
        EarlyShield
      </span>
    </span>
  );
}
