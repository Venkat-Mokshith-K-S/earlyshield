import { useMemo } from "react";

interface ThreatGaugeProps {
  threatScore: number; // 0-100
  prediction: "benign" | "ransomware_like";
}

function scoreToColor(score: number): string {
  if (score < 30) return "#3B5BFD"; // blue — safe
  if (score < 65) return "#F59E0B"; // amber — caution
  return "#EF4444"; // red — threat
}

export function ThreatGauge({ threatScore, prediction }: ThreatGaugeProps) {
  const radius = 88;
  const circumference = 2 * Math.PI * radius;

  const { offset, color } = useMemo(() => {
    const clamped = Math.max(0, Math.min(100, threatScore));
    return {
      offset: circumference - (clamped / 100) * circumference,
      color: scoreToColor(clamped),
    };
  }, [threatScore, circumference]);

  return (
    <div className="relative flex items-center justify-center" style={{ width: 220, height: 220 }}>
      <svg width="220" height="220" viewBox="0 0 220 220" className="-rotate-90">
        <circle cx="110" cy="110" r={radius} fill="none" stroke="#E3E6F2" strokeWidth="14" />
        <circle
          cx="110"
          cy="110"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span
          className="font-mono text-5xl font-semibold tabular-nums"
          style={{ color }}
        >
          {threatScore.toFixed(0)}
        </span>
        <span className="mt-1 font-mono text-xs uppercase tracking-wide text-surface-400">
          threat score
        </span>
        <span
          className="mt-2 rounded-full px-3 py-0.5 text-xs font-medium"
          style={{
            color,
            backgroundColor: `${color}1A`,
          }}
        >
          {prediction === "ransomware_like" ? "Ransomware-like" : "Benign"}
        </span>
      </div>
    </div>
  );
}
