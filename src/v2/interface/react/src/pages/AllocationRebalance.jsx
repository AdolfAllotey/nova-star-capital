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

function Box({ children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20 hover:shadow-[0_0_40px_rgba(34,211,238,0.06)] ${className}`}>
      {children}
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
      <div className={`mt-1 truncate text-lg font-semibold ${tones[tone] || tones.white}`}>{value}</div>
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

function DriftBar({ value }) {
  const width = Math.max(0, Math.min(100, Math.abs(num(value)) * 100));
  const color = width >= 8 ? "bg-red-500" : width >= 3 ? "bg-amber-400" : "bg-emerald-400";

  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className={`h-1.5 rounded ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export default function AllocationRebalance() {
  const [portfolioState, setPortfolioState] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [rebalancePlan, setRebalancePlan] = useState(null);
  const [bridgeAudit, setBridgeAudit] = useState(null);
  const [alignmentAudit, setAlignmentAudit] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [stateRes, targetRes, rebalanceRes, bridgeRes, alignmentRes] = await Promise.all([
        fetchJson("/api/portfolio-state", { timeoutMs: 8000 }),
        fetchJson("/api/portfolio-target", { timeoutMs: 8000 }),
        fetchJson("/api/rebalance-plan", { timeoutMs: 8000 }),
        fetchJson("/api/execution-plan", { timeoutMs: 8000 }),
        fetchJson("/api/aggregator-audit", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      if (!stateRes?.ok || !targetRes?.ok || !rebalanceRes?.ok) {
        setErr("Unable to load allocation or rebalance data.");
      }

      setPortfolioState(stateRes?.ok ? stateRes.data : null);
      setPortfolioTarget(targetRes?.ok ? targetRes.data : null);
      setRebalancePlan(rebalanceRes?.ok ? rebalanceRes.data : null);
      setBridgeAudit(bridgeRes?.ok ? {
        status: bridgeRes.data?.blocked ? "blocked" : "audit_only",
        execution_allowed: bridgeRes.data?.blocked === false && bridgeRes.data?.execution_mode === "LIVE",
        writes_execution_plan: false,
        message: "Derived from /api/execution-plan until dedicated bridge endpoint is available."
      } : null);
      setAlignmentAudit(alignmentRes?.ok ? {
        status:
          alignmentRes.data?.status
          || alignmentRes.data?.result
          || alignmentRes.data?.verdict
          || alignmentRes.data?.alignment_status
          || "unavailable",
        warning: alignmentRes.data?.summary?.warnings_count > 0
          ? `${alignmentRes.data.summary.warnings_count} warning(s) detected by aggregator audit.`
          : "Derived from /api/aggregator-audit until dedicated alignment endpoint is available."
      } : null);
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
  const weights = pt?.final_brick_weights || {};
  const cashBuffer = num(pt?.cash_buffer);
  const regime = pt?.portfolio_regime || ps?.portfolio_regime || "UNKNOWN";
  const actions = Array.isArray(rebalancePlan?.actions) ? rebalancePlan.actions : [];

  const rows = useMemo(() => {
    const keys = Array.from(new Set([...Object.keys(weights), ...Object.keys(bricks)]));
    return keys.map((key) => {
      const b = bricks[key] || {};
      const target = num(weights[key] ?? b.target_weight_snapshot);
      const current = num(b.current_weight_estimate ?? b.target_weight_snapshot ?? target);
      const drift = current - target;
      const action = actions.find((a) => a.brick === key) || null;

      return {
        key,
        label: BRICK_LABELS[key] || key,
        target,
        current,
        drift,
        action,
        status: b.status || "UNKNOWN",
        origin: b.state_origin || "signal_derived",
      };
    }).sort((a, b) => Math.abs(b.drift) - Math.abs(a.drift));
  }, [weights, bricks, actions]);

  const proposed = actions.filter((a) => a.status === "proposed").length;
  const approved = actions.filter((a) => a.status === "approved").length;
  const deferred = actions.filter((a) => a.status === "deferred").length;
  const blocked = actions.filter((a) => a.status === "blocked").length;
  const reduceActions = actions.filter((a) => String(a.action || a.type || "").toUpperCase().includes("REDUCE")).length;
  const increaseActions = actions.filter((a) => String(a.action || a.type || "").toUpperCase().includes("INCREASE")).length;
  const maxDrift = rows.reduce((m, r) => Math.max(m, Math.abs(r.drift)), 0);
  const executionAllowed = bridgeAudit?.execution_allowed === true;
  const writesExecutionPlan = bridgeAudit?.writes_execution_plan === true;

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Allocation layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Allocation & Rebalance Command</h1>
            <p className="text-xs text-slate-400">
              Portfolio target, current state, drift intelligence, rebalance decisions and execution bridge supervision
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone="green">{String(regime).toUpperCase()}</StatusPill>
            <StatusPill tone={proposed > 0 ? "amber" : "slate"}>Proposed {proposed}</StatusPill>
            <StatusPill tone={executionAllowed ? "red" : "green"}>{executionAllowed ? "EXECUTION ALLOWED" : "SHADOW ONLY"}</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-7 gap-3">
          <Metric label="Cash Buffer" value={pct(cashBuffer)} tone="blue" />
          <Metric label="Max Drift" value={pct(maxDrift)} tone={maxDrift >= 0.08 ? "red" : maxDrift >= 0.03 ? "amber" : "green"} />
          <Metric label="Portfolio Actions" value={actions.length} tone="white" />
          <Metric label="Proposed" value={proposed} tone={proposed > 0 ? "amber" : "slate"} />
          <Metric label="Blocked" value={blocked} tone={blocked > 0 ? "red" : "slate"} />
          <Metric label="Reduce" value={reduceActions} tone={reduceActions > 0 ? "amber" : "slate"} />
          <Metric label="Increase" value={increaseActions} tone={increaseActions > 0 ? "blue" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Capital orchestration">Allocation Command Center</Title>
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Regime</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{String(regime).toUpperCase()}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Approved</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{approved}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Deferred</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{deferred}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Bridge Mode</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">
                  {writesExecutionPlan ? "WRITES PLAN" : "AUDIT ONLY"}
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Execution Bridge Supervision</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${executionAllowed ? "text-red-400" : "text-emerald-400"}`}>
                {executionAllowed ? "EXECUTION ENABLED" : "SHADOW / AUDIT"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Rebalance intentions are supervised against execution alignment. In PREPROD, the bridge must remain audit-only unless explicitly governed.
              </div>
            </div>
          </Box>
        </div>

        <Box className="mb-3 p-3">
          <Title right="Target vs state by sleeve">Allocation Drift Intelligence</Title>

          <div className="grid grid-cols-[1fr_70px_70px_130px_70px_110px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Brick</div>
            <div>Target</div>
            <div>Current</div>
            <div></div>
            <div>Drift</div>
            <div>Action</div>
            <div>Status</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.map((row) => {
              const driftTone = Math.abs(row.drift) >= 0.08 ? "text-red-400" : Math.abs(row.drift) >= 0.03 ? "text-amber-300" : "text-emerald-400";
              return (
                <div key={row.key} className="grid grid-cols-[1fr_70px_70px_130px_70px_110px_90px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-200">{row.label}</div>
                  <div className="text-slate-300">{pct(row.target)}</div>
                  <div className="text-slate-300">{pct(row.current)}</div>
                  <DriftBar value={row.drift} />
                  <div className={driftTone}>{(row.drift * 100).toFixed(1)}%</div>
                  <div className="truncate text-sky-300">{row.action?.action || row.action?.type || "HOLD"}</div>
                  <div className="truncate text-slate-500">{row.action?.status || row.status}</div>
                </div>
              );
            })}
          </div>
        </Box>

        <div className="mb-3 grid grid-cols-[1fr_1fr] gap-3">
          <Box className="p-3">
            <Title>Governed Rebalance Actions</Title>
            <div className="space-y-2">
              {actions.length === 0 ? (
                <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                  No rebalance action proposed.
                </div>
              ) : actions.map((a, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_100px_90px_80px] gap-2 rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2 text-xs">
                  <div className="truncate text-slate-200">{BRICK_LABELS[a.brick] || a.brick || "—"}</div>
                  <div className="text-sky-300">{a.action || a.type || "—"}</div>
                  <div className="text-slate-400">{a.status || "—"}</div>
                  <div className="text-right text-amber-300">{pct(a.approved_delta ?? a.delta ?? 0)}</div>
                </div>
              ))}
            </div>
          </Box>

          <Box className="p-3">
            <Title>Execution Alignment Audit</Title>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Bridge Status" value={bridgeAudit?.status || "UNKNOWN"} tone="blue" />
              <Metric label="Alignment" value={alignmentAudit?.status || "UNKNOWN"} tone="blue" />
              <Metric label="Execution Allowed" value={executionAllowed ? "YES" : "NO"} tone={executionAllowed ? "red" : "green"} />
              <Metric label="Writes Plan" value={writesExecutionPlan ? "YES" : "NO"} tone={writesExecutionPlan ? "red" : "green"} />
            </div>

            <div className="mt-3 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-300">
              {alignmentAudit?.warning || alignmentAudit?.message || "Execution alignment is monitored in audit-only mode."}
            </div>
          </Box>
        </div>

        <div className="mt-3 text-[10px] text-slate-600">
          Sources: {apiUrl("/api/portfolio-state")} · {apiUrl("/api/portfolio-target")} · {apiUrl("/api/rebalance-plan")}
        </div>
      </main>
    </div>
  );
}
