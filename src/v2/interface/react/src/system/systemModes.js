export const SYSTEM_MODES = {
  simulated_only: {
    label: "PREPROD LOCK",
    shortLabel: "LOCK",
    tone: "amber",
    description: "Preproduction governance prevents real execution.",
  },
  simulated_execution: {
    label: "PAPER EXECUTION",
    shortLabel: "PAPER",
    tone: "cyan",
    description: "Execution is simulated and monitored.",
  },
  shadow: {
    label: "SHADOW MODE",
    shortLabel: "SHADOW",
    tone: "purple",
    description: "Observed but isolated from live execution.",
  },
  patrimonial: {
    label: "LONG TERM",
    shortLabel: "LT",
    tone: "emerald",
    description: "Long-term patrimonial allocation.",
  },
  live: {
    label: "LIVE EXECUTION",
    shortLabel: "LIVE",
    tone: "green",
    description: "Real execution enabled.",
  },
}

export function getSystemMode(value = "") {
  const normalized = String(value || "").toLowerCase()
  return SYSTEM_MODES[normalized] || {
    label: String(value || "UNKNOWN").toUpperCase(),
    shortLabel: "UNK",
    tone: "slate",
    description: "Unknown mode.",
  }
}
