export function humanizeLabel(value = "") {
  if (value === null || value === undefined) return "Unknown"

  return String(value)
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function formatRegime(value = "") {
  const normalized = String(value || "").toLowerCase()

  const mapping = {
    risk_on: "Risk-On",
    risk_off: "Risk-Off",
    neutral: "Neutral",
    neutral_defensive: "Neutral Defensive",
    stabilization_active: "Stabilization Active",
    systemic_hedge_active: "Systemic Hedge Active",
    shadow_mode: "Shadow Mode",
    patrimonial: "Patrimonial",
  }

  return mapping[normalized] || humanizeLabel(value)
}

export function formatMode(value = "") {
  const normalized = String(value || "").toLowerCase()

  const mapping = {
    simulated_only: "PREPROD LOCK",
    simulated_execution: "PAPER EXECUTION",
    simulated: "SIMULATED",
    shadow: "SHADOW MODE",
    shadow_mode: "SHADOW MODE",
    patrimonial: "LONG TERM",
    live: "LIVE EXECUTION",
  }

  return mapping[normalized] || humanizeLabel(value)
}

export function formatStatus(value = "") {
  const normalized = String(value || "").toLowerCase()

  const mapping = {
    ok: "OK",
    healthy: "HEALTHY",
    watch: "WATCH",
    caution: "CAUTION",
    warning: "WARNING",
    critical: "CRITICAL",
    active: "ACTIVE",
    inactive: "INACTIVE",
    off: "OFF",
    on: "ON",
  }

  return mapping[normalized] || humanizeLabel(value)
}

export function formatPolicy(value = "") {
  const normalized = String(value || "").toLowerCase()

  const mapping = {
    simulated_only: "PREPROD LOCK",
    simulated_execution: "PAPER EXECUTION",
    live: "LIVE EXECUTION",
    blocked: "BLOCKED",
    exit_only: "EXIT ONLY",
    reduce_only: "REDUCE ONLY",
  }

  return mapping[normalized] || humanizeLabel(value)
}
