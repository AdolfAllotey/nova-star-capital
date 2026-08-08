import React from "react";

const STATUS_STYLES = {
  ACTIVE: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  RUNNING: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  OK: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  LIVE: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  HEALTHY: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  EXECUTED_ENTRY: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  ENTRY_EXECUTED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  EXECUTED_EXIT: "bg-teal-500/10 text-teal-300 border-teal-500/30",
  EXIT_EXECUTED: "bg-teal-500/10 text-teal-300 border-teal-500/30",

  PREPROD: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  CAUTION: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  PENDING: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  QUEUED: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  ENTRY_NOT_EXECUTED: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  NOT_SELECTED_BY_PLAN: "bg-amber-500/10 text-amber-300 border-amber-500/30",

  SIMULATED_ONLY: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  SIGNAL_ONLY: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  WARNING: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  EXIT_PRIORITIZED: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  BLOCKED_BY_CAPS: "bg-orange-500/10 text-orange-300 border-orange-500/30",

  NOT_DEPLOYED: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  DISABLED: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  IDLE: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  UNKNOWN: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  N_A: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  EXIT_NOT_EXECUTED: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
  UNKNOWN_CLASS: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",

  BREACH: "bg-red-500/10 text-red-300 border-red-500/30",
  ANOMALY: "bg-red-500/10 text-red-300 border-red-500/30",
  ERROR: "bg-red-500/10 text-red-300 border-red-500/30",
  OFF: "bg-red-500/10 text-red-300 border-red-500/30",
  BLOCKED: "bg-red-500/10 text-red-300 border-red-500/30",
  HARD_BLOCK: "bg-red-500/10 text-red-300 border-red-500/30",
  BLOCKED_BY_GOVERNANCE: "bg-red-500/10 text-red-300 border-red-500/30",
  VETO_PRESENT: "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/30",

  BOOTSTRAP: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  REBALANCE: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  MONITORING: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  ACTIVE_MODE: "bg-sky-500/10 text-sky-300 border-sky-500/30",
};

const PRETTY_LABELS = {
  ENTRY_EXECUTED: "Entry Executed",
  EXIT_EXECUTED: "Exit Executed",
  ENTRY_NOT_EXECUTED: "Entry Not Executed",
  EXIT_NOT_EXECUTED: "Exit Not Executed",
  EXECUTED_ENTRY: "Executed Entry",
  EXECUTED_EXIT: "Executed Exit",
  NOT_SELECTED_BY_PLAN: "Not Selected by Plan",
  BLOCKED_BY_GOVERNANCE: "Blocked by Governance",
  BLOCKED_BY_CAPS: "Blocked by Caps",
  EXIT_PRIORITIZED: "Exit Prioritized",
  VETO_PRESENT: "Veto Present",
  UNKNOWN_CLASS: "Unknown Class",
  N_A: "N/A",
};

function normalizeStatus(value) {
  if (value === null || value === undefined || value === "") return "UNKNOWN";
  return String(value).trim().replace(/\s+/g, "_").toUpperCase();
}

function prettyLabel(raw, normalized) {
  if (raw !== null && raw !== undefined && raw !== "") return String(raw);
  return PRETTY_LABELS[normalized] || normalized.replace(/_/g, " ");
}

export default function StatusBadge({ status, label }) {
  const normalized = normalizeStatus(status ?? label);
  const style =
    STATUS_STYLES[normalized] ||
    "bg-zinc-500/10 text-zinc-300 border-zinc-500/30";
  const display = prettyLabel(label ?? status, normalized);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap ${style}`}
      title={String(display)}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {display}
    </span>
  );
}
