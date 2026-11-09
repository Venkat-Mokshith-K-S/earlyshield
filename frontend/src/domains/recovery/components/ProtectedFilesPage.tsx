import { useMemo, useState } from "react";
import clsx from "clsx";
import { useProtectedFiles, useRestoreFiles } from "@/domains/recovery/hooks/useRecovery";
import { useHasRole } from "@/domains/auth/hooks/useAuth";

function formatTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "—";
}

export function ProtectedFilesPage() {
  const { data: files = [], isLoading, isError, error } = useProtectedFiles();
  const restore = useRestoreFiles();
  const canRestore = useHasRole("admin", "analyst");

  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // Optional cut-off: only use backups taken before this moment (e.g. when
  // an attack started). Empty = newest clean version.
  const [before, setBefore] = useState("");

  const visible = useMemo(
    () => files.filter((f) => f.path.toLowerCase().includes(filter.toLowerCase())),
    [files, filter]
  );
  const missing = files.filter((f) => !f.exists).length;

  const toggle = (path: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  const allVisibleSelected = visible.length > 0 && visible.every((f) => selected.has(f.path));
  const toggleAll = () =>
    setSelected(allVisibleSelected ? new Set() : new Set(visible.map((f) => f.path)));

  const runRestore = () =>
    restore.mutate(
      { paths: [...selected], before: before ? new Date(before).toISOString() : undefined },
      { onSuccess: () => setSelected(new Set()) }
    );

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-6 py-10">
      <div>
        <h2 className="headline text-[2.5rem]"><span className="text-surface-100">Every file,</span>{" "}<span className="bg-gradient-to-r from-electric-500 to-electric-300 bg-clip-text text-transparent">one click from restored</span></h2>
        <p className="mt-1 text-sm text-surface-400">
          Every file EarlyShield holds a verified shadow copy of. Select files to restore them manually; the current
          content is moved to quarantine first, so a restore can always be undone.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 card p-4">
        <div className="min-w-[220px] flex-1">
          <label htmlFor="file-filter" className="mb-1 block text-xs text-surface-400">
            Filter by path
          </label>
          <input
            id="file-filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="e.g. finance or .csv"
            className="w-full rounded-md border border-surface-700 bg-surface-900 px-3 py-2 font-mono text-sm text-surface-100 focus:border-teal-500"
          />
        </div>
        <div>
          <label htmlFor="restore-before" className="mb-1 block text-xs text-surface-400">
            Use backups taken before (optional)
          </label>
          <input
            id="restore-before"
            type="datetime-local"
            value={before}
            onChange={(e) => setBefore(e.target.value)}
            className="rounded-md border border-surface-700 bg-surface-900 px-3 py-2 text-sm text-surface-100 focus:border-teal-500"
          />
        </div>
        <button
          onClick={runRestore}
          disabled={!canRestore || selected.size === 0 || restore.isPending}
          className="rounded-md bg-teal-500 px-4 py-2 text-sm font-medium text-surface-950 transition-colors hover:bg-teal-400 disabled:opacity-50"
        >
          {restore.isPending ? "Restoring…" : `Restore selected (${selected.size})`}
        </button>
      </div>

      {!canRestore && <p className="text-xs text-surface-400">Viewers can browse backups but not restore them.</p>}
      {restore.isSuccess && (
        <p className="rounded-md border border-teal-500/30 bg-teal-500/10 px-4 py-3 text-sm text-teal-300">
          {restore.data.restored} restored · {restore.data.skipped} skipped (already intact or no clean version) ·{" "}
          {restore.data.failed} failed. Details are in the recovery log.
        </p>
      )}
      {restore.isError && (
        <p className="rounded-md border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-400">
          {(restore.error as { message?: string })?.message ?? "Restore failed."}
        </p>
      )}

      <div className="card">
        <div className="flex items-center justify-between border-b border-surface-700 px-4 py-3 text-xs text-surface-400">
          <span>
            {files.length} file(s) protected{missing > 0 && <span className="text-amber-400"> · {missing} missing on disk</span>}
          </span>
          <span>Refreshes every 10 s</span>
        </div>
        {isLoading ? (
          <p className="px-4 py-6 text-sm text-surface-400">Loading…</p>
        ) : isError ? (
          <p className="px-4 py-6 text-sm text-danger-400">{(error as { message?: string })?.message}</p>
        ) : files.length === 0 ? (
          <p className="px-4 py-6 text-sm text-surface-400">
            No shadow copies yet. Start monitoring a folder and a baseline snapshot is taken automatically.
          </p>
        ) : (
          <div className="max-h-[60vh] overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-surface-800 text-xs text-surface-400">
                <tr>
                  <th className="w-10 px-4 py-2">
                    <input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} aria-label="Select all" />
                  </th>
                  <th className="px-2 py-2 font-medium">Path</th>
                  <th className="px-2 py-2 font-medium">Versions</th>
                  <th className="px-2 py-2 font-medium">Latest backup</th>
                  <th className="px-4 py-2 font-medium">On disk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {visible.map((f) => (
                  <tr key={f.path} className={clsx(selected.has(f.path) && "bg-teal-500/5")}>
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selected.has(f.path)}
                        onChange={() => toggle(f.path)}
                        aria-label={`Select ${f.path}`}
                      />
                    </td>
                    <td className="max-w-[420px] truncate px-2 py-2 font-mono text-xs text-surface-100" title={f.path}>
                      {f.path}
                    </td>
                    <td className="px-2 py-2 font-mono text-xs text-surface-200">{f.versions}</td>
                    <td className="px-2 py-2 text-xs text-surface-200">{formatTime(f.latest_captured_at)}</td>
                    <td className={clsx("px-4 py-2 text-xs", f.exists ? "text-teal-400" : "text-amber-400")}>
                      {f.exists ? "present" : "missing"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
