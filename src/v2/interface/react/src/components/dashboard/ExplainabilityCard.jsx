import React from "react";

function getExplainability(global) {
  const regime = String(global?.regime || "").toLowerCase();
  const governance = String(global?.governanceMode || "").toLowerCase();
  const riskFlags = Number(global?.riskFlags || 0);
  const ordersCount = Number(global?.ordersCount || 0);
  const candidatesCount = Number(global?.candidatesCount || 0);

  let marketReading = "Market conditions remain unclear.";
  let decision = "System stays selective.";
  let capitalProtection = "Standard protection rules remain active.";
  let executionImpact = "Execution posture remains neutral.";
  let systemStance = "Balanced posture with selective monitoring.";
  let stanceTone = "text-zinc-200 border-white/10 bg-white/5";

  if (regime.includes("risk_on") || regime.includes("bull")) {
    marketReading = "Market regime is constructive with offensive conditions available.";
    decision = "System can authorize selective offensive deployment.";
    systemStance = "Constructive posture with controlled offensive bias.";
    stanceTone = "text-emerald-200 border-emerald-500/20 bg-emerald-500/8";
  } else if (regime.includes("risk_off") || regime.includes("bear")) {
    marketReading = "Market regime is defensive and risk appetite is compressed.";
    decision = "System reduces aggressiveness and prioritizes defensive posture.";
    systemStance = "Defensive posture with capital preservation priority.";
    stanceTone = "text-red-200 border-red-500/20 bg-red-500/8";
  } else {
    marketReading = "Market regime is balanced with mixed directional signals.";
    decision = "System remains selective and avoids overcommitment.";
    systemStance = "Balanced posture with selective deployment.";
    stanceTone = "text-amber-200 border-amber-500/20 bg-amber-500/8";
  }

  if (governance.includes("caution")) {
    decision = "Governance is in CAUTION mode, so execution remains moderated.";
    systemStance = "Selective posture with moderated execution.";
    stanceTone = "text-amber-200 border-amber-500/20 bg-amber-500/8";
  } else if (governance.includes("blocked")) {
    decision = "Governance constraints are active and can restrict execution.";
    systemStance = "Restricted posture under governance constraints.";
    stanceTone = "text-red-200 border-red-500/20 bg-red-500/8";
  }

  if (riskFlags >= 3) {
    capitalProtection = "Multiple risk flags detected, so exposure should remain tightly controlled.";
  } else if (riskFlags >= 1) {
    capitalProtection = "Some risk signals are active, so capital deployment should stay monitored.";
  } else {
    capitalProtection = "No major risk alerts detected, while baseline protection remains enforced.";
  }

  if (governance.includes("blocked")) {
    executionImpact = "Execution is effectively constrained by governance and should remain highly restricted.";
  } else if (governance.includes("caution")) {
    executionImpact = "Execution is allowed, but position entry should remain filtered and reduced.";
  } else if (ordersCount > 0) {
    executionImpact = "Executable orders are available, so the system can translate signals into action.";
  } else if (candidatesCount > 0) {
    executionImpact = "Signals are present, but no final execution has been authorized yet.";
  } else {
    executionImpact = "No actionable execution flow is currently active.";
  }

  return {
    marketReading,
    decision,
    capitalProtection,
    executionImpact,
    systemStance,
    stanceTone,
  };
}

function ExplainBlock({ label, value }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-black/30 px-5 py-5 backdrop-blur-md">
      <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">
        {label}
      </div>
      <div className="mt-3 text-sm leading-6 text-zinc-200">
        {value}
      </div>
    </div>
  );
}

export default function ExplainabilityCard({ global }) {
  const {
    marketReading,
    decision,
    capitalProtection,
    executionImpact,
    systemStance,
    stanceTone,
  } = getExplainability(global);

  return (
    <div className="rounded-[28px] border border-white/10 bg-zinc-950/55 p-6 space-y-5 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent" />
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
            Decision Explainability
          </div>
          <div className="mt-2 text-lg font-semibold text-zinc-100">
            NSC Intelligence Layer
          </div>
        </div>

        <div className="rounded-full border border-white/10 bg-black/30 px-3 py-1.5 text-xs text-zinc-400">
          Narrative Engine
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-4">
        <ExplainBlock label="Market Reading" value={marketReading} />
        <ExplainBlock label="Decision" value={decision} />
        <ExplainBlock label="Capital Protection" value={capitalProtection} />
        <ExplainBlock label="Execution Impact" value={executionImpact} />
      </div>

      <div className={["rounded-[24px] border px-5 py-5", stanceTone].join(" ")}>
        <div className="text-[10px] uppercase tracking-[0.18em] opacity-70">
          System Stance
        </div>
        <div className="mt-3 text-base font-medium leading-7">
          {systemStance}
        </div>
      </div>
    </div>
  );
}
