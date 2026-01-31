// src/components/ui/KpiCard.jsx
import React from "react";

export default function KpiCard({ label, value, hint, delta, right }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs text-zinc-400">{label}</div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>

      <div className="mt-1 text-xl font-semibold text-zinc-50">{value}</div>

      {(hint || delta !== undefined) && (
        <div className="mt-2 flex items-center justify-between gap-3">
          {hint ? <div className="text-xs text-zinc-500">{hint}</div> : <div />}
          {delta !== undefined && delta !== null ? (
            <div className="text-xs text-zinc-400">{delta}</div>
          ) : null}
        </div>
      )}
    </div>
  );
}
