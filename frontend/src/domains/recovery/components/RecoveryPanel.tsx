import clsx from "clsx";
import type { RecoveryStatus } from "@/domains/recovery/api/recoveryApi";
import {
  useResumeProcess,
  useSnapshotNow,
  useUpdateRecoverySettings,
} from "@/domains/recovery/hooks/useRecovery";
import { useHasRole } from "@/domains/auth/hooks/useAuth";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface ToggleProps {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
}

function Toggle({ label, checked, disabled, onChange }: ToggleProps) {
  return (
    <label className={clsx("flex items-center justify-between text-xs", disabled ? "text-surface-400" : "text-surface-200")}>
      {label}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={clsx(
          "relative h-5 w-9 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60",
          checked ? "bg-teal-500" : "bg-surface-700"
        )}
      >
        <span
          className={clsx(
            "absolute top-0.5 h-4 w-4 rounded-full bg-surface-100 transition-transform",
            checked ? "translate-x-4" : "translate-x-0.5"
          )}
        />
      </button>
    </label>
  );
}

interface RecoveryPanelProps {
  status: RecoveryStatus | undefined;
  monitorRunning: boolean;
}

export function RecoveryPanel({ status, monitorRunning }: RecoveryPanelProps) {
  const isAdmin = useHasRole("admin");
  const canAct = useHasRole("admin", "analyst");
  const updateSettings = useUpdateRecoverySettings();
  const snapshot = useSnapshotNow();
  const resume = useResumeProcess();

  if (!status) return null;

  const armed = status.auto_response;
  const stats = [
    { label: "Files protected", value: status.files_protected.toLocaleString() },
    { label: "Versions", value: status.versions_stored.toLocaleString() },
    { label: "Vault size", value: formatBytes(status.vault_size_bytes) },
    { label: "Quarantined", value: status.quarantined_files.toLocaleString() },
  ];

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-surface-100">Automated recovery</h2>
        <span
          className={clsx(
            "rounded-full px-2.5 py-1 text-xs font-medium",
            status.active_incident_id
              ? "bg-danger-500/15 text-danger-400"
              : armed
                ? "bg-teal-500/10 text-teal-400"
                : "bg-amber-500/10 text-amber-400"
          )}
        >
          {status.active_incident_id ? "Responding" : armed ? "Armed" : "Alert only"}
        </span>
      </div>

      <dl className="mb-4 grid grid-cols-2 gap-3 font-mono text-sm">
        {stats.map((s) => (
          <div key={s.label}>
            <dt className="text-xs text-surface-400">{s.label}</dt>
            <dd className="text-surface-100">{s.value}</dd>
          </div>
        ))}
      </dl>

      <div className="space-y-2 border-t border-surface-700 pt-4">
        <Toggle
          label="Auto quarantine & restore"
          checked={status.auto_response}
          disabled={!isAdmin || updateSettings.isPending}
          onChange={(v) => updateSettings.mutate({ auto_response: v })}
        />
        <Toggle
          label="Auto suspend process"
          checked={status.auto_suspend}
          disabled={!isAdmin || updateSettings.isPending || !status.auto_response}
          onChange={(v) => updateSettings.mutate({ auto_suspend: v })}
        />
        <p className="text-xs text-surface-400">
          Acts at ≥{Math.round(status.confidence_threshold * 100)}% confidence.
          {!isAdmin && " Only admins can change these."}
        </p>
      </div>

      {status.suspended_processes.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-surface-700 pt-4">
          <h3 className="text-xs font-medium text-danger-400">Suspended processes</h3>
          {status.suspended_processes.map((p) => (
            <div key={p.pid} className="flex items-center justify-between gap-2 font-mono text-xs">
              <span className="truncate text-surface-100" title={p.name}>
                {p.name} <span className="text-surface-400">#{p.pid}</span>
              </span>
              <button
                onClick={() => resume.mutate(p.pid)}
                disabled={!canAct || resume.isPending}
                className="rounded border border-surface-700 px-2 py-0.5 text-surface-200 hover:bg-surface-700 disabled:opacity-50"
              >
                Resume
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => snapshot.mutate()}
        disabled={!canAct || snapshot.isPending || !monitorRunning}
        title={monitorRunning ? undefined : "Start monitoring first; snapshots are taken of the watched folder"}
        className="mt-4 w-full rounded-md border border-surface-700 px-4 py-2 text-sm text-surface-200 transition-colors hover:bg-surface-700 disabled:opacity-50"
      >
        {snapshot.isPending ? "Snapshotting…" : "Snapshot watched folder now"}
      </button>
      {snapshot.isError && (
        <p className="mt-2 text-xs text-danger-400">
          {(snapshot.error as { message?: string })?.message ?? "Snapshot failed."}
        </p>
      )}
      <p className="mt-3 truncate font-mono text-xs text-surface-400" title={status.vault_path}>
        vault: {status.vault_path}
      </p>
    </div>
  );
}
