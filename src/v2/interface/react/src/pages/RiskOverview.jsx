import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson, apiUrl } from "../lib/apiClient";

const BRICK_LABELS = {
  crypto: "Crypto",
  equities_offensive: "Offensive",
  equities_defensive: "Defensive",
  bonds: "Bonds",
  precious_metals: "Metals",
  long_term: "Long Term",
  options_us: "Options US · Simulated",
  options_v2_shadow: "Options V2 · Shadow",
};

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function pct(v) {
  return `${(num(v) * 100).toFixed(1)}%`;
}

function shortId(v) {
  const s = String(v || "—");
  if (s.length <= 14) return s;
  return `${s.slice(0, 10)}…${s.slice(-4)}`;
}

function Box({ children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20 hover:shadow-[0_0_40px_rgba(34,211,238,0.06)] ${className}`}>
      {children}
    </div>
  );
}

function LiveIndicator({ label = "LIVE", tone = "emerald" }) {
  const toneMap = {
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
    amber: "border-amber-400/20 bg-amber-400/10 text-amber-300",
    red: "border-red-400/20 bg-red-400/10 text-red-300",
    violet: "border-violet-400/20 bg-violet-400/10 text-violet-300",
  };

  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
    violet: "bg-violet-400",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] ${toneMap[tone] || toneMap.emerald}`}>
      <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${dotMap[tone] || dotMap.emerald}`}></span>
      {label}
    </span>
  );
}

function PremiumSectionHeader({ title, subtitle, tone = "cyan", badges = [] }) {
  const toneMap = {
    emerald: "border-emerald-400/10 from-[#071018] via-[#0b1a19] to-[#071018] text-emerald-100",
    cyan: "border-cyan-400/10 from-[#071018] via-[#0a1724] to-[#071018] text-cyan-100",
    amber: "border-amber-400/10 from-[#100d08] via-[#17120a] to-[#100d08] text-amber-100",
    red: "border-red-400/10 from-[#160808] via-[#1a0c0c] to-[#100808] text-red-100",
    violet: "border-violet-400/10 from-[#080d18] via-[#101426] to-[#080d18] text-violet-100",
  };

  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
    violet: "bg-violet-400",
  };

  return (
    <div className={`mb-3 rounded-2xl border bg-gradient-to-r px-5 py-4 shadow-[0_0_50px_rgba(34,211,238,0.05)] ${toneMap[tone] || toneMap.cyan}`}>
      <div className="flex items-center justify-between gap-2.5">
        <div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full animate-pulse ${dotMap[tone] || dotMap.cyan}`}></div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em]">{title}</div>
          </div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-500">{subtitle}</div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
          {badges.map((badge, idx) => (
            <span key={idx} className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">
              {badge}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function Title({ children, right }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[13px] font-semibold uppercase tracking-wide text-white">{children}</h3>
      {right ? <div className="text-[10px] uppercase tracking-wide text-slate-500">{right}</div> : null}
    </div>
  );
}

function Metric({ label, value, tone = "white" }) {
  const tones = {
    white: "text-white",
    green: "text-emerald-400",
    amber: "text-amber-300",
    red: "text-red-400",
    blue: "text-sky-300",
    slate: "text-slate-300",
  };

  return (
    <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 truncate text-base font-semibold ${tones[tone] || tones.white}`} title={String(value)}>{value}</div>
    </div>
  );
}

function StatusPill({ children, tone = "blue" }) {
  const tones = {
    green: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-300",
    red: "border-red-400/30 bg-red-400/10 text-red-300",
    blue: "border-sky-400/30 bg-sky-400/10 text-sky-300",
    slate: "border-slate-400/20 bg-slate-400/10 text-slate-300",
  };

  return (
    <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${tones[tone] || tones.blue}`}>
      {children}
    </span>
  );
}

function RiskBar({ value }) {
  const width = Math.max(0, Math.min(100, Math.abs(num(value)) * 100));
  const color = width >= 8 ? "bg-red-500" : width >= 3 ? "bg-amber-400" : "bg-emerald-400";

  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className={`h-1.5 rounded ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}


function parseRuntimeTimestamp(value) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

function ageSeconds(value) {
  const parsed = parseRuntimeTimestamp(value);

  if (!parsed) {
    return null;
  }

  return Math.max(
    0,
    Math.round((Date.now() - parsed.getTime()) / 1000)
  );
}

function telemetryFreshness(value, staleAfterSeconds = 300) {
  const age = ageSeconds(value);

  if (age === null) {
    return {
      value: "UNAVAILABLE",
      status: "UNAVAILABLE",
      color: "slate",
      age: null,
    };
  }

  return {
    value: `${age}s`,
    status: age <= staleAfterSeconds ? "LIVE" : "STALE",
    color: age <= staleAfterSeconds ? "emerald" : "amber",
    age,
  };
}

export default function RiskOverview() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [portfolioState, setPortfolioState] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [rebalancePlan, setRebalancePlan] = useState(null);
  const [fundingPlan, setFundingPlan] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [executionPlan, setExecutionPlan] = useState(null);
  const [executionOrders, setExecutionOrders] = useState(null);
  const [explainability, setExplainability] = useState([]);
  const [explainabilitySummary, setExplainabilitySummary] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const [stateRes, targetRes, rebalanceRes, fundingRes, govRes, execRes, ordersRes] = await Promise.all([
        fetchJson("/api/portfolio-state", { timeoutMs: 8000 }),
        fetchJson("/api/portfolio-target", { timeoutMs: 8000 }),
        fetchJson("/api/rebalance-plan", { timeoutMs: 8000 }),
        fetchJson("/api/funding-plan", { timeoutMs: 8000 }),
        fetchJson("/governance/status", { timeoutMs: 8000 }),
        fetchJson("/api/execution-plan", { timeoutMs: 8000 }),
        fetchJson("/api/execution-orders", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      if (!stateRes?.ok && !targetRes?.ok) setErr("Unable to load risk data sources.");

      setPortfolioState(stateRes?.ok ? stateRes.data : null);
      setPortfolioTarget(targetRes?.ok ? targetRes.data : null);
      setRebalancePlan(rebalanceRes?.ok ? rebalanceRes.data : null);
      setFundingPlan(fundingRes?.ok ? fundingRes.data : null);
      setGovernance(govRes?.ok ? govRes.data : null);
      setExecutionPlan(execRes?.ok ? execRes.data : null);
      setExecutionOrders(ordersRes?.ok ? ordersRes.data : null);

      try {
        const explainRes = await fetch(apiUrl("/api/explainability"), { credentials: "include" });
        if (explainRes.ok) {
          const explainJson = await explainRes.json();
          if (!cancelled) {
            setExplainability(explainJson?.explanations || []);
            setExplainabilitySummary(explainJson?.summary || null);
          }
        }
      } catch {
        // keep page resilient
      }

      setLoading(false);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const ps = portfolioState?.data || portfolioState || {};
  const pt = portfolioTarget?.data || portfolioTarget || {};
  const bricks = ps?.bricks || {};
  const targetWeights = pt?.final_brick_weights || {};

  const driftRows = useMemo(() => {
    const keys = Array.from(new Set([...Object.keys(bricks), ...Object.keys(targetWeights)]));
    return keys.map((key) => {
      const b = bricks[key] || {};
      const target = num(targetWeights[key] ?? b.target_weight_snapshot);
      const exposure = num(b.current_weight_estimate ?? b.target_weight_snapshot ?? target);
      const drift = exposure - target;
      const severity = Math.abs(drift) >= 0.08 ? "HIGH" : Math.abs(drift) >= 0.03 ? "MEDIUM" : "LOW";

      return {
        key,
        label: BRICK_LABELS[key] || key,
        target,
        exposure,
        drift,
        severity,
        status: b.status || "UNKNOWN",
        origin: b.state_origin || "signal_derived",
      };
    }).sort((a, b) => Math.abs(b.drift) - Math.abs(a.drift));
  }, [bricks, targetWeights]);

  const maxDrift = driftRows.reduce((acc, row) => Math.max(acc, Math.abs(row.drift)), 0);
  const highDriftCount = driftRows.filter((row) => Math.abs(row.drift) >= 0.08).length;
  const mediumDriftCount = driftRows.filter((row) => Math.abs(row.drift) >= 0.03).length;

  const topDriftRow = driftRows[0] || null;
  const topDriftLabel = topDriftRow?.label || topDriftRow?.key || "portfolio sleeve";
  const topDriftAbsPct = Math.abs(num(topDriftRow?.drift)) * 100;
  const topDriftDirection = num(topDriftRow?.drift) < 0 ? "under-allocated" : "over-allocated";

  const approvedActions = Array.isArray(rebalancePlan?.actions)
    ? rebalancePlan.actions.filter((a) => a.status === "approved")
    : [];

  const hardBlock =
    String(governance?.mode || "").toUpperCase() === "HARD_BLOCK" ||
    String(governance?.action_policy || "").toUpperCase() === "BLOCKED" ||
    executionPlan?.blocked === true;

  const killSwitch = hardBlock ? "ON" : "OFF";
  const governanceMode = governance?.mode || governance?.governance_mode || (executionPlan?.blocked ? "SAFE" : "NORMAL");
  const actionPolicy = governance?.action_policy || executionPlan?.action_policy || executionPlan?.execution_mode || "SIM";

  const manualFundingRequired =
    fundingPlan?.requires_manual_transfer_between_pools === true ||
    fundingPlan?.manual_approval_required === true ||
    fundingPlan?.inter_universe_transfer?.automatic_transfer_allowed === false;

  const regime = pt?.portfolio_regime || ps?.portfolio_regime || "UNKNOWN";

  const severity =
    hardBlock || executionPlan?.blocked
      ? "CRITICAL"
      : maxDrift >= 0.08
        ? "WATCH"
        : maxDrift >= 0.03
          ? "WATCH"
          : "LOW";

  const riskPressureScore = Math.max(
    0,
    Math.min(
      100,
      Math.round(
        (maxDrift * 180)
        + (hardBlock ? 35 : 0)
        + (executionPlan?.blocked ? 25 : 0)
        + (approvedActions.length * 8)
        + (manualFundingRequired ? 8 : 0)
      )
    )
  );

  const riskPressureLabel =
    riskPressureScore >= 70 ? "HIGH" :
    riskPressureScore >= 35 ? "WATCH" :
    "LOW";

  const riskPressureClass =
    riskPressureLabel === "HIGH"
      ? "text-red-400"
      : riskPressureLabel === "WATCH"
      ? "text-amber-300"
      : "text-emerald-400";

  const riskPressureBar =
    riskPressureLabel === "HIGH"
      ? "bg-red-400"
      : riskPressureLabel === "WATCH"
      ? "bg-amber-300"
      : "bg-emerald-400";

  const riskBrickLabel = (key) => ({
    crypto: "Crypto",
    equities_offensive: "Offensive Equities",
    equities_defensive: "Defensive Equities",
    bonds: "Bonds",
    precious_metals: "Precious Metals",
    metals: "Precious Metals",
    options_v2_shadow: "Options V2 · Shadow",
    options_us: "Options US · Simulated",
    long_term: "Long Term",
  }[key] || String(key || "Unknown").replaceAll("_", " "));

  const topRiskContributors = [...driftRows]
    .sort((a, b) => Math.abs(b.drift || 0) - Math.abs(a.drift || 0))
    .slice(0, 8)
    .map((row) => {
      const absDrift = Math.abs(row.drift || 0);
      return {
        ...row,
        pressure: Math.min(100, Math.round(absDrift * 260)),
        severity: absDrift >= 0.25 ? "HIGH" : absDrift >= 0.10 ? "WATCH" : "LOW",
      };
    });


  const governanceEvents = [
    {
      ts: "LIVE",
      label: hardBlock
        ? "Governance hard block active"
        : "Governance operating normally",
      tone: hardBlock ? "red" : "emerald"
    },
    {
      ts: "LIVE",
      label:
        maxDrift >= 0.08
          ? "Portfolio drift escalation detected"
          : "Portfolio drift remains stable",
      tone:
        maxDrift >= 0.08
          ? "amber"
          : "emerald"
    },
    {
      ts: "LIVE",
      label:
        executionPlan?.blocked
          ? "Execution validation required"
          : "Execution layer synchronized",
      tone:
        executionPlan?.blocked
          ? "red"
          : "cyan"
    },
    {
      ts: "LIVE",
      label:
        manualFundingRequired
          ? "Manual funding transfer required"
          : "Funding pools synchronized",
      tone:
        manualFundingRequired
          ? "amber"
          : "emerald"
    }
  ];

  const driftTrend =
    maxDrift >= 0.15
      ? "WORSENING"
      : maxDrift >= 0.05
      ? "WATCH"
      : "STABLE";

  const driftTrendClass =
    driftTrend === "WORSENING"
      ? "text-red-400"
      : driftTrend === "WATCH"
      ? "text-amber-300"
      : "text-emerald-400";

  const driftTrendBg =
    driftTrend === "WORSENING"
      ? "border-red-500/20 bg-red-500/5"
      : driftTrend === "WATCH"
      ? "border-amber-500/20 bg-amber-500/5"
      : "border-emerald-500/20 bg-emerald-500/5";

  const rebalanceUrgency =
    maxDrift >= 0.25 ? "HIGH" :
    maxDrift >= 0.10 ? "MEDIUM" :
    "LOW";

  const alerts = [];
  if (hardBlock) alerts.push("Execution is currently blocked by governance.");
  if (maxDrift >= 0.08) alerts.push(topDriftRow ? `${topDriftLabel} sleeve ${topDriftDirection} by ${topDriftAbsPct.toFixed(1)} pts vs target.` : "High portfolio drift detected on at least one sleeve.");
  if (approvedActions.length > 0) alerts.push(`${approvedActions.length} approved rebalance action(s) require supervision.`);
  if (manualFundingRequired) alerts.push("Inter-pool transfers remain manual only.");
  if (!alerts.length) alerts.push("No critical blocker at the moment.");

  const suggestedActions = [];
  if (maxDrift >= 0.25) suggestedActions.push(topDriftRow ? `Review ${topDriftLabel.toLowerCase()} allocation gap before next rebalance cycle.` : "Reduce portfolio drift exposure.");
  if (maxDrift >= 0.08) suggestedActions.push(topDriftRow ? `Validate whether ${topDriftLabel.toLowerCase()} under-allocation is intentional or requires manual funding.` : "Review highest deviation sleeves.");
  if (approvedActions.length > 0) suggestedActions.push("Validate pending rebalance actions.");
  if (hardBlock) suggestedActions.push("Resolve governance blocker before execution.");
  if (!suggestedActions.length) suggestedActions.push("Continue monitoring under current policy.");

  const executionReadinessScore = Math.max(
    0,
    Math.min(
      100,
      Math.round(
        100
          - (hardBlock ? 45 : 0)
          - (executionPlan?.blocked ? 35 : 0)
          - (maxDrift >= 0.25 ? 25 : maxDrift >= 0.08 ? 15 : maxDrift >= 0.03 ? 7 : 0)
          - (approvedActions.length > 0 ? 8 : 0)
          - (manualFundingRequired ? 6 : 0)
      )
    )
  );

  const executionReadinessLabel =
    hardBlock || executionPlan?.blocked
      ? "BLOCKED"
      : executionReadinessScore >= 75
      ? "READY"
      : executionReadinessScore >= 50
      ? "DEGRADED"
      : "WATCH";

  const executionReadinessClass =
    executionReadinessLabel === "READY"
      ? "text-emerald-400"
      : executionReadinessLabel === "DEGRADED"
      ? "text-amber-300"
      : "text-red-400";

  const executionReadinessBar =
    executionReadinessLabel === "READY"
      ? "bg-emerald-400"
      : executionReadinessLabel === "DEGRADED"
      ? "bg-amber-300"
      : "bg-red-400";

  const riskConfidencePct = (() => {
    const weights = pt?.final_brick_weights || {};
    const confidences = pt?.brick_confidence || {};

    let weighted = 0;
    let total = 0;

    Object.entries(weights).forEach(([brick, weight]) => {
      const w = num(weight);
      const c = num(confidences?.[brick]);

      if (w > 0 && c > 0) {
        weighted += w * c;
        total += w;
      }
    });

    if (total > 0) {
      return Math.round((weighted / total) * 100);
    }

    const raw = num(
      portfolioTarget?.confidencePct ??
      portfolioTarget?.confidence_pct ??
      portfolioTarget?.portfolio_confidence_pct ??
      portfolioTarget?.confidence ??
      0
    );

    return Math.round(raw > 1 ? raw : raw * 100);
  })();

  const dashboardGlobal =
    portfolioState?.dashboard_global ||
    portfolioState?.global ||
    {};

  const governanceGeneratedAt =
    governance?.generated_at ||
    governance?.updated_at ||
    dashboardGlobal?.lastRefresh ||
    null;

  const executionGeneratedAt =
    executionOrders?.generated_at ||
    executionOrders?.updated_at ||
    executionPlan?.generated_at ||
    executionPlan?.updated_at ||
    null;

  const heartbeatTelemetry =
    telemetryFreshness(
      executionGeneratedAt ||
      governanceGeneratedAt,
      300
    );

  const governanceTelemetry =
    telemetryFreshness(
      governanceGeneratedAt,
      300
    );

  const orchestrationStatus =
    dashboardGlobal?.orchestrationStatus ||
    portfolioState?.orchestration_status ||
    portfolioState?.orchestrationStatus ||
    null;

  const orchestrationOnline =
    ["OK", "HEALTHY", "RUNNING", "ONLINE"].includes(
      String(orchestrationStatus || "").toUpperCase()
    );

  const portfolioStateRegime =
    portfolioState?.portfolio_regime ||
    portfolioState?.data?.portfolio_regime ||
    null;

  const portfolioTargetRegime =
    portfolioTarget?.portfolio_regime ||
    portfolioTarget?.data?.portfolio_regime ||
    null;

  const portfolioSyncAvailable =
    Boolean(portfolioStateRegime && portfolioTargetRegime);

  const portfolioSynchronized =
    portfolioSyncAvailable &&
    String(portfolioStateRegime) ===
      String(portfolioTargetRegime);


  const telemetryItems = [
    {
      label: "API LATENCY",
      value: "UNAVAILABLE",
      status: "UNAVAILABLE",
      color: "slate",
    },
    {
      label: "HEARTBEAT",
      value: heartbeatTelemetry.value,
      status: heartbeatTelemetry.status,
      color: heartbeatTelemetry.color,
    },
    {
      label: "GOV FRESHNESS",
      value: governanceTelemetry.value,
      status: governanceTelemetry.status,
      color: governanceTelemetry.color,
    },
    {
      label: "ORCHESTRATOR",
      value: orchestrationStatus || "UNAVAILABLE",
      status: orchestrationStatus
        ? orchestrationOnline
          ? "OK"
          : "WATCH"
        : "UNAVAILABLE",
      color: orchestrationStatus
        ? orchestrationOnline
          ? "emerald"
          : "amber"
        : "slate",
    },
    {
      label: "EXECUTION QUEUE",
      value: `${approvedActions.length || 0}`,
      status:
        approvedActions.length > 0
          ? "PENDING"
          : "CLEAR",
      color:
        approvedActions.length > 0
          ? "amber"
          : "emerald",
    },
    {
      label: "PORTFOLIO SYNC",
      value: portfolioSyncAvailable
        ? portfolioSynchronized
          ? "SYNCED"
          : "MISMATCH"
        : "UNAVAILABLE",
      status: portfolioSyncAvailable
        ? portfolioSynchronized
          ? "OK"
          : "WARN"
        : "UNAVAILABLE",
      color: portfolioSyncAvailable
        ? portfolioSynchronized
          ? "cyan"
          : "amber"
        : "slate",
    },
  ];

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Risk layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-2.5">
        <div className="mx-auto max-w-[1680px] space-y-2">
        <header className="rounded-2xl border border-[#1f2a37] bg-[radial-gradient(circle_at_top_left,#102033_0%,#09111a_42%,#05080d_100%)] p-2.5 shadow-[0_0_50px_rgba(34,211,238,0.08)]">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold whitespace-nowrap uppercase tracking-wide">Risk Console</h1>
            <p className="text-xs text-slate-400">
              Governance, kill-switch, exposure drift, blockers and execution readiness
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <LiveIndicator label={loading ? "SYNCING" : "LIVE RISK"} tone={severity === "LOW" ? "emerald" : severity === "WATCH" || severity === "MEDIUM" ? "amber" : "red"} />
            <StatusPill tone={killSwitch === "ON" ? "red" : "green"}>Kill Switch {killSwitch}</StatusPill>
            <StatusPill tone={severity === "LOW" ? "green" : severity === "WATCH" || severity === "MEDIUM" ? "amber" : "red"}>{severity}</StatusPill>
            <StatusPill tone="blue">{String(regime).toUpperCase()}</StatusPill>
            <StatusPill tone="amber">{String(actionPolicy).toUpperCase()}</StatusPill>
          </div>
        </div>
        </header>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-2.5 text-xs text-red-200">
            {err}
          </Box>
        ) : null}

        <PremiumSectionHeader
          title="Risk Protection Layer"
          subtitle="Kill-switch, severity, exposure drift and execution readiness"
          tone={severity === "LOW" ? "emerald" : severity === "WATCH" || severity === "MEDIUM" ? "amber" : "red"}
          badges={["portfolio risk", "governance linked", "preprod protected"]}
        />

        <Box className="mb-3 border-cyan-500/15 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.12),rgba(7,17,29,0.96)_38%,rgba(5,8,13,0.98)_100%)] p-3">
          <div className="grid grid-cols-[1.1fr_0.9fr_0.9fr_0.9fr_0.9fr] gap-3">
            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
                Global Risk Level
              </div>
              <div className={`mt-2 text-3xl font-semibold ${
                severity === "LOW" ? "text-emerald-300" : severity === "WATCH" || severity === "MEDIUM" ? "text-amber-300" : "text-red-300"
              }`}>
                {severity}
              </div>
              <div className="mt-2 text-[11px] leading-4 text-slate-400">
                Current NSC risk posture based on drift, governance, blockers and execution readiness.
              </div>
            </div>

            {[
              {
                title: "Market Risk",
                value: severity === "LOW" ? "LOW" : severity,
                meta1: `Regime ${String(regime).toUpperCase()}`,
                meta2: `Confidence ${riskConfidencePct}%`,
                tone: severity === "LOW" ? "green" : severity === "MEDIUM" ? "amber" : "red",
              },
              {
                title: "Governance Risk",
                value: hardBlock ? "HIGH" : "LOW",
                meta1: `Status ${String(governanceMode).toUpperCase()}`,
                meta2: `Policy ${String(actionPolicy).toUpperCase()}`,
                tone: hardBlock ? "red" : "green",
              },
              {
                title: "Funding Risk",
                value: fundingPlan?.manual_approval_required ? "WATCH" : "LOW",
                meta1: `Cash Buffer ${pct(num(portfolioState?.cash_available_eur) / Math.max(1, num(portfolioState?.capital_observed_eur, 1)))}`,
                meta2: fundingPlan?.manual_approval_required ? "Manual approval YES" : "Manual approval NO",
                tone: fundingPlan?.manual_approval_required ? "amber" : "green",
              },
              {
                title: "Execution Risk",
                value: executionPlan?.blocked ? "HIGH" : "LOW",
                meta1: `Orders ${approvedActions.length || 0}`,
                meta2: executionPlan?.blocked ? "Execution BLOCKED" : "Execution clear",
                tone: executionPlan?.blocked ? "red" : "green",
              },
            ].map((d) => (
              <div key={d.title} className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">{d.title}</div>
                    <div className={`mt-2 text-2xl font-semibold ${
                      d.tone === "red" ? "text-red-300" : d.tone === "amber" ? "text-amber-300" : "text-emerald-300"
                    }`}>
                      {d.value}
                    </div>
                  </div>
                  <span className={`rounded-full border px-2 py-0.5 text-[8px] font-semibold uppercase tracking-wide ${
                    d.tone === "red"
                      ? "border-red-400/25 bg-red-400/10 text-red-300"
                      : d.tone === "amber"
                        ? "border-amber-300/25 bg-amber-300/10 text-amber-200"
                        : "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
                  }`}>
                    {d.value}
                  </span>
                </div>
                <div className="mt-3 space-y-1 text-[10px] text-slate-400">
                  <div>{d.meta1}</div>
                  <div>{d.meta2}</div>
                </div>
              </div>
            ))}
          </div>
        </Box>

        <div className="mb-3 grid grid-cols-5 gap-2.5">
          <Metric label="Risk Severity" value={severity} tone={severity === "LOW" ? "green" : severity === "WATCH" || severity === "MEDIUM" ? "amber" : "red"} />
          <Metric label="Max Drift" value={pct(maxDrift)} tone={maxDrift >= 0.08 ? "red" : maxDrift >= 0.03 ? "amber" : "green"} />
          <Metric label="High Drift" value={highDriftCount} tone={highDriftCount > 0 ? "red" : "green"} />
          <Metric label="Approved Portfolio Actions" value={approvedActions.length} tone={approvedActions.length > 0 ? "amber" : "slate"} />
          <Metric label="Execution Blocked" value={executionPlan?.blocked ? "YES" : "NO"} tone={executionPlan?.blocked ? "red" : "green"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.35fr_1fr] gap-2.5">
          <Box className="p-2.5">
            <Title right={loading ? "Loading" : "Live"}>Risk Command Center</Title>
            <div className="grid grid-cols-3 gap-2.5">
              <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] p-2.5 min-h-[178px]">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Governance</div>
                <div className="mt-2 text-base font-semibold text-sky-300">{String(governanceMode).toUpperCase()}</div>
                <div className="mt-3 text-[13px] leading-5 text-slate-300">
                  Current policy: <span className="text-amber-300">{String(actionPolicy).toUpperCase()}</span>
                </div>
              </div>

              <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] p-2.5 min-h-[178px]">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Protection</div>
                <div className={`mt-2 text-base font-semibold ${killSwitch === "ON" ? "text-red-400" : "text-emerald-400"}`}>
                  {killSwitch === "ON" ? "BLOCKED" : "PROTECTED"}
                </div>
                <div className="mt-3 text-[13px] leading-5 text-slate-300">
                  Hard block: {hardBlock ? "active" : "inactive"} · Execution blocked: {executionPlan?.blocked ? "yes" : "no"}
                </div>
              </div>

              <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] p-2.5 min-h-[178px]">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Risk Reading</div>
                <div className={`mt-2 text-base font-semibold ${severity === "LOW" ? "text-emerald-400" : severity === "MEDIUM" ? "text-amber-300" : "text-red-400"}`}>
                  {severity}
                </div>
                <div className="mt-3 text-[13px] leading-5 text-slate-300">
                  Drift and rebalance pressure remain the main monitored risks.
                </div>
              </div>

              <div className={`rounded-lg border p-2.5 ${driftTrendBg}`}>
                <div className="flex items-center justify-between">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">
                    Drift Trend
                  </div>

                  <div className={`flex items-center gap-1 text-[10px] font-semibold ${driftTrendClass}`}>
                    <span className="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse" />
                    LIVE
                  </div>
                </div>

                <div className={`mt-2 text-base font-semibold ${driftTrendClass}`}>
                  {driftTrend}
                </div>

                <div className="mt-3">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full rounded-full ${
                        driftTrend === "WORSENING"
                          ? "bg-red-400"
                          : driftTrend === "WATCH"
                          ? "bg-amber-300"
                          : "bg-emerald-400"
                      }`}
                      style={{
                        width:
                          driftTrend === "WORSENING"
                            ? "88%"
                            : driftTrend === "WATCH"
                            ? "54%"
                            : "18%"
                      }}
                    />
                  </div>
                </div>

                <div className="mt-3 text-[13px] leading-5 text-slate-300">
                  Real-time drift deterioration monitoring across portfolio sleeves.
                </div>
              </div>

              <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">
                    Execution Readiness
                  </div>

                  <div className={`flex items-center gap-1 text-[10px] font-semibold ${executionReadinessClass}`}>
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    LIVE
                  </div>
                </div>

                <div className={`mt-2 text-base font-semibold ${executionReadinessClass}`}>
                  {executionReadinessScore}/100
                </div>

                <div className={`mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${executionReadinessClass}`}>
                  {executionReadinessLabel}
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className={`h-full rounded-full ${executionReadinessBar}`}
                    style={{ width: `${executionReadinessScore}%` }}
                  />
                </div>

                <div className="mt-3 text-[13px] leading-5 text-slate-300">
                  Execution readiness combines governance, blockers, drift pressure and funding constraints.
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-2.5">
            <div className="mb-3 flex items-center justify-between">
              <Title>Alerts / Blockers</Title>

              <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${
                rebalanceUrgency === "HIGH"
                  ? "border-red-500/30 bg-red-500/10 text-red-300"
                  : rebalanceUrgency === "MEDIUM"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              }`}>
                {rebalanceUrgency} urgency
              </span>
            </div>

            <div className="space-y-2">
              {alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className={`rounded-lg border px-3 py-2 text-xs ${
                    idx === 0 && alert.includes("No critical")
                      ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-100"
                      : "border-amber-500/20 bg-amber-500/5 text-amber-100"
                  }`}
                >
                  {alert}
                </div>
              ))}

              <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-2.5">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-300">
                  Suggested actions
                </div>

                <div className="space-y-2">
                  {suggestedActions.map((action, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-cyan-500/20 bg-[#07131d] px-3 py-2 text-[11px] text-cyan-100"
                    >
                      → {action}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Box>
        </div>

        <div className="mb-3 grid grid-cols-6 gap-2.5">
          {telemetryItems.map((item, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-cyan-500/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(5,10,18,0.96))] px-3 py-2 shadow-[0_0_20px_rgba(34,211,238,0.06)] transition-all duration-300 hover:shadow-[0_0_28px_rgba(34,211,238,0.10)]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    item.status === "LIVE" || item.status === "SYNC" || item.status === "OK"
                      ? "bg-emerald-400 animate-pulse"
                      : item.status === "PENDING"
                      ? "bg-amber-300 animate-pulse"
                      : "bg-slate-500"
                  }`} />
                  <div className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                    {item.label}
                  </div>
                </div>

                <div
                  className={`text-[9px] font-semibold ${
                    item.color === "emerald"
                      ? "text-emerald-400"
                      : item.color === "amber"
                      ? "text-amber-300"
                      : item.color === "violet"
                      ? "text-violet-300"
                      : "text-cyan-300"
                  }`}
                >
                  {item.status}
                </div>
              </div>

              <div
                className={`mt-2 text-base font-semibold ${
                  item.color === "emerald"
                    ? "text-emerald-400"
                    : item.color === "amber"
                    ? "text-amber-300"
                    : item.color === "violet"
                    ? "text-violet-300"
                    : "text-cyan-300"
                }`}
              >
                {item.value}
              </div>

              <div className="mt-3 h-[2px] overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full ${
                    item.color === "emerald"
                      ? "bg-emerald-400"
                      : item.color === "amber"
                      ? "bg-amber-300"
                      : item.color === "violet"
                      ? "bg-violet-300"
                      : "bg-cyan-300"
                  }`}
                  style={{ width: "100%", boxShadow: "0 0 14px currentColor" }}
                />
              </div>
            </div>
          ))}
        </div>

        <PremiumSectionHeader
          title="Exposure Drift Intelligence"
          subtitle="Target versus state, sleeve drift severity and allocation-origin monitoring"
          tone="cyan"
          badges={["target/state", "drift monitor", "policy layer"]}
        />

        <div className="mb-3 grid grid-cols-1 gap-2.5">
          <Box className="p-2.5">
            <Title>Exposure Drift Monitor</Title>
            <div className="grid grid-cols-[1fr_70px_70px_130px_70px_80px_100px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
              <div>Brick</div>
              <div>Target</div>
              <div>Exposure</div>
              <div></div>
              <div>Drift</div>
              <div>Severity</div>
              <div>Origin</div>
            </div>

            <div className="space-y-2 pt-2">
              {driftRows.map((row) => (
                <div key={row.key} className="grid grid-cols-[1fr_70px_70px_130px_70px_80px_100px] items-center gap-2 text-xs">
                  <div className="truncate text-slate-200">{row.label}</div>
                  <div className="text-slate-300">{pct(row.target)}</div>
                  <div className="text-slate-300">{pct(row.exposure)}</div>
                  <RiskBar value={row.drift} />
                  <div className={Math.abs(row.drift) >= 0.08 ? "text-red-400" : Math.abs(row.drift) >= 0.03 ? "text-amber-300" : "text-emerald-400"}>
                    {(row.drift * 100).toFixed(1)}%
                  </div>
                  <div className={row.severity === "HIGH" ? "text-red-400" : row.severity === "MEDIUM" ? "text-amber-300" : "text-emerald-400"}>
                    {row.severity}
                  </div>
                  <div className="truncate text-slate-500">{row.origin}</div>
                </div>
              ))}
            </div>
          </Box>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                Risk Heatmap
              </div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Cross-brick pressure, drift and severity snapshot
              </div>
            </div>

            <div className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Live
            </div>
          </div>

          <div className="grid grid-cols-6 gap-2">
            {driftRows.map((row) => {
              const absDrift = Math.abs(row.drift || 0);
              const severity =
                absDrift >= 0.25 ? "HIGH" :
                absDrift >= 0.10 ? "WATCH" :
                "LOW";

              return (
                <div
                  key={row.key}
                  className={`rounded-xl border p-3 ${
                    severity === "HIGH"
                      ? "border-red-500/25 bg-red-500/[0.06]"
                      : severity === "WATCH"
                      ? "border-amber-500/25 bg-amber-500/[0.05]"
                      : "border-emerald-500/20 bg-emerald-500/[0.04]"
                  }`}
                >
                  <div className="truncate text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-300">
                    {riskBrickLabel(row.key)}
                  </div>

                  <div className={`mt-2 text-lg font-semibold whitespace-nowrap ${
                    severity === "HIGH"
                      ? "text-red-300"
                      : severity === "WATCH"
                      ? "text-amber-300"
                      : "text-emerald-300"
                  }`}>
                    {(absDrift * 100).toFixed(1)}%
                  </div>

                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full rounded-full ${
                        severity === "HIGH"
                          ? "bg-red-400"
                          : severity === "WATCH"
                          ? "bg-amber-300"
                          : "bg-emerald-400"
                      }`}
                      style={{ width: `${Math.min(100, absDrift * 260)}%` }}
                    />
                  </div>

                  <div className="mt-2 text-[9px] uppercase tracking-[0.12em] text-slate-500">
                    {severity}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                Governance Timeline
              </div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Latest system decisions, constraints and supervision events
              </div>
            </div>

            <div className="rounded-md border border-violet-500/20 bg-violet-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-violet-300">
              Live Trace
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 xl:grid-cols-8">
            {[
              ["Drift escalation", maxDrift >= 0.08 ? "ACTIVE" : "CLEAR", maxDrift >= 0.08 ? "red" : "emerald"],
              ["Execution policy", String(actionPolicy || "SIM").replace("SIM", "SIM"), "amber"],
              ["Governance block", hardBlock ? "BLOCKED" : "CLEAR", hardBlock ? "red" : "emerald"],
              ["Supervision", executionPlan?.blocked ? "REVIEW" : "NORMAL", executionPlan?.blocked ? "amber" : "cyan"],
            ].map(([label, value, tone]) => (
              <div
                key={label}
                className={`flex w-full min-h-[150px] w-full flex-col justify-between overflow-hidden rounded-2xl border px-5 py-4 ${
                  tone === "red"
                    ? "border-red-500/25 bg-red-500/[0.06]"
                    : tone === "amber"
                    ? "border-amber-500/25 bg-amber-500/[0.05]"
                    : tone === "violet"
                    ? "border-violet-500/25 bg-violet-500/[0.05]"
                    : tone === "cyan"
                    ? "border-cyan-500/20 bg-cyan-500/[0.04]"
                    : "border-emerald-500/20 bg-emerald-500/[0.04]"
                }`}
              >
                <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  {label}
                </div>

                <div className={`mt-3 text-lg font-semibold whitespace-nowrap leading-tight tracking-tight ${
                  tone === "red"
                    ? "text-red-300"
                    : tone === "amber"
                    ? "text-amber-300"
                    : tone === "violet"
                    ? "text-violet-300"
                    : tone === "cyan"
                    ? "text-cyan-300"
                    : "text-emerald-300"
                }`}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-3">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                System State Matrix
              </div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Risk, governance, execution and funding status overview
              </div>
            </div>

            <div className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Control Layer
            </div>
          </div>

          <div className="grid w-full grid-cols-2 gap-3 xl:grid-cols-4">
            {[
              {
                label: "Risk",
                value: severity,
                tone: severity === "LOW" ? "emerald" : severity === "MEDIUM" ? "amber" : "red",
                detail: `Pressure ${riskPressureScore}/100`
              },
              {
                label: "Governance",
                value: hardBlock ? "BLOCKED" : "OK",
                tone: hardBlock ? "red" : "emerald",
                detail: actionPolicy || "SIM"
              },
              {
                label: "Execution",
                value: executionPlan?.blocked ? "BLOCKED" : "READY",
                tone: executionPlan?.blocked ? "red" : "cyan",
                detail: executionPlan?.blocked ? "Execution guard active" : "Simulated execution allowed"
              },
              {
                label: "Funding",
                value: manualFundingRequired ? "MANUAL" : "READY",
                tone: manualFundingRequired ? "amber" : "emerald",
                detail: manualFundingRequired ? "Manual transfer required" : "Funding state clear"
              },
            ].map((item) => (
              <div
                key={item.label}
                className={`rounded-xl border p-3 ${
                  item.tone === "red"
                    ? "border-red-500/25 bg-red-500/[0.06]"
                    : item.tone === "amber"
                    ? "border-amber-500/25 bg-amber-500/[0.05]"
                    : item.tone === "cyan"
                    ? "border-cyan-500/20 bg-cyan-500/[0.04]"
                    : "border-emerald-500/20 bg-emerald-500/[0.04]"
                }`}
              >
                <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  {item.label}
                </div>

                <div className={`mt-2 text-sm font-semibold ${
                  item.tone === "red"
                    ? "text-red-300"
                    : item.tone === "amber"
                    ? "text-amber-300"
                    : item.tone === "cyan"
                    ? "text-cyan-300"
                    : "text-emerald-300"
                }`}>
                  {item.value}
                </div>

                <div className="mt-2 truncate text-[10px] text-slate-500">
                  {item.detail}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-2.5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                Live Governance Feed
              </div>

              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Real-time orchestration, supervision and governance events
              </div>
            </div>

            <div className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Streaming
            </div>
          </div>

          <div className="space-y-2">
            {governanceEvents.map((event, idx) => (
              <div
                key={idx}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 ${
                  event.tone === "red"
                    ? "border-red-500/20 bg-red-500/[0.05]"
                    : event.tone === "amber"
                    ? "border-amber-500/20 bg-amber-500/[0.05]"
                    : event.tone === "cyan"
                    ? "border-cyan-500/20 bg-cyan-500/[0.04]"
                    : "border-emerald-500/20 bg-emerald-500/[0.04]"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`h-1.5 w-1.5 rounded-full animate-pulse ${
                      event.tone === "red"
                        ? "bg-red-400"
                        : event.tone === "amber"
                        ? "bg-amber-300"
                        : event.tone === "cyan"
                        ? "bg-cyan-300"
                        : "bg-emerald-400"
                    }`}
                  />

                  <div className="text-[11px] text-slate-200">
                    {event.label}
                  </div>
                </div>

                <div className="text-[9px] uppercase tracking-[0.14em] text-slate-500">
                  {event.ts}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-2.5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                Top Risk Contributors
              </div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Highest portfolio pressure sources by sleeve drift
              </div>
            </div>

            <div className="rounded-md border border-red-500/20 bg-red-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-red-300">
              Pressure
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            {topRiskContributors.map((row) => (
              <div
                key={row.key}
                className={`rounded-xl border p-3 ${
                  row.severity === "HIGH"
                    ? "border-red-500/25 bg-red-500/[0.06]"
                    : row.severity === "WATCH"
                    ? "border-amber-500/25 bg-amber-500/[0.05]"
                    : "border-emerald-500/20 bg-emerald-500/[0.04]"
                }`}
              >
                <div className="truncate text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-300">
                  {riskBrickLabel(row.key)}
                </div>

                <div className={`mt-2 text-lg font-semibold whitespace-nowrap ${
                  row.severity === "HIGH"
                    ? "text-red-300"
                    : row.severity === "WATCH"
                    ? "text-amber-300"
                    : "text-emerald-300"
                }`}>
                  {row.pressure}/100
                </div>

                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className={`h-full rounded-full ${
                      row.severity === "HIGH"
                        ? "bg-red-400"
                        : row.severity === "WATCH"
                        ? "bg-amber-300"
                        : "bg-emerald-400"
                    }`}
                    style={{ width: `${row.pressure}%` }}
                  />
                </div>

                <div className="mt-2 flex justify-between text-[9px] uppercase tracking-[0.12em] text-slate-500">
                  <span>{row.severity}</span>
                  <span>{(Math.abs(row.drift || 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-2 rounded-2xl border border-[#1f2a37] bg-[#08111b] p-2.5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-white">
                Cross-Brick Pressure Map
              </div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Portfolio-level pressure propagation across NSC sleeves
              </div>
            </div>

            <div className="rounded-md border border-cyan-500/20 bg-cyan-500/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Contagion Monitor
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 xl:grid-cols-6">
            {[
              {
                source: "Crypto",
                target: "Offensive Equities",
                pressure: maxDrift >= 0.10 ? "Elevated" : "Contained",
                tone: maxDrift >= 0.10 ? "amber" : "emerald",
                reason: "Risk-on sleeve correlation"
              },
              {
                source: "Offensive Equities",
                target: "Defensive Equities",
                pressure: severity === "HIGH" ? "Rotation watch" : "Balanced",
                tone: severity === "HIGH" ? "amber" : "cyan",
                reason: "Offensive to defensive rotation"
              },
              {
                source: "Defensive Equities",
                target: "Bonds",
                pressure: severity === "HIGH" ? "Stabilizer active" : "Normal",
                tone: severity === "HIGH" ? "cyan" : "emerald",
                reason: "Portfolio stabilization sleeve"
              },
              {
                source: "Bonds",
                target: "Precious Metals",
                pressure: manualFundingRequired ? "Manual funding" : "Operational",
                tone: manualFundingRequired ? "amber" : "emerald",
                reason: "Macro hedge coordination"
              },
              {
                source: "Precious Metals",
                target: "US Options",
                pressure: severity === "HIGH" ? "Hedge overlay" : "Standby",
                tone: severity === "HIGH" ? "amber" : "cyan",
                reason: "Systemic hedge and volatility overlay"
              },
              {
                source: "US Options",
                target: "Portfolio Hedge",
                pressure: executionPlan?.blocked ? "Blocked" : "Shadow mode",
                tone: executionPlan?.blocked ? "red" : "violet",
                reason: "Options overlay remains governed"
              },
            ].map((flow) => (
              <div
                key={`${flow.source}-${flow.target}`}
                className={`rounded-xl border p-3 ${
                  flow.tone === "red"
                    ? "border-red-500/25 bg-red-500/[0.06]"
                    : flow.tone === "amber"
                    ? "border-amber-500/25 bg-amber-500/[0.05]"
                    : flow.tone === "cyan"
                    ? "border-cyan-500/20 bg-cyan-500/[0.04]"
                    : "border-emerald-500/20 bg-emerald-500/[0.04]"
                }`}
              >
                <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.12em] text-slate-500">
                  <span>{flow.source}</span>
                  <span>→</span>
                  <span>{flow.target}</span>
                </div>

                <div className={`mt-2 text-sm font-semibold ${
                  flow.tone === "red"
                    ? "text-red-300"
                    : flow.tone === "amber"
                    ? "text-amber-300"
                    : flow.tone === "cyan"
                    ? "text-cyan-300"
                    : "text-emerald-300"
                }`}>
                  {flow.pressure}
                </div>

                <div className="mt-2 text-[10px] text-slate-500">
                  {flow.reason}
                </div>
              </div>
            ))}
          </div>
        </div>

        <PremiumSectionHeader
          title="Execution & Explainability Layer"
          subtitle="Execution readiness, blockers, why-not / why-exit reasoning and decision trace"
          tone="violet"
          badges={["execution guard", "explainability", "simulated orders"]}
        />

        <div className="mb-3 grid grid-cols-[1fr_1fr] gap-2.5">
          <Box className="p-2.5">
            <Title>Portfolio Execution Readiness</Title>

            <div className="grid grid-cols-[1fr_0.8fr_1.2fr_0.7fr] gap-2">
              <Metric label="Mode" value={executionPlan?.execution_mode || actionPolicy || "—"} tone="amber" />
              <Metric label="Blocked" value={executionPlan?.blocked ? "YES" : "NO"} tone={executionPlan?.blocked ? "red" : "green"} />
              <Metric label="Plan ID" value={shortId(executionPlan?.plan_id)} tone="slate" />
              <Metric label="Portfolio Actions" value={Array.isArray(executionPlan?.actions) ? executionPlan.actions.length : 0} tone="blue" />
              <Metric label="Simulated Orders" value={executionOrders?.orders_count ?? 0} tone={(executionOrders?.orders_count ?? 0) > 0 ? "amber" : "slate"} />
            </div>

            <div className="mt-3 grid grid-cols-[1fr_1fr] gap-2">
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
                <div className="text-[9px] uppercase tracking-wider text-slate-500">Execution Policy</div>
                <div className="mt-1 truncate text-xs font-semibold text-amber-300">
                  {String(actionPolicy || "UNKNOWN").toUpperCase()}
                </div>
              </div>

              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
                <div className="text-[9px] uppercase tracking-wider text-slate-500">Safety State</div>
                <div className={`mt-1 text-xs font-semibold ${executionPlan?.blocked ? "text-red-400" : "text-emerald-400"}`}>
                  {executionPlan?.blocked ? "BLOCKED" : "READY / SIMULATED"}
                </div>
              </div>
            </div>

            {Array.isArray(executionPlan?.block_reasons) && executionPlan.block_reasons.length > 0 ? (
              <div className="mt-3 rounded-lg border border-red-500/20 bg-red-500/5 p-2.5 text-xs text-red-100">
                {executionPlan.block_reasons.join(" · ")}
              </div>
            ) : (
              <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs text-emerald-100">
                No execution blocker reported. Orders remain governed by simulated execution policy.
              </div>
            )}
          </Box>

          <Box className="p-2.5">
            <Title>Why Not / Why Exit</Title>
            <div className="mb-2 rounded-2xl border border-red-500/15 bg-red-500/[0.035] p-2.5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Risk Pressure Score
                </div>
                <div className={`mt-1 text-lg font-semibold whitespace-nowrap ${riskPressureClass}`}>
                  {riskPressureScore}/100
                </div>
              </div>

              <div className={`rounded-md border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] ${
                riskPressureLabel === "HIGH"
                  ? "border-red-500/30 bg-red-500/10 text-red-300"
                  : riskPressureLabel === "WATCH"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              }`}>
                {riskPressureLabel}
              </div>
            </div>

            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full ${riskPressureBar}`}
                style={{ width: `${riskPressureScore}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2">
              <Metric label="Symbols" value={explainabilitySummary?.total_symbols ?? 0} />
              <Metric label="Events" value={explainabilitySummary?.total_events ?? 0} />
              <Metric label="No Entry" value={explainabilitySummary?.entries_not_executed ?? 0} tone="amber" />
              <Metric label="Exits" value={explainabilitySummary?.exits_executed ?? 0} tone="blue" />
              <Metric label="No Exit" value={explainabilitySummary?.exits_not_executed ?? 0} />
            </div>

            <div className="mt-3 space-y-2 text-xs">
              {explainability.length > 0 ? explainability.slice(0, 4).map((e, idx) => (
                <div key={idx} className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-white">{e.symbol || "—"}</div>
                    <div className="text-sky-300">{e.decision || "UNKNOWN"}</div>
                  </div>
                  <div className="mt-1 text-slate-400">
                    {e.narrative?.decision?.reason || e.decision_class || "No narrative available."}
                  </div>
                </div>
              )) : (
                <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-2.5 text-slate-400">
                  No explainability data available.
                </div>
              )}
            </div>
          </Box>
        </div>

        <div className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/70 px-5 py-4 text-[10px] text-slate-600">
          Sources: {apiUrl("/api/portfolio-state")} · {apiUrl("/api/portfolio-target")} · {apiUrl("/api/rebalance-plan")} · {apiUrl("/api/funding-plan")} · {apiUrl("/governance/status")} · {apiUrl("/api/execution-plan")} · {apiUrl("/api/execution-orders")}
        </div>
        </div>
      </main>
    </div>
  );
}
