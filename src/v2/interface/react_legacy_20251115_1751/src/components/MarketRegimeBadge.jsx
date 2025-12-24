import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

export default function MarketRegimeBadge() {
  const { data, error } = usePolling(`${BASE_URL}/api/market/regime`, 20000);

  const regime = data?.regime || "—";
  const score = typeof data?.score === "number" ? data.score : null;
  const date  = data?.date || "—";

  const color =
    regime.toLowerCase() === "bull" ? "bg-emerald-500/15 text-emerald-400 border-emerald-700/30" :
    regime.toLowerCase() === "bear" ? "bg-rose-500/15 text-rose-400 border-rose-700/30" :
    "bg-slate-500/15 text-slate-300 border-slate-700/30";

  return (
    <div className={`inline-flex items-center gap-3 rounded-xl border px-3 py-2 ${color}`}>
      <span className="text-sm font-semibold">Regime: {regime}</span>
      <span className="text-xs opacity-80">score: {score ?? "—"}</span>
      <span className="text-xs opacity-60">date: {date}</span>
      {error && <span className="text-xs text-rose-400"> (err)</span>}
    </div>
  );
}
