import React from "react";

function tone(strategy) {
  const status = String(strategy?.status || "").toUpperCase();
  const mode = String(strategy?.mode || "").toUpperCase();

  if (status === "NOT_DEPLOYED") {
    return "bg-zinc-900 text-zinc-400 border-zinc-800";
  }
  if (mode === "SHADOW") {
    return "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/20";
  }
  if (status === "PREPROD") {
    return "bg-amber-500/10 text-amber-300 border-amber-500/20";
  }
  return "bg-sky-500/10 text-sky-300 border-sky-500/20";
}

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "n/a";
  return `${(Number(v) * 100).toFixed(0)}%`;
}

export default function SignalHeatmap({ strategies = [] }) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {(Array.isArray(strategies) ? strategies : []).map((s) => (
        <div
          key={s.key}
          className={`rounded-2xl border p-4 transition-all duration-200 hover:scale-[1.01] ${tone(s)}`}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold">{s.name}</div>
            <div className="text-[10px] uppercase tracking-wide opacity-80">{s.mode || s.status || "n/a"}</div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <div className="opacity-70">Signals</div>
              <div className="mt-1 text-sm font-semibold">{Number(s.candidates || 0)}</div>
            </div>
            <div>
              <div className="opacity-70">Orders</div>
              <div className="mt-1 text-sm font-semibold">{Number(s.orders || 0)}</div>
            </div>
            <div>
              <div className="opacity-70">Open</div>
              <div className="mt-1 text-sm font-semibold">{Number(s.openPositions || 0)}</div>
            </div>
            <div>
              <div className="opacity-70">Confidence</div>
              <div className="mt-1 text-sm font-semibold">{fmtPct(s.confidence)}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
