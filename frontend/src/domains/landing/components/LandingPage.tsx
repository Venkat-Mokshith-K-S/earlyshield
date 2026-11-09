import { Link } from "react-router-dom";
import { useHasToken } from "@/domains/auth/hooks/useAuth";
import { BrandMark } from "@/shared/components/BrandMark";
import { FeatureIso, HeroIso } from "@/domains/landing/components/IsoArt";

// Every number on this page comes from the project's own measurements:
// ml/README.md (offline accuracy) and backend/evaluation/README.md (live runs).

function Arrow({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NavBar({ signedIn }: { signedIn: boolean }) {
  return (
    <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between border-b border-white/10 px-6 py-4">
      <Link to="/" aria-label="EarlyShield home">
        <BrandMark tone="light" />
      </Link>
      <nav className="hidden items-center divide-x divide-white/10 border-x border-white/10 md:flex" aria-label="Sections">
        {[
          ["How it works", "#how"],
          ["Results", "#results"],
          ["Recovery", "#recovery"],
        ].map(([label, href]) => (
          <a key={href} href={href} className="px-6 py-1 text-[13px] text-white/60 transition hover:text-white">
            {label}
          </a>
        ))}
      </nav>
      <div className="flex items-center gap-2">
        {signedIn ? (
          <Link to="/dashboard" className="rounded-lg bg-white px-4 py-2 text-[13px] font-medium text-ink transition hover:bg-white/90">
            Open dashboard
          </Link>
        ) : (
          <>
            <Link to="/login" className="rounded-lg bg-white/10 px-4 py-2 text-[13px] font-medium text-white ring-1 ring-white/10 transition hover:bg-white/15">
              Sign in
            </Link>
            <Link to="/register" className="rounded-lg bg-white px-4 py-2 text-[13px] font-medium text-ink transition hover:bg-white/90">
              Get started
            </Link>
          </>
        )}
      </div>
    </header>
  );
}

function Hero({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="bg-hero relative overflow-hidden text-white">
      <div className="grid-lines pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" />
      <NavBar signedIn={signedIn} />

      <div className="relative mx-auto grid max-w-7xl items-center gap-6 px-6 pb-10 pt-14 lg:grid-cols-[1.05fr_1fr] lg:pt-20">
        <div>
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.12em]">
            <span className="rounded border border-white/15 bg-white/5 px-2 py-1 text-white/80">96.79% model accuracy</span>
            <span className="flex items-center gap-1.5 rounded px-2 py-1 text-white/50">
              Status
              <span className="es-pulse h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span className="text-white/80">Monitoring</span>
            </span>
          </div>

          <h1 className="headline mt-6 text-[clamp(2.75rem,6.4vw,5.25rem)]">
            <span className="text-white/55">Caught before</span>
            <br />
            <span className="text-white">it&apos;s encrypted</span>
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-relaxed text-white/65">
            Behavioural machine learning that spots ransomware within seconds, explains every alert, and puts your files
            back on its own.
          </p>

          <div className="mt-8 flex items-center">
            <Link
              to={signedIn ? "/dashboard" : "/register"}
              className="group inline-flex items-center overflow-hidden rounded-lg shadow-glow"
            >
              <span className="bg-gradient-to-b from-electric-400 to-electric-500 px-5 py-3 text-sm font-medium">
                {signedIn ? "Open dashboard" : "Get started"}
              </span>
              <span className="flex h-full items-center bg-electric-600 px-3.5 py-3 transition group-hover:bg-electric-700">
                <Arrow />
              </span>
            </Link>
            <a href="#how" className="ml-5 text-sm text-white/60 transition hover:text-white">
              How it works
            </a>
          </div>
        </div>

        <div className="relative -mr-6 h-[340px] sm:h-[440px] lg:h-[520px]">
          <HeroIso />
        </div>
      </div>

      <div className="relative mx-auto max-w-7xl px-6 pb-12">
        <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-white/40">Built with</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-10 gap-y-3 text-lg font-medium tracking-tight text-white/85">
          <span>FastAPI</span>
          <span>scikit-learn</span>
          <span>SHAP</span>
          <span>React</span>
          <span>PostgreSQL</span>
          <span>Docker</span>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ dark, accent, children }: { dark: string; accent: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-2xl">
      <h2 className="headline text-[clamp(2.25rem,4.6vw,3.5rem)]">
        <span className="text-surface-100">{dark}</span>
        <br />
        <span className="bg-gradient-to-r from-electric-500 to-electric-300 bg-clip-text text-transparent">{accent}</span>
      </h2>
      {children && <p className="mt-4 text-[15px] leading-relaxed text-surface-400">{children}</p>}
    </div>
  );
}

const FEATURES = [
  {
    icon: "layers" as const,
    title: "Every file accounted for",
    body: "A SHA-256 shadow-copy vault keeps clean versions of every watched file, stored outside the watched folder.",
  },
  {
    icon: "cube" as const,
    title: "Behaviour, not signatures",
    body: "Eleven behavioural signals (entropy jumps, renames, write bursts) catch variants no one has seen before.",
  },
  {
    icon: "grid" as const,
    title: "Every alert explained",
    body: "SHAP shows exactly which signals pushed the score up, in a sentence an analyst can act on.",
  },
  {
    icon: "ring" as const,
    title: "Recovery on its own",
    body: "Encrypted copies are quarantined and originals restored automatically, in 1.5 s on average.",
  },
];

function Features() {
  return (
    <section id="how" className="scroll-mt-6 bg-surface-950">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <SectionHeading dark="Built for the alerts" accent="that actually matter">
          EarlyShield watches how files change, not what they are called, so it can act within one observation window.
        </SectionHeading>

        <div className="mt-16 grid border-y border-surface-700 sm:grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-surface-700">
          {FEATURES.map((f, i) => (
            <div key={f.title} className="flex flex-col px-6 py-8">
              <span className="font-mono text-[10.5px] text-surface-500">0{i + 1}</span>
              <div className="my-6 flex justify-center">
                <FeatureIso variant={f.icon} />
              </div>
              <h3 className="text-[15px] font-medium text-surface-100">{f.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-surface-400">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const ATTACK_ROWS = ["Burst", "Throttled", "Slow in-place", "Copy + delete"];

function DetectionGrid() {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-[13px] font-medium text-surface-200">Detection by attack type</p>
        <span className="font-mono text-[10.5px] text-surface-500">36 live trials</span>
      </div>
      <div className="mt-4 flex gap-8">
        <div>
          <p className="text-2xl font-light tracking-tight text-surface-100">36 / 36</p>
          <p className="text-[11px] text-surface-400">attacks detected</p>
        </div>
        <div>
          <p className="text-2xl font-light tracking-tight text-surface-100">0</p>
          <p className="text-[11px] text-surface-400">files lost after recovery</p>
        </div>
      </div>
      <div className="mt-5 space-y-1.5">
        {ATTACK_ROWS.map((row, r) => (
          <div key={row} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-[11px] text-surface-400">{row}</span>
            <div className="flex gap-1">
              {Array.from({ length: 9 }, (_, t) => (
                <span
                  key={t}
                  className="h-4 w-4 rounded-[3px]"
                  style={{ background: `rgba(59,91,253,${0.45 + ((r * 9 + t) % 5) * 0.12})` }}
                  title={`${row}, trial ${t + 1}: detected, 0 files lost`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between text-[10.5px] text-surface-500">
        <span>Windows of 2, 5 and 10 s · 3 trials each</span>
        <span>Incident follow-up run</span>
      </div>
    </div>
  );
}

function TtdChart() {
  // Stylised distribution of time to detection; the marked values are real.
  return (
    <div className="card p-5">
      <p className="text-[13px] font-medium text-surface-200">Time to detection</p>
      <div className="mt-4 flex gap-8">
        <div>
          <p className="text-2xl font-light tracking-tight text-surface-100">5.5 s</p>
          <p className="text-[11px] text-surface-400">median</p>
        </div>
        <div>
          <p className="text-2xl font-light tracking-tight text-surface-100">10.5 s</p>
          <p className="text-[11px] text-surface-400">90th percentile</p>
        </div>
      </div>
      <svg viewBox="0 0 320 110" className="mt-3 w-full" aria-hidden="true">
        <defs>
          <linearGradient id="ttd" x1="0" x2="1">
            <stop offset="0%" stopColor="#8FA2FF" stopOpacity="0.15" />
            <stop offset="35%" stopColor="#3B5BFD" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#8FA2FF" stopOpacity="0.15" />
          </linearGradient>
        </defs>
        <path d="M0 55 C 40 54, 70 30, 115 22 S 190 34, 230 46 S 300 54, 320 55 C 300 56, 270 64, 230 66 S 150 90, 115 88 S 40 56, 0 55 Z" fill="url(#ttd)" />
        <path d="M0 55 C 40 55, 80 40, 115 36 S 200 46, 240 52 S 300 55, 320 55 C 300 55, 260 58, 240 60 S 150 76, 115 74 S 40 55, 0 55 Z" fill="#3B5BFD" opacity="0.55" />
        {[
          [115, "5.5 s"],
          [215, "10.5 s"],
        ].map(([x, label]) => (
          <g key={label as string}>
            <line x1={x as number} y1={8} x2={x as number} y2={102} stroke="#0E1020" strokeOpacity="0.15" />
            <rect x={(x as number) - 22} y={45} width="44" height="20" rx="10" fill="#2C3145" />
            <text x={x as number} y={58.5} textAnchor="middle" fontSize="10" fill="white" fontFamily="IBM Plex Mono, monospace">
              {label}
            </text>
          </g>
        ))}
      </svg>
      <div className="flex justify-between text-[10.5px] text-surface-500">
        <span>Attack starts</span>
        <span>Detected</span>
        <span>Restored</span>
      </div>
    </div>
  );
}

const DIGEST = [
  { title: "Throttled encryption · demo_files", status: "Recovered", tone: "ok", lines: ["100 files restored from the vault", "Ransom note quarantined"] },
  { title: "Copy-then-delete · projects", status: "Recovered", tone: "ok", lines: [".enc copies quarantined", "Originals restored, hashes verified"] },
  { title: "gzip archiving · notes", status: "Review", tone: "warn", lines: ["Flagged at 0.60: archives held in quarantine", "Release them from the Protected files page"] },
];

function IncidentDigest() {
  return (
    <div className="card p-5 lg:absolute lg:-top-24 lg:right-0 lg:w-[340px]">
      <div className="flex items-center justify-between">
        <p className="text-[13px] font-medium text-surface-200">Incident digest</p>
        <span className="rounded-md border border-surface-700 px-2 py-0.5 font-mono text-[10px] text-surface-400">example</span>
      </div>
      <p className="mt-3 text-[11px] text-surface-400">Recent incidents</p>
      <ul className="mt-2 divide-y divide-surface-700">
        {DIGEST.map((d) => (
          <li key={d.title} className="py-3">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-medium text-surface-200">{d.title}</span>
              <span
                className={
                  d.tone === "ok"
                    ? "rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9.5px] font-medium text-emerald-700"
                    : "rounded-full bg-amber-50 px-1.5 py-0.5 text-[9.5px] font-medium text-amber-700"
                }
              >
                ● {d.status}
              </span>
            </div>
            {d.lines.map((l) => (
              <p key={l} className="mt-1 text-[11px] text-surface-400">
                · {l}
              </p>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Results() {
  return (
    <section id="results" className="scroll-mt-6 border-t border-surface-700 bg-surface-950">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <SectionHeading dark="Your files already know" accent="something's wrong">
          Measured on the running system, not just a test set: a separate process attacks a live folder while EarlyShield
          watches. 225 live trials in total.
        </SectionHeading>
        <a href="#recovery" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-surface-100">
          See how recovery works <Arrow />
        </a>

        <div className="relative mt-32 grid gap-5 lg:grid-cols-[1fr_1fr_340px] lg:pr-0">
          <DetectionGrid />
          <TtdChart />
          <div className="relative min-h-[1px]">
            <IncidentDigest />
          </div>
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  ["Snapshot", "Every watched file is copied into a content-addressed vault, and kept current after each quiet window."],
  ["Detect", "Each window's 11 behavioural features go to a Random Forest; SHAP explains the score."],
  ["Respond", "Above the threshold: encrypted copies and ransom notes are quarantined, never deleted."],
  ["Restore", "Originals come back from their newest clean version, each one hash-verified and logged."],
];

function Recovery() {
  return (
    <section id="recovery" className="scroll-mt-6 bg-ink text-white">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <h2 className="headline text-[clamp(2.25rem,4.6vw,3.5rem)]">
          <span className="text-white/55">From alert to restored</span>
          <br />
          <span className="text-white">in one window</span>
        </h2>
        <ol className="mt-14 grid gap-px overflow-hidden rounded-2xl bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="bg-ink p-6">
              <span className="font-mono text-[10.5px] text-electric-300">STEP 0{i + 1}</span>
              <h3 className="mt-3 text-lg font-medium">{title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-white/55">{body}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 max-w-3xl text-[12.5px] leading-relaxed text-white/45">
          Known limits, stated plainly: slow in-place encryption scores right at the decision boundary and can be missed,
          and gzip archiving can trigger a (reversible) response. Details in the evaluation report.
        </p>
      </div>
    </section>
  );
}

function ClosingCta({ signedIn }: { signedIn: boolean }) {
  return (
    <section className="bg-hero relative overflow-hidden text-white">
      <div className="grid-lines pointer-events-none absolute inset-0 opacity-60" />
      <div className="relative mx-auto flex max-w-7xl flex-col items-start gap-8 px-6 py-20 md:flex-row md:items-end md:justify-between">
        <h2 className="headline text-[clamp(2rem,4vw,3rem)]">
          Protect a folder
          <br />
          <span className="text-white/60">in under five minutes</span>
        </h2>
        <div className="flex gap-3">
          <Link to={signedIn ? "/dashboard" : "/register"} className="rounded-lg bg-white px-5 py-3 text-sm font-medium text-ink transition hover:bg-white/90">
            {signedIn ? "Open dashboard" : "Create an account"}
          </Link>
          {!signedIn && (
            <Link to="/login" className="rounded-lg bg-white/10 px-5 py-3 text-sm font-medium ring-1 ring-white/15 transition hover:bg-white/15">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}

export function LandingPage() {
  const signedIn = useHasToken();
  return (
    <div className="min-h-screen bg-surface-950">
      <Hero signedIn={signedIn} />
      <Features />
      <Results />
      <Recovery />
      <ClosingCta signedIn={signedIn} />
      <footer className="bg-ink">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-6 py-8 text-[12px] text-white/40 sm:flex-row sm:items-center sm:justify-between">
          <BrandMark tone="light" className="opacity-70" />
          <span>B.Tech mini project (CSS7102), Presidency University, Bengaluru</span>
        </div>
      </footer>
    </div>
  );
}
