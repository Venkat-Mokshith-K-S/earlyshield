import clsx from "clsx";
import type { RecoveryAction, RecoveryActionType } from "@/domains/recovery/api/recoveryApi";

const ACTION_LABELS: Record<RecoveryActionType, string> = {
  baseline_snapshot: "Baseline snapshot",
  manual_snapshot: "Manual snapshot",
  suspend_process: "Suspend process",
  resume_process: "Resume process",
  quarantine_file: "Quarantine",
  restore_file: "Restore",
  incident_summary: "Incident",
};

const STATUS_STYLES: Record<RecoveryAction["status"], string> = {
  success: "text-teal-400",
  skipped: "text-amber-400",
  failed: "text-danger-400",
};

function shortTarget(target: string | null): string {
  if (!target) return "";
  // Paths: show just the file name; the full path is in the tooltip.
  const parts = target.split(/[\\/]/);
  return parts[parts.length - 1] || target;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function RecoveryActionLog({ actions }: { actions: RecoveryAction[] }) {
  if (actions.length === 0) {
    return (
      <div className="flex h-20 items-center justify-center rounded-lg border border-dashed border-surface-700 text-sm text-surface-400">
        No recovery actions yet. A baseline snapshot is taken when monitoring starts.
      </div>
    );
  }

  return (
    <ul className="max-h-80 divide-y divide-surface-700 overflow-y-auto">
      {actions.map((a) => (
        <li
          key={a.id}
          className={clsx("py-2.5 text-sm", a.action_type === "incident_summary" && "rounded-md bg-danger-500/5 px-2")}
        >
          <div className="flex items-baseline justify-between gap-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <span className={clsx("font-mono text-xs uppercase", STATUS_STYLES[a.status])}>{a.status}</span>
              <span className="font-medium text-surface-100">{ACTION_LABELS[a.action_type] ?? a.action_type}</span>
              {a.target && (
                <span className="truncate font-mono text-xs text-surface-200" title={a.target}>
                  {shortTarget(a.target)}
                </span>
              )}
            </div>
            <span className="flex-shrink-0 font-mono text-xs text-surface-400">{formatTime(a.created_at)}</span>
          </div>
          <p className="mt-0.5 text-xs text-surface-400">
            {a.detail}
            {a.triggered_by !== "auto" && <span> · by {a.triggered_by}</span>}
          </p>
        </li>
      ))}
    </ul>
  );
}
