import React from "react";

const colorByRegime = (regime) => {
  if (!regime) return "from-zinc-800 to-zinc-700";
  switch (regime.toLowerCase()) {
    case "bull":  return "from-emerald-600 to-emerald-500";
    case "bear":  return "from-rose-600 to-rose-500";
    case "range": return "from-amber-600 to-amber-500";
    default:      return "from-zinc-700 to-zinc-600";
  }
};

export default function RegimeCard({ data, loading, error }) {
  if (loading) {
    return (
      <div className="p-6 rounded-2xl bg-zinc-900/60 ring-1 ring-white/10 animate-pulse">
        <div className="h-5 w-36 bg-zinc-700/60 rounded mb-4"></div>
        <div className="h-8 w-64 bg-zinc-700/60 rounded"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-rose-950/50 ring-1 ring-rose-800 text-rose-200">
        {error}
      </div>
    );
  }

  const regime = data?.regime ?? "N/A";
  const score  = data?.score?.toFixed?.(4);
  const date   = data?.date ?? "—";
  const bg     = colorByRegime(regime);

  return (
    <div className={`p-6 rounded-2xl bg-gradient-to-br ${bg} text-white shadow-xl`}>
      <div className="text-sm opacity-90">Régime du marché</div>
      <div className="text-3xl font-semibold mt-1 uppercase tracking-wide">{regime}</div>
      <div className="mt-3 text-sm opacity-90">Score: <span className="font-mono">{score ?? "—"}</span></div>
      <div className="mt-1 text-xs opacity-80">Mise à jour: {date}</div>
    </div>
  );
}
