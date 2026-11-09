import { motion, AnimatePresence } from "framer-motion";
import { ThreatGauge } from "@/domains/detection/components/ThreatGauge";
import { ShapContributionChart } from "@/domains/detection/components/ShapContributionChart";
import type { DetectionResult } from "@/domains/detection/api/detectionApi";

interface DetectionDetailPanelProps {
  result: DetectionResult;
  timestamp?: string;
  attributedProcess?: string | null;
  emptyState?: false;
}

interface EmptyPanelProps {
  emptyState: true;
}

export function DetectionDetailPanel(props: DetectionDetailPanelProps | EmptyPanelProps) {
  if (props.emptyState) {
    return (
      <div className="flex min-h-[280px] flex-col items-center justify-center card p-8 text-center">
        <div className="mb-3 h-16 w-16 rounded-full border-2 border-dashed border-surface-700" />
        <p className="text-sm text-surface-400">
          Start monitoring a directory, or try a scenario, to see a live detection reading here.
        </p>
      </div>
    );
  }

  const { result, timestamp, attributedProcess } = props;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={timestamp ?? result.explanation_summary}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.25 }}
        className="card p-6"
      >
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
          <ThreatGauge threatScore={result.threat_score} prediction={result.prediction} />
          <div className="flex-1">
            <p className="text-base leading-relaxed text-surface-100">{result.explanation_summary}</p>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-surface-400">
              {timestamp && <span>{new Date(timestamp).toLocaleString()}</span>}
              {attributedProcess && <span>process: {attributedProcess}</span>}
              <span>confidence: {(result.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <div className="mt-6 border-t border-surface-700 pt-5">
          <h3 className="mb-4 text-sm font-medium text-surface-100">Feature contributions</h3>
          <ShapContributionChart contributions={result.top_contributing_features} />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
