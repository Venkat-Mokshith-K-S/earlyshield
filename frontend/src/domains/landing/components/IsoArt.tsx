/**
 * Isometric line art for the landing page, drawn in plain SVG (no image
 * assets). Iso edges run at ±30°, so a plate centred on (cx, cy) with
 * half-width w has half-height w * tan(30°) ≈ w * 0.577.
 */

const ISO = 0.577;

function plate(cx: number, cy: number, w: number) {
  const h = w * ISO;
  return `${cx},${cy - h} ${cx + w},${cy} ${cx},${cy + h} ${cx - w},${cy}`;
}

function sides(cx: number, cy: number, w: number, depth: number) {
  const h = w * ISO;
  return {
    left: `${cx - w},${cy} ${cx},${cy + h} ${cx},${cy + h + depth} ${cx - w},${cy + depth}`,
    right: `${cx},${cy + h} ${cx + w},${cy} ${cx + w},${cy + depth} ${cx},${cy + h + depth}`,
  };
}

/** A label lying flat along an iso edge. */
function EdgeLabel({ x, y, angle, children }: { x: number; y: number; angle: number; children: string }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${angle}) skewX(${angle > 0 ? -30 : 30})`}>
      <rect x={-4} y={-11} width={children.length * 6.6 + 8} height={16} rx={2} fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.35)" strokeWidth="0.75" />
      <text x={0} y={0} fontSize="9" letterSpacing="1.4" fill="rgba(255,255,255,0.85)" fontFamily="IBM Plex Mono, monospace">
        {children}
      </text>
    </g>
  );
}

export function HeroIso() {
  const cx = 330;
  const cy = 300;
  const slab = sides(cx, cy, 175, 34);

  return (
    <svg viewBox="0 0 660 560" className="h-full w-full" role="img" aria-label="Isometric diagram of the EarlyShield pipeline">
      <defs>
        <linearGradient id="es-top" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7E93FF" />
          <stop offset="55%" stopColor="#3B5BFD" />
          <stop offset="100%" stopColor="#2236F0" />
        </linearGradient>
        <linearGradient id="es-left" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2A3FE0" />
          <stop offset="100%" stopColor="#141C8A" />
        </linearGradient>
        <linearGradient id="es-right" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3550F5" />
          <stop offset="100%" stopColor="#1B27A8" />
        </linearGradient>
        <radialGradient id="es-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6B83FF" stopOpacity="0.75" />
          <stop offset="100%" stopColor="#3B5BFD" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* ground grid */}
      <polygon points={plate(cx, cy + 40, 300)} fill="none" stroke="rgba(255,255,255,0.14)" strokeDasharray="3 5" />
      <polygon points={plate(cx, cy + 40, 235)} fill="none" stroke="rgba(255,255,255,0.10)" />
      <line x1={cx - 300} y1={cy + 40} x2={cx + 300} y2={cy + 40} stroke="rgba(255,255,255,0.06)" />

      <ellipse cx={cx} cy={cy + 20} rx="250" ry="120" fill="url(#es-glow)" />

      {/* the solid slab: the detector */}
      <polygon points={slab.left} fill="url(#es-left)" />
      <polygon points={slab.right} fill="url(#es-right)" />
      <polygon points={plate(cx, cy, 175)} fill="url(#es-top)" />
      <polygon points={plate(cx, cy, 175)} fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth="1" />
      <polygon points={plate(cx, cy, 120)} fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="0.8" />
      {[-1, 1].map((s) => (
        <circle key={s} cx={cx + s * 175} cy={cy} r="2.5" fill="#fff" />
      ))}
      <circle cx={cx} cy={cy + 101} r="2.5" fill="#fff" />

      {/* floating wireframe: the explanation layer */}
      <g className="es-float">
        <polygon points={plate(cx + 40, cy - 165, 150)} fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.75)" strokeWidth="1" />
        <path
          d={`M ${cx - 60} ${cy - 160} q 30 -40 60 -10 t 60 -20 t 50 10`}
          fill="none"
          stroke="rgba(255,255,255,0.55)"
          strokeWidth="1"
        />
        {[0, 1, 2, 3].map((i) => (
          <line
            key={i}
            x1={cx + 40 + (i - 1.5) * 34}
            y1={cy - 165 - 86 + Math.abs(i - 1.5) * 19.6}
            x2={cx + 40 + (i - 1.5) * 34}
            y2={cy - 95}
            stroke="rgba(255,255,255,0.08)"
          />
        ))}
        <EdgeLabel x={cx - 2} y={cy - 238} angle={30}>
          SHAP EXPLAINER
        </EdgeLabel>
      </g>

      {/* vertical guide lines from slab corners */}
      {[-175, 175].map((dx) => (
        <line key={dx} x1={cx + dx} y1={cy} x2={cx + dx} y2={cy - 140} stroke="rgba(255,255,255,0.15)" strokeDasharray="2 4" />
      ))}

      <EdgeLabel x={cx - 150} y={cy + 30} angle={30}>
        ENTROPY Δ
      </EdgeLabel>
      <EdgeLabel x={cx + 70} y={cy + 75} angle={-30}>
        SHADOW VAULT
      </EdgeLabel>
      <EdgeLabel x={cx + 205} y={cy - 70} angle={30}>
        TTD 5.5 s
      </EdgeLabel>
      <EdgeLabel x={cx - 255} y={cy + 135} angle={-30}>
        0 FILES LOST
      </EdgeLabel>
    </svg>
  );
}

/** Small line icons for the feature row: four ways of stacking a plate. */
export function FeatureIso({ variant }: { variant: "layers" | "cube" | "grid" | "ring" }) {
  const stroke = "#3B5BFD";
  const cx = 80;
  return (
    <svg viewBox="0 0 160 130" className="h-28 w-36" aria-hidden="true">
      {variant === "layers" &&
        [0, 1, 2, 3].map((i) => (
          <polygon
            key={i}
            points={plate(cx, 88 - i * 14, 52)}
            fill={i === 3 ? "rgba(59,91,253,0.12)" : "white"}
            stroke={stroke}
            strokeOpacity={0.35 + i * 0.2}
          />
        ))}
      {variant === "cube" && (
        <g>
          <polygon points={plate(cx, 96, 52)} fill="white" stroke={stroke} strokeOpacity="0.45" />
          <polygon points={sides(cx - 14, 56, 22, 34).left} fill="white" stroke={stroke} />
          <polygon points={sides(cx - 14, 56, 22, 34).right} fill="rgba(59,91,253,0.1)" stroke={stroke} />
          <polygon points={plate(cx - 14, 56, 22)} fill="rgba(59,91,253,0.18)" stroke={stroke} />
          <polygon points={plate(cx + 22, 30, 16)} fill="white" stroke={stroke} strokeDasharray="2 3" />
        </g>
      )}
      {variant === "grid" && (
        <g>
          <polygon points={plate(cx, 92, 56)} fill="white" stroke={stroke} strokeOpacity="0.5" />
          {[-2, -1, 0, 1, 2].flatMap((r) =>
            [-2, -1, 0, 1, 2].map((c) => (
              <circle
                key={`${r}${c}`}
                cx={cx + (c - r) * 10}
                cy={92 + (c + r) * 5.8}
                r={r === 0 && c === 0 ? 4.5 : 2.6}
                fill={r === 0 && c === 0 ? stroke : "white"}
                stroke={stroke}
                strokeOpacity={0.7}
              />
            ))
          )}
          <line x1={cx} y1={92} x2={cx} y2={34} stroke={stroke} strokeDasharray="2 3" />
          <polygon points={plate(cx, 34, 16)} fill="rgba(59,91,253,0.15)" stroke={stroke} />
        </g>
      )}
      {variant === "ring" && (
        <g>
          <ellipse cx={cx} cy={80} rx={60} ry={34} fill="none" stroke={stroke} strokeOpacity="0.35" strokeDasharray="3 4" />
          <polygon points={plate(cx, 80, 34)} fill="white" stroke={stroke} />
          <polygon points={plate(cx, 70, 20)} fill="rgba(59,91,253,0.15)" stroke={stroke} />
          {[0, 90, 180, 270].map((a) => (
            <circle key={a} cx={cx + 60 * Math.cos((a * Math.PI) / 180)} cy={80 + 34 * Math.sin((a * Math.PI) / 180)} r="3" fill={stroke} />
          ))}
        </g>
      )}
    </svg>
  );
}
