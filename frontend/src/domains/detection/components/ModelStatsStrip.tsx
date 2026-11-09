import type { ModelInfo } from "@/domains/detection/api/detectionApi";

interface ModelStatsStripProps {
  info: ModelInfo | undefined;
}

export function ModelStatsStrip({ info }: ModelStatsStripProps) {
  if (!info) return null;

  const stats = [
    { label: "Accuracy", value: info.training_accuracy },
    { label: "F1 score", value: info.training_f1_score },
    { label: "ROC-AUC", value: info.training_roc_auc },
  ];

  return (
    <div className="flex flex-col gap-3 card px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-xs text-surface-400">{info.model_type}</span>
      <div className="flex gap-6">
        {stats.map((s) => (
          <div key={s.label} className="text-right">
            <div className="font-mono text-sm font-medium text-surface-100">
              {(s.value * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-surface-400">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
