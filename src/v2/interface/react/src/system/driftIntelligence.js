export function classifyDrift({
  drift = 0,
  target = 0,
  current = 0,
  policy = "",
  mode = "",
  reason = "",
} = {}) {
  const absDrift = Math.abs(Number(drift || 0));
  const normalizedPolicy = String(policy || mode || "").toLowerCase();
  const normalizedReason = String(reason || "").toLowerCase();

  const isPreprod =
    normalizedPolicy.includes("simulated_only") ||
    normalizedPolicy.includes("preprod") ||
    normalizedPolicy.includes("paper") ||
    normalizedPolicy.includes("shadow");

  const isZeroTarget = Number(target || 0) === 0 && Number(current || 0) > 0;

  const isGoverned =
    isPreprod ||
    normalizedReason.includes("governance") ||
    normalizedReason.includes("preprod") ||
    normalizedReason.includes("manual") ||
    normalizedReason.includes("funding") ||
    normalizedReason.includes("rebalance");

  if (absDrift < 0.025) {
    return {
      type: "aligned",
      label: "Aligned",
      severity: 0,
      tone: "emerald",
      description: "Current exposure is aligned with the target allocation.",
    };
  }

  if (isGoverned || isZeroTarget) {
    return {
      type: "intentional_drift",
      label: "Governed Drift",
      severity: Math.min(60, Math.round(absDrift * 100)),
      tone: "cyan",
      description: "Allocation drift is monitored and constrained by governance or PREPROD policy.",
    };
  }

  if (absDrift < 0.08) {
    return {
      type: "monitored_drift",
      label: "Monitored Drift",
      severity: Math.min(75, Math.round(absDrift * 100)),
      tone: "amber",
      description: "Allocation drift requires monitoring but is not critical.",
    };
  }

  return {
    type: "critical_drift",
    label: "Critical Drift",
    severity: Math.min(100, Math.round(absDrift * 100)),
    tone: "red",
    description: "Allocation drift exceeds the acceptable monitoring threshold.",
  };
}

export function driftToneClasses(tone = "slate") {
  const tones = {
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    cyan: "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    orange: "border-orange-500/30 bg-orange-500/10 text-orange-300",
    red: "border-red-500/30 bg-red-500/10 text-red-300",
    slate: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  };

  return tones[tone] || tones.slate;
}
