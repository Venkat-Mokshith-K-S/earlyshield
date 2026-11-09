import { useState } from "react";
import { useMonitorStatus, useMonitorEvents } from "@/domains/monitoring/hooks/useMonitoring";
import { useModelInfo } from "@/domains/detection/hooks/useDetection";
import { MonitorControlPanel } from "@/domains/monitoring/components/MonitorControlPanel";
import { EventTimeline } from "@/domains/monitoring/components/EventTimeline";
import { DetectionDetailPanel } from "@/domains/detection/components/DetectionDetailPanel";
import { SimulatePanel } from "@/domains/detection/components/SimulatePanel";
import { ModelStatsStrip } from "@/domains/detection/components/ModelStatsStrip";
import type { SimulationScenario } from "@/domains/detection/api/detectionApi";
import { RecoveryPanel } from "@/domains/recovery/components/RecoveryPanel";
import { RecoveryActionLog } from "@/domains/recovery/components/RecoveryActionLog";
import { useRecoveryActions, useRecoveryStatus } from "@/domains/recovery/hooks/useRecovery";

export function Dashboard() {
  const { data: status } = useMonitorStatus();
  const { data: events = [] } = useMonitorEvents(status?.is_running ?? false);
  const { data: modelInfo } = useModelInfo();
  const { data: recoveryStatus } = useRecoveryStatus();
  const { data: recoveryActions = [] } = useRecoveryActions();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [simulationResult, setSimulationResult] = useState<SimulationScenario | null>(null);

  // A fresh live event takes priority as "what's showing" over a stale
  // simulation result; a manual simulation is shown until the next real
  // event arrives.
  const selectedEvent = events[selectedIndex];
  const showingSimulation = !selectedEvent && simulationResult;

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <h2 className="headline text-[clamp(2rem,4vw,3rem)]">
            <span className="text-surface-100">Live protection</span>
            <br />
            <span className="bg-gradient-to-r from-electric-500 to-electric-300 bg-clip-text text-transparent">
              for the files that matter
            </span>
          </h2>
          <span className="flex items-center gap-2 rounded-full border border-surface-700 bg-surface-800 px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.1em] text-surface-400">
            <span className={status?.is_running ? "es-pulse h-1.5 w-1.5 rounded-full bg-emerald-500" : "h-1.5 w-1.5 rounded-full bg-surface-500"} />
            {status?.is_running ? "Monitoring" : "Monitor idle"}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
          <div className="space-y-6">
            {selectedEvent?.recovery_incident_id && (
              <div className="rounded-2xl border border-danger-500/30 bg-danger-500/5 px-4 py-3 text-sm text-danger-600">
                Automated response triggered for this window. Affected files were quarantined and restored from
                shadow copies. See the recovery log below.
              </div>
            )}
            {selectedEvent ? (
              <DetectionDetailPanel
                result={selectedEvent.result}
                timestamp={selectedEvent.timestamp}
                attributedProcess={selectedEvent.attributed_process}
              />
            ) : showingSimulation ? (
              <DetectionDetailPanel result={simulationResult.result} />
            ) : (
              <DetectionDetailPanel emptyState />
            )}

            <div className="card p-5">
              <h2 className="mb-4 text-sm font-medium text-surface-100">Detection timeline</h2>
              <EventTimeline events={events} selectedIndex={selectedIndex} onSelect={setSelectedIndex} />
            </div>

            <div className="card p-5">
              <h2 className="mb-3 text-sm font-medium text-surface-100">Recovery log</h2>
              <RecoveryActionLog actions={recoveryActions} />
            </div>

            <ModelStatsStrip info={modelInfo} />
          </div>

          <div className="space-y-6">
            <MonitorControlPanel status={status} />
            <RecoveryPanel status={recoveryStatus} monitorRunning={status?.is_running ?? false} />
            <SimulatePanel onResult={setSimulationResult} />
          </div>
        </div>
      </main>
  );
}
