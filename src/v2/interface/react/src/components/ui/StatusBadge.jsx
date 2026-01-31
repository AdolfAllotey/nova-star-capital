// src/components/ui/StatusBadge.jsx
import React from "react";

const styles = {
  ON: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  OFF: "border-zinc-700 bg-zinc-900/40 text-zinc-300",
  PAUSED: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  SIMULATION: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  RISK_OFF: "border-orange-500/30 bg-orange-500/10 text-orange-200",
  GEL: "border-red-500/30 bg-red-500/10 text-red-200",
  COMING: "border-amber-500/30 bg-amber-500/10 text-amber-200",
};

export default function StatusBadge({ status = "OFF", className = "" }) {
  const key = String(status || "OFF").toUpperCase();
  const cls = styles[key] || styles.OFF;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${cls} ${className}`}
    >
      {key}
    </span>
  );
}
