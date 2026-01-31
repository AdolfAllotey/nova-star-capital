// src/components/UiKit.jsx
import React from "react";

export function SectionCard({ title, right, children, className = "" }) {
  return (
    <section className={`rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4 ${className}`}>
      {(title || right) && (
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
          <div className="text-xs text-zinc-500">{right}</div>
        </div>
      )}
      {children}
    </section>
  );
}

export function StatusBadge({ status = "COMING" }) {
  const map = {
    ON: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    OFF: "bg-zinc-500/10 text-zinc-300 border-zinc-500/20",
    SIMULATION: "bg-sky-500/10 text-sky-300 border-sky-500/20",
    RISK_OFF: "bg-amber-500/10 text-amber-200 border-amber-500/20",
    PAUSED: "bg-amber-500/10 text-amber-200 border-amber-500/20",
    GEL: "bg-red-500/10 text-red-200 border-red-500/20",
    COMING: "bg-zinc-500/10 text-zinc-300 border-zinc-500/20",
  };
  const cls = map[status] || map.COMING;
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${cls}`}>
      {status}
    </span>
  );
}

export function BrickHeader({ title, subtitle, status = "COMING", right }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-zinc-50">{title}</h1>
          <StatusBadge status={status} />
        </div>
        {subtitle && <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>}
      </div>
      {right && <div className="text-xs text-zinc-500">{right}</div>}
    </div>
  );
}
