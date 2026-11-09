import { useState } from "react";
import type { MonitorStatus } from "@/domains/monitoring/api/monitoringApi";
import { useStartMonitor, useStopMonitor } from "@/domains/monitoring/hooks/useMonitoring";
import { useHasRole } from "@/domains/auth/hooks/useAuth";

interface MonitorControlPanelProps {
  status: MonitorStatus | undefined;
}

export function MonitorControlPanel({ status }: MonitorControlPanelProps) {
  // Matches the folder created by `python -m evaluation.demo setup` (see DEMO.md).
  const [watchPath, setWatchPath] = useState("/watched/demo_files");
  const [windowSeconds, setWindowSeconds] = useState(10);
  const startMonitor = useStartMonitor();
  const stopMonitor = useStopMonitor();

  const isRunning = status?.is_running ?? false;
  // Mirrors the backend rule; the server still enforces it on its own.
  const canControl = useHasRole("admin", "analyst");

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-surface-100">Live monitor</h2>
        <span
          className={
            isRunning
              ? "flex items-center gap-1.5 rounded-full bg-teal-500/10 px-2.5 py-1 text-xs font-medium text-teal-400"
              : "flex items-center gap-1.5 rounded-full bg-surface-700 px-2.5 py-1 text-xs font-medium text-surface-400"
          }
        >
          <span
            className={
              isRunning ? "h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse" : "h-1.5 w-1.5 rounded-full bg-surface-400"
            }
          />
          {isRunning ? "Watching" : "Idle"}
        </span>
      </div>

      {isRunning ? (
        <div className="space-y-3">
          <dl className="grid grid-cols-2 gap-3 font-mono text-sm">
            <div>
              <dt className="text-xs text-surface-400">Path</dt>
              <dd className="truncate text-surface-100">{status?.watch_path}</dd>
            </div>
            <div>
              <dt className="text-xs text-surface-400">Window</dt>
              <dd className="text-surface-100">{status?.window_seconds}s</dd>
            </div>
            <div>
              <dt className="text-xs text-surface-400">Windows processed</dt>
              <dd className="text-surface-100">{status?.windows_processed}</dd>
            </div>
          </dl>
          <button
            onClick={() => stopMonitor.mutate()}
            disabled={stopMonitor.isPending || !canControl}
            className="w-full rounded-md border border-danger-500/40 bg-danger-500/10 px-4 py-2 text-sm font-medium text-danger-400 transition-colors hover:bg-danger-500/20 disabled:opacity-50"
          >
            {stopMonitor.isPending ? "Stopping…" : "Stop monitoring"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-surface-400" htmlFor="watch-path">
              Directory to watch
            </label>
            <input
              id="watch-path"
              type="text"
              value={watchPath}
              onChange={(e) => setWatchPath(e.target.value)}
              className="w-full rounded-md border border-surface-700 bg-surface-900 px-3 py-2 font-mono text-sm text-surface-100 focus:border-teal-500"
              placeholder="/watched"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-surface-400" htmlFor="window-seconds">
              Observation window (seconds)
            </label>
            <input
              id="window-seconds"
              type="number"
              min={2}
              max={120}
              value={windowSeconds}
              onChange={(e) => setWindowSeconds(Number(e.target.value))}
              className="w-full rounded-md border border-surface-700 bg-surface-900 px-3 py-2 font-mono text-sm text-surface-100 focus:border-teal-500"
            />
          </div>
          <button
            onClick={() => startMonitor.mutate({ watchPath, windowSeconds })}
            disabled={startMonitor.isPending || !watchPath || !canControl}
            className="w-full rounded-md bg-teal-500 px-4 py-2 text-sm font-medium text-surface-950 transition-colors hover:bg-teal-400 disabled:opacity-50"
          >
            {startMonitor.isPending ? "Starting…" : "Start monitoring"}
          </button>
          {!canControl && (
            <p className="text-xs text-surface-400">Viewers can watch results but not start or stop the monitor.</p>
          )}
          {startMonitor.isError && (
            <p className="text-xs text-danger-400">
              {(startMonitor.error as { message?: string })?.message ?? "Could not start the monitor."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
