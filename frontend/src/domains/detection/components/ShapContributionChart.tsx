import type { FeatureContribution } from "@/domains/detection/api/detectionApi";

const FEATURE_LABELS: Record<string, string> = {
  file_modification_rate: "File modification rate",
  file_rename_rate: "File rename rate",
  file_deletion_rate: "File deletion rate",
  entropy_mean: "Content entropy",
  entropy_delta: "Entropy shift vs. baseline",
  extension_change_ratio: "Extension-change ratio",
  unique_dirs_touched: "Directories touched",
  avg_size_change_ratio: "File size change ratio",
  process_cpu_percent: "Process CPU usage",
  io_write_rate_mb_s: "Disk write throughput",
  read_write_ratio: "Read/write ratio",
};

interface ShapContributionChartProps {
  contributions: FeatureContribution[];
}

export function ShapContributionChart({ contributions }: ShapContributionChartProps) {
  const maxAbs = Math.max(...contributions.map((c) => Math.abs(c.shap_value)), 0.01);

  return (
    <div className="space-y-4 sm:space-y-3">
      {contributions.map((c) => {
        const widthPct = (Math.abs(c.shap_value) / maxAbs) * 100;
        const isRisk = c.direction === "increases_risk";
        return (
          <div key={c.feature} className="flex flex-col gap-1 sm:grid sm:grid-cols-[1fr_2fr_56px] sm:items-center sm:gap-3">
            <span className="text-sm text-surface-200 sm:text-right">
              {FEATURE_LABELS[c.feature] ?? c.feature}
            </span>
            <div className="flex items-center gap-3 sm:contents">
              <div className="relative h-6 flex-1">
                <div className="absolute left-1/2 top-0 h-full w-px bg-surface-700" />
                <div
                  className="absolute top-0 h-full rounded"
                  style={{
                    width: `${widthPct / 2}%`,
                    left: isRisk ? "50%" : `${50 - widthPct / 2}%`,
                    backgroundColor: isRisk ? "#EF4444" : "#3B5BFD",
                    opacity: 0.85,
                  }}
                />
              </div>
              <span className="font-mono text-xs tabular-nums text-surface-400">
                {c.shap_value > 0 ? "+" : ""}
                {c.shap_value.toFixed(3)}
              </span>
            </div>
          </div>
        );
      })}
      <div className="flex justify-between pt-1 text-xs text-surface-400 sm:grid sm:grid-cols-[1fr_2fr_56px] sm:gap-3">
        <span className="sm:hidden" />
        <div className="flex w-full justify-between sm:col-start-2">
          <span>← decreases risk</span>
          <span>increases risk →</span>
        </div>
      </div>
    </div>
  );
}
