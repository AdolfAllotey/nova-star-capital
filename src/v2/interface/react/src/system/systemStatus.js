export const SYSTEM_STATUS = {
  ok: { label: "OK", tone: "emerald" },
  healthy: { label: "HEALTHY", tone: "emerald" },
  watch: { label: "WATCH", tone: "cyan" },
  caution: { label: "CAUTION", tone: "amber" },
  warning: { label: "WARNING", tone: "orange" },
  critical: { label: "CRITICAL", tone: "red" },
  blocked: { label: "BLOCKED", tone: "red" },
  active: { label: "ACTIVE", tone: "emerald" },
  inactive: { label: "INACTIVE", tone: "slate" },
}

export function getSystemStatus(value = "") {
  const normalized = String(value || "").toLowerCase()
  return SYSTEM_STATUS[normalized] || {
    label: String(value || "UNKNOWN").toUpperCase(),
    tone: "slate",
  }
}
