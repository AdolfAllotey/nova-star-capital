import React from "react";

function normalizeRegime(regime) {
  return String(regime || "unknown").toLowerCase();
}

function getTone(regime) {
  const r = normalizeRegime(regime);

  if (r.includes("risk_on") || r.includes("bull")) {
    return {
      ring: "border-emerald-500/20",
      bg: "bg-emerald-500/8",
      glow: "from-emerald-500/18 via-emerald-400/8 to-transparent",
      dot: "bg-emerald-400",
      text: "text-emerald-300",
      sub: "Risk appetite active",
    };
  }

  if (r.includes("risk_off") || r.includes("bear")) {
    return {
      ring: "border-red-500/20",
      bg: "bg-red-500/8",
      glow: "from-red-500/18 via-red-400/8 to-transparent",
      dot: "bg-red-400",
      text: "text-red-300",
      sub: "Capital protection mode",
    };
  }

  return {
    ring: "border-amber-500/20",
    bg: "bg-amber-500/8",
    glow: "from-amber-500/18 via-amber-400/8 to-transparent",
    dot: "bg-amber-300",
    text: "text-amber-300",
    sub: "Balanced / caution regime",
  };
}

function fmtConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "n/a";
  return `${(value * 100).toFixed(0)}%`;
}

export default function MarketStateCapsule({
  regime = "unknown",
  confidence = null,
  governance = "unknown",
  lastRefresh = "—",
}) {
  const tone = getTone(regime);

  return (
    <div
      className={[
        "relative overflow-hidden rounded-[28px] border px-8 py-6",
        "bg-zinc-950/65 backdrop-blur-sm",
        tone.ring,
        tone.bg,
      ].join(" ")}
    >
      <div
        className={[
          "pointer-events-none absolute top-[-30%] right-[-10%] w-[500px] h-[500px] rounded-full blur-2xl opacity-15 bg-gradient-to-r",
          tone.glow,
          "nsc-glow-curve",
        ].join(" ")}
      />

      <div className="relative flex flex-col items-center justify-center text-center gap-5 min-h-[300px] min-h-[300px]">
        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className={["h-2.5 w-2.5 rounded-full shadow-sm", tone.dot].join(" ")} />
          <span className="text-[10px] uppercase tracking-[0.22em] text-zinc-500">
            Market State
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <div className={["text-4xl font-semibold tracking-[-0.03em] leading-none", tone.text].join(" ")}>
            {String(regime || "UNKNOWN").replaceAll("_", " ").toUpperCase()}
          </div>

          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-300">
            Governance {String(governance || "UNKNOWN").toUpperCase()}
          </span>
        </div>

        <div className="text-sm text-zinc-500 text-center max-w-md">
          {tone.sub}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <div className="rounded-full border border-white/10 bg-black/15 px-4 py-3">
            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Confidence
            </div>
            <div className="mt-1 text-sm font-medium text-zinc-100 text-center">
              {fmtConfidence(confidence)}
            </div>
          </div>

          <div className="rounded-full border border-white/10 bg-black/15 px-4 py-3 min-w-[220px]">
            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Last Refresh
            </div>
            <div className="mt-1 text-sm font-medium text-zinc-200 text-center truncate tabular-nums">
              {lastRefresh || "—"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
