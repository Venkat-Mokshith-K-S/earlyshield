import { useSimulateScenario } from "@/domains/detection/hooks/useDetection";
import type { SimulationScenario } from "@/domains/detection/api/detectionApi";

interface SimulatePanelProps {
  onResult: (result: SimulationScenario) => void;
}

const SCENARIOS: { key: SimulationScenario["scenario"]; label: string }[] = [
  { key: "benign", label: "Normal activity" },
  { key: "ransomware_typical", label: "Ransomware (typical)" },
  { key: "ransomware_stealthy", label: "Ransomware (stealthy)" },
];

export function SimulatePanel({ onResult }: SimulatePanelProps) {
  const simulate = useSimulateScenario();

  return (
    <div className="card p-5">
      <h2 className="mb-1 text-sm font-medium text-surface-100">Try a scenario</h2>
      <p className="mb-4 text-xs text-surface-400">
        Generates a synthetic sample and runs it through the live model — useful when no directory is
        being watched yet.
      </p>
      <div className="flex flex-col gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            onClick={() => simulate.mutate(s.key, { onSuccess: onResult })}
            disabled={simulate.isPending}
            className="rounded-md border border-surface-700 bg-surface-900 px-3 py-2 text-left text-sm text-surface-200 transition-colors hover:border-teal-500/50 hover:text-surface-100 disabled:opacity-50"
          >
            {simulate.isPending && simulate.variables === s.key ? "Running…" : s.label}
          </button>
        ))}
      </div>
      {simulate.isError && (
        <p className="mt-3 text-xs text-danger-400">
          {(simulate.error as { message?: string; errorCode?: string })?.message ??
            "Something went wrong running that scenario."}
        </p>
      )}
    </div>
  );
}