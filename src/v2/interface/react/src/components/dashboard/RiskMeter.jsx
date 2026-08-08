import React from "react";

function getRiskLevel(global) {
  const flags = Number(global?.riskFlags || 0);
  const regime = String(global?.regime || "").toLowerCase();
  const governance = String(global?.governanceMode || "").toLowerCase();

  let score = 0;
  if (flags >= 3) score += 2;
  else if (flags >= 1) score += 1;

  if (regime.includes("risk_off")) score += 2;
  else if (regime.includes("caution")) score += 1;
  else if (regime.includes("risk_on")) score += 0;

  if (governance.includes("caution")) score += 1;
  if (governance.includes("blocked")) score += 2;

  if (score <= 1) {
    return {
      label: "LOW",
      width: "33%",
      bar: "from-emerald-400 to-emerald-500",
      text: "text-emerald-300",
      pill: "border-emerald-500/20 bg-emerald-500/10 text-emerald-200",
      tone: "border-emerald-500/15 bg-emerald-500/[0.05]",
      summary: "Risk posture remains contained and baseline deployment can stay active.",
    };
  }

  if (score <= 3) {
    return {
      label: "MEDIUM",
      width: "66%",
      bar: "from-amber-300 to-amber-500",
      text: "text-amber-300",
      pill: "border-amber-500/20 bg-amber-500/10 text-amber-200",
      tone: "border-amber-500/15 bg-amber-500/[0.05]",
      summary: "Risk posture is moderated and execution should stay selective.",
    };
  }

  return {
    label: "HIGH",
    width: "100%",
    bar: "from-red-400 to-red-500",
    text: "text-red-300",
    pill: "border-red-500/20 bg-red-500/10 text-red-200",
    tone: "border-red-500/15 bg-red-500/[0.05]",
    summary: "Risk posture is elevated and capital protection should dominate.",
  };
}

function MetricPill({ label, value }) {
  return (
    <div className="rounded-full border border-white/10 bg-black/20 px-4 py-2.5">
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-sm font-medium text-zinc-100">
        {value}
      </div>
    </div>
  );
}

export default function RiskMeter({ global }) {
  const risk = getRiskLevel(global);
  const flags = Number(global?.riskFlags || 0);
  const regime = global?.regime || "UNKNOWN";
  const governance = global?.governanceMode || "UNKNOWN";

  return (
    <div className={["relative overflow-hidden rounded-[28px] border p-6 backdrop-blur-md", risk.tone].join(" ")}>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />

      <div className="relative space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
              Risk Console
            </div>
            <div className="mt-2 text-lg font-semibold text-zinc-100">
              Global Risk Level
            </div>
          </div>

          <div className={["rounded-full border px-4 py-2 text-xs font-medium", risk.pill].join(" ")}>
            {risk.label}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">Risk intensity</span>
            <span className={["font-medium", risk.text].join(" ")}>{risk.label}</span>
          </div>

          <div className="h-3 rounded-full bg-zinc-900/80 overflow-hidden">
            <div
              className={["h-3 rounded-full bg-gradient-to-r shadow-sm", risk.bar].join(" ")}
              style={{ width: risk.width }}
            />
          </div>

          <div className="text-sm text-zinc-400 leading-6">
            {risk.summary}
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <MetricPill label="Regime" value={regime} />
          <MetricPill label="Governance" value={governance} />
          <MetricPill label="Risk Flags" value={flags} />
        </div>
      </div>
    </div>
  );
}
