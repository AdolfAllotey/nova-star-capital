// src/ui/MarketRegimeBadge.jsx
import React from "react";

const colorByRegime = (regime) => {
  switch ((regime || "").toLowerCase()) {
    case "bull":
      return "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/30";
    case "bear":
      return "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/30";
    default:
      return "bg-zinc-500/15 text-zinc-300 ring-1 ring-zinc-400/30";
  }
};

export default function MarketRegimeBadge({ regime = "neutral", confidence = 0 }) {
  const pct = Math.round((confidence || 0) * 100);
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm font-medium ${colorByRegime(regime)}`}>
      <span className="inline-block h-2.5 w-2.5 rounded-full bg-current/70" />
      <span className="uppercase tracking-wide">{regime}</span>
      <span className="opacity-70">{pct}%</span>
    </span>
  );
}
