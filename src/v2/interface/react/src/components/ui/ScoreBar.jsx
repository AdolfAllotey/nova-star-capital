// src/components/ui/ScoreBar.jsx
import React from "react";

export default function ScoreBar({ label, value, hint }) {
  const v = Number.isFinite(Number(value)) ? Math.max(0, Math.min(100, Number(value))) : null;

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
      <div className="flex items-baseline justify-between">
        <div className="text-sm font-semibold text-zinc-100">{label}</div>
        <div className="text-xs text-zinc-500">{v === null ? "—" : `${v}/100`}</div>
      </div>

      <div className="mt-3 h-2 w-full rounded-full bg-zinc-900/60 border border-zinc-800 overflow-hidden">
        <div
          className="h-full rounded-full bg-emerald-500/40"
          style={{ width: v === null ? "0%" : `${v}%` }}
        />
      </div>

      {hint ? <div className="mt-2 text-xs text-zinc-500">{hint}</div> : null}
    </div>
  );
}
