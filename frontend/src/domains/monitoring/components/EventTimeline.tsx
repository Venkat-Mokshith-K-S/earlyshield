import clsx from "clsx";
import type { DetectionEvent } from "@/domains/monitoring/api/monitoringApi";

function scoreToColor(score: number): string {
  if (score < 30) return "#3B5BFD";
  if (score < 65) return "#F59E0B";
  return "#EF4444";
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

interface EventTimelineProps {
  events: DetectionEvent[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export function EventTimeline({ events, selectedIndex, onSelect }: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-surface-700 text-sm text-surface-400">
        No windows analyzed yet — activity in the watched directory will appear here.
      </div>
    );
  }

  const maxScore = 100;
  // Events arrive newest-first from the API; display oldest-to-newest
  // (left-to-right reads naturally as a timeline) while keeping each
  // item's ORIGINAL index so selection stays consistent with the parent,
  // which tracks "selected" by index into the original newest-first array.
  const displayOrder = events.map((event, originalIndex) => ({ event, originalIndex })).reverse();

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-end gap-1" style={{ minWidth: events.length * 14 }}>
        {displayOrder.map(({ event, originalIndex }) => {
          const heightPct = Math.max(6, (event.result.threat_score / maxScore) * 100);
          const isSelected = originalIndex === selectedIndex;
          return (
            <button
              key={event.timestamp + originalIndex}
              onClick={() => onSelect(originalIndex)}
              title={`${formatTime(event.timestamp)} — ${event.result.prediction} (${event.result.threat_score.toFixed(0)})`}
              className={clsx(
                "group relative flex h-16 w-3 flex-shrink-0 items-end rounded-sm transition-opacity",
                isSelected ? "opacity-100" : "opacity-60 hover:opacity-90"
              )}
            >
              <span
                className="w-full rounded-sm"
                style={{
                  height: `${heightPct}%`,
                  backgroundColor: scoreToColor(event.result.threat_score),
                  boxShadow: isSelected ? `0 0 0 2px #0E1020` : "none",
                }}
              />
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between font-mono text-xs text-surface-400">
        <span>{formatTime(events[events.length - 1].timestamp)}</span>
        <span>{events.length} windows</span>
        <span>{formatTime(events[0].timestamp)}</span>
      </div>
    </div>
  );
}
