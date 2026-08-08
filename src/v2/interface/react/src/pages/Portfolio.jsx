import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import NscSidebar from "../components/layout/NscSidebar";
import WorldExposureMap from "../components/dashboard/WorldExposureMap";
import { fetchJson, apiUrl } from "../lib/apiClient";

const BRICK_LABELS = {
  crypto: "Crypto",
  equities_offensive: "Offensive Equities",
  equities_defensive: "Defensive Equities",
  bonds: "Bonds",
  precious_metals: "Precious Metals",
  long_term: "Long Term",
  options_us: "Options US · Simulated",
  options_v2_shadow: "Options Shadow",
};

const BRICK_ROUTES = {
  crypto: "/bricks/crypto",
  equities_offensive: "/bricks/offensive",
  equities_defensive: "/bricks/defensive",
  bonds: "/bricks/bonds",
  precious_metals: "/bricks/precious-metals",
  long_term: "/bricks/lt",
  options_us: "/bricks/options",
  options_v2_shadow: "/bricks/options",
};

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function pct(v) {
  return `${(num(v) * 100).toFixed(1)}%`;
}

function eur(v) {
  return `${num(v).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
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
    violet: "border-violet-400/20 bg-violet-400/10 text-violet-300",
    red: "border-red-400/20 bg-red-400/10 text-red-300",
  };

  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    violet: "bg-violet-400",
    red: "bg-red-400",
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
    violet: "border-violet-400/10 from-[#080d18] via-[#101426] to-[#080d18] text-violet-100",
    sky: "border-sky-400/10 from-[#071018] via-[#0a1724] to-[#071018] text-sky-100",
  };

  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    violet: "bg-violet-400",
    sky: "bg-sky-400",
  };

  return (
    <div className={`mb-3 rounded-2xl border bg-gradient-to-r px-4 py-3 shadow-[0_0_50px_rgba(34,211,238,0.05)] ${toneMap[tone] || toneMap.cyan}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full animate-pulse ${dotMap[tone] || dotMap.cyan}`}></div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em]">
              {title}
            </div>
          </div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            {subtitle}
          </div>
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
      <h3 className="text-[13px] font-semibold uppercase tracking-[0.14em] text-slate-100">{children}</h3>
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
    <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] px-3 py-2 transition-all duration-300 hover:border-cyan-500/20 hover:bg-[#101927] hover:shadow-[0_0_20px_rgba(34,211,238,0.04)]">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${tones[tone] || tones.white}`}>{value}</div>
    </div>
  );
}


function confidenceTone(v) {
  const n = num(v);
  if (n >= 0.85) return "text-emerald-400";
  if (n >= 0.7) return "text-cyan-300";
  if (n >= 0.4) return "text-amber-300";
  return "text-slate-500";
}

function gapTone(v) {
  const n = num(v);
  if (Math.abs(n) < 0.001) return "text-slate-300";
  if (n > 0) return "text-cyan-300";
  return "text-amber-300";
}

function AllocationBar({ value }) {
  const width = Math.max(0, Math.min(100, num(value) * 100));
  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className="h-1.5 rounded bg-blue-500" style={{ width: `${width}%` }} />
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

function pickPositions(data) {
  if (Array.isArray(data?.positions)) return data.positions;
  if (Array.isArray(data?.data?.positions)) return data.data.positions;
  return [];
}

function pickSymbol(p) {
  return p?.symbol || p?.token || p?.asset || p?.id || "—";
}

function pickPnl(p) {
  return num(p?.pnl ?? p?.pnl_eur ?? p?.unrealized_pnl ?? 0);
}

function pickValue(p) {
  return num(p?.value_eur ?? p?.notional_eur ?? p?.position_value_eur ?? 0);
}

export default function Portfolio() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [positions, setPositions] = useState([]);
  const [portfolioState, setPortfolioState] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [rebalancePlan, setRebalancePlan] = useState(null);
  const [fundingPlan, setFundingPlan] = useState(null);
  const [aggregatorAudit, setAggregatorAudit] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const [openRes, stateRes, targetRes, rebalanceRes, fundingRes, auditRes] = await Promise.all([
        fetchJson("/portfolio/open", { timeoutMs: 8000 }),
        fetchJson("/api/portfolio-state", { timeoutMs: 8000 }),
        fetchJson("/api/portfolio-target", { timeoutMs: 8000 }),
        fetchJson("/api/rebalance-plan", { timeoutMs: 8000 }),
        fetchJson("/api/funding-plan", { timeoutMs: 8000 }),
        fetchJson("/api/aggregator-audit", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      if (!stateRes?.ok || !targetRes?.ok) {
        setErr("Unable to load portfolio state or target.");
      }

      setPositions(openRes?.ok ? pickPositions(openRes.data) : []);
      setPortfolioState(stateRes?.ok ? stateRes.data : null);
      setPortfolioTarget(targetRes?.ok ? targetRes.data : null);
      setRebalancePlan(rebalanceRes?.ok ? rebalanceRes.data : null);
      setFundingPlan(fundingRes?.ok ? fundingRes.data : null);
      setAggregatorAudit(auditRes?.ok ? auditRes.data : null);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const stateBricks = portfolioState?.bricks || portfolioState?.data?.bricks || {};
  const finalWeights = portfolioTarget?.final_brick_weights || portfolioTarget?.data?.final_brick_weights || {};
  const confidence = portfolioTarget?.brick_confidence || portfolioTarget?.data?.brick_confidence || {};
  const regimes = portfolioTarget?.brick_regimes || portfolioTarget?.data?.brick_regimes || {};
  const cashBuffer = num(portfolioTarget?.cash_buffer ?? portfolioTarget?.data?.cash_buffer);
  const regime = portfolioTarget?.portfolio_regime || portfolioTarget?.data?.portfolio_regime || portfolioState?.portfolio_regime || "unknown";

  const allocationRows = useMemo(() => {
    const keys = Array.from(new Set([...Object.keys(finalWeights), ...Object.keys(stateBricks)]));
    return keys.map((key) => {
      const state = stateBricks[key] || {};
      const target = num(finalWeights[key] ?? state.target_weight_snapshot);
      const current = num(state.current_weight_estimate ?? state.target_weight_snapshot ?? target);
      const gap = current - target;

      return {
        key,
        label: BRICK_LABELS[key] || key,
        route: BRICK_ROUTES[key],
        target,
        current,
        gap,
        confidence: num(confidence[key] ?? state.confidence),
        regime: regimes[key] || state.regime || "—",
        origin: state.state_origin || "signal_derived",
        pool: state.funding_pool || "—",
      };
    });
  }, [finalWeights, stateBricks, confidence, regimes]);

  const actions = Array.isArray(rebalancePlan?.actions) ? rebalancePlan.actions : [];
  const approved = actions.filter((a) => a.status === "approved").length;
  const deferred = actions.filter((a) => a.status === "deferred").length;
  const manualTransfers = fundingPlan?.requires_manual_transfer_between_pools ? "MANUAL" : "NONE";
  const totalTarget = allocationRows.reduce((s, r) => s + r.target, 0);
  const totalCurrent = allocationRows.reduce((s, r) => s + r.current, 0);

  const positionStats = useMemo(() => {
    const pnl = positions.reduce((s, p) => s + pickPnl(p), 0);
    const exposure = positions.reduce((s, p) => s + pickValue(p), 0);
    return { count: positions.length, pnl, exposure };
  }, [positions]);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Portfolio layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Portfolio</h1>
            <p className="text-xs text-slate-400">
              Capital allocation, target/state alignment, funding pools and geographic exposure
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone="green">{String(regime).toUpperCase()}</StatusPill>
            <StatusPill tone={approved > 0 ? "amber" : "slate"}>Approved {approved}</StatusPill>
            <StatusPill tone={deferred > 0 ? "amber" : "slate"}>Deferred {deferred}</StatusPill>
            <StatusPill tone={manualTransfers === "MANUAL" ? "amber" : "green"}>Transfers {manualTransfers}</StatusPill>
          </div>
        </div>

        <PremiumSectionHeader
          title="Portfolio Command Layer"
          subtitle="Target/state alignment · funding pools · capital drift · geographic exposure"
          tone="cyan"
          badges={[
            "UI v6.0.0 standard",
            "Portfolio synced",
            "Allocator watch",
            manualTransfers === "MANUAL" ? "Manual transfer" : "Transfers clear"
          ]}
        />

        <div className="mb-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-r from-[#060b12] via-[#08111b] to-[#060b12] px-4 py-3 shadow-[0_0_60px_rgba(34,211,238,0.05)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-100">
                Live Portfolio Telemetry
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.14em]">
              <LiveIndicator label="PORTFOLIO LIVE" tone="cyan" />
              <LiveIndicator label={String(regime).toUpperCase()} tone="emerald" />
              <LiveIndicator label={`APPROVED ${approved}`} tone={approved > 0 ? "amber" : "emerald"} />
              <LiveIndicator label={`DEFERRED ${deferred}`} tone={deferred > 0 ? "amber" : "emerald"} />
              <LiveIndicator label={`TRANSFERS ${manualTransfers}`} tone={manualTransfers === "MANUAL" ? "amber" : "emerald"} />
            </div>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Target Deployed" value={pct(totalTarget)} tone="blue" />
          <Metric label="Current Exposure" value={pct(totalCurrent)} tone="white" />
          <Metric label="Cash Buffer" value={pct(cashBuffer)} tone="blue" />
          <Metric label="Open Positions" value={positionStats.count} tone="white" />
          <Metric label="Open PnL" value={eur(positionStats.pnl)} tone={positionStats.pnl >= 0 ? "green" : "red"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.45fr_1fr] gap-3">
          <Box className="p-3 border border-violet-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(139,92,246,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Portfolio Brain</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">
                  Allocation intelligence and policy context
                </div>
              </div>
              <LiveIndicator label={loading ? "LOADING" : "LIVE"} tone="violet" />
            </div>
            <div className="grid grid-cols-[1.1fr_1fr_1fr] gap-4">
              <div className="rounded-2xl border border-emerald-400/10 bg-emerald-400/5 p-4 shadow-[0_0_24px_rgba(16,185,129,0.04)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">
                  Market Reading
                </div>
                <div className="mt-2 text-2xl font-semibold text-emerald-400">{String(regime).toUpperCase()}</div>
                <div className="mt-3 text-sm leading-5 text-slate-300">
                  Portfolio allocation is governed by market regime, confidence scoring,
                  funding constraints and policy-layer controls.
                </div>
              </div>

              <div className="rounded-2xl border border-cyan-400/10 bg-cyan-400/5 p-4 shadow-[0_0_24px_rgba(34,211,238,0.04)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">
                  Capital Decision
                </div>
                <div className="mt-2 text-xl font-semibold text-sky-300">Deploy selectively</div>
                <div className="mt-3 text-sm leading-5 text-slate-300">
                  Capital deployment remains selective while defensive and hedge sleeves
                  adapt dynamically to regime transitions.
                </div>
              </div>

              <div className="rounded-2xl border border-amber-400/10 bg-amber-400/5 p-4 shadow-[0_0_24px_rgba(251,191,36,0.04)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">
                  Audit Status
                </div>
                <div className={`mt-2 text-xl font-semibold ${
                  aggregatorAudit?.status === "OK"
                    ? "text-emerald-400"
                    : aggregatorAudit?.status === "WARNING"
                      ? "text-amber-300"
                      : "text-red-400"
                }`}>
                  {aggregatorAudit?.status || "UNKNOWN"}
                </div>
                <div className="mt-3 text-sm leading-5 text-slate-300">
                  Anomalies {aggregatorAudit?.summary?.anomalies_count ?? 0}
                  · Warnings {aggregatorAudit?.summary?.warnings_count ?? 0}
                  · Drift monitored
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-3 border border-cyan-400/10 bg-gradient-to-b from-[#0b1722] to-[#09111a] shadow-[0_0_40px_rgba(34,211,238,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Funding Pools</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">
                  Treasury pools and available capital
                </div>
              </div>
              <LiveIndicator label="POOLS" tone="cyan" />
            </div>
            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-[1fr_70px_70px_40px] border-b border-[#1f2a37] pb-1 text-[9px] uppercase tracking-wide text-slate-500">
                <div>Pool</div>
                <div className="text-right">Target</div>
                <div className="text-right">Available</div>
                <div className="text-right">Util.</div>
              </div>

              {(() => {
                const poolsObj =
                  fundingPlan?.pools ||
                  fundingPlan?.funding_pools ||
                  portfolioState?.funding_pools ||
                  portfolioState?.data?.funding_pools ||
                  {};

                const entries = Object.entries(poolsObj);

                if (entries.length === 0) {
                  return (
                    <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-slate-400">
                      No funding pool data available yet.
                    </div>
                  );
                }

                const totalTarget = entries.reduce(
                  (s, [, pool]) => s + num(pool?.target ?? pool?.target_amount_eur ?? 0),
                  0
                );

                return (
                  <>
                    {entries.map(([key, pool]) => (
                      <div key={key} className="grid grid-cols-[1fr_70px_70px_40px] border-b border-[#172231] py-2 last:border-b-0">
                        <div className="flex items-center gap-2 truncate text-slate-200">
                          <span className={`h-2 w-2 rounded-full ${
                            String(key).includes("crypto")
                              ? "bg-cyan-400"
                              : "bg-emerald-400"
                          }`} />
                          {key.replaceAll("_", " ")}
                        </div>
                        <div className="text-right text-slate-300">
                          {eur(pool?.target ?? pool?.target_amount_eur ?? 0)}
                        </div>
                        <div className="text-right text-emerald-400">
                          {eur(pool?.available ?? pool?.available_eur ?? pool?.target_amount_eur ?? 0)}
                        </div>
                        <div className="text-right text-slate-400">
                          {pct(pool?.utilization ?? pool?.target_weight_sum ?? 0)}
                        </div>
                      </div>
                    ))}

                    <div className="grid grid-cols-[1fr_70px_70px_40px] border-t border-[#1f2a37] pt-2 text-[10px] font-semibold">
                      <div className="text-white">TOTAL</div>
                      <div className="text-right text-sky-300">{eur(totalTarget)}</div>
                      <div className="text-right text-sky-300">{eur(totalTarget)}</div>
                      <div className="text-right text-sky-300">—</div>
                    </div>
                  </>
                );
              })()}
            </div>
          </Box>
        </div>

        <PremiumSectionHeader
          title="Allocation Alignment Layer"
          subtitle="Portfolio target · current exposure · confidence · state origin"
          tone="sky"
          badges={[
            "Target synced",
            "State monitored",
            "Drift visible"
          ]}
        />

        <div className="mb-3 grid grid-cols-1 gap-3">
          <Box className="p-3 border border-sky-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(56,189,248,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Target vs State</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-sky-300/70">
                  Allocation drift and confidence supervision
                </div>
              </div>
              <LiveIndicator label="ALIGNMENT" tone="cyan" />
            </div>
            <div className="grid grid-cols-[1fr_60px_60px_110px_60px_60px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
              <div>Brick</div>
              <div>Target</div>
              <div>Current</div>
              <div></div>
              <div>Gap</div>
              <div>Confidence</div>
              <div>Origin</div>
            </div>

            <div className="space-y-2 pt-2">
              {allocationRows.map((row) => {
                const gapClass = gapTone(row.gap);
                const confClass = confidenceTone(row.confidence);
                const name = row.route ? (
                  <Link to={row.route} className="text-slate-200 hover:text-sky-300">
                    {row.label}
                  </Link>
                ) : (
                  <span className="text-slate-200">{row.label}</span>
                );

                return (
                  <div key={row.key} className="grid grid-cols-[1fr_60px_60px_110px_60px_60px_90px] items-center gap-2 text-xs">
                    <div className="truncate">{name}</div>
                    <div className="text-slate-300">{pct(row.target)}</div>
                    <div className="text-slate-300">{pct(row.current)}</div>
                    <AllocationBar value={row.current} />
                    <div className={gapClass}>{`${(row.gap * 100).toFixed(1)}%`}</div>
                    <div className={confClass}>
                      <div className="flex items-center gap-2">
                        <span>{pct(row.confidence)}</span>
                        <div className="h-1.5 w-10 rounded bg-[#1a2532]">
                          <div
                            className="h-1.5 rounded bg-current"
                            style={{ width: `${Math.max(0, Math.min(100, row.confidence * 100))}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="truncate text-slate-500">{row.origin}</div>
                  </div>
                );
              })}
            </div>
          </Box>

          <Box className="min-h-[620px] overflow-hidden p-3 border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(16,185,129,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Geographic Exposure</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">
                  Regional allocation and exposure map
                </div>
              </div>
              <LiveIndicator label="GEO" tone="emerald" />
            </div>
            <div className="[&>div]:border-0 [&>div]:bg-transparent [&>div]:p-0">
              <WorldExposureMap portfolioTarget={portfolioTarget} />
            </div>
          </Box>
        </div>

        <PremiumSectionHeader
          title="Execution Preparation Layer"
          subtitle="Rebalance intent · open positions · simulated execution readiness"
          tone="amber"
          badges={[
            "Rebalance monitored",
            "Positions synced",
            "Execution governed"
          ]}
        />

        <div className="mb-3 grid grid-cols-[1fr_1fr] gap-3">
          <Box className="p-3 border border-amber-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(251,191,36,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Rebalance Plan</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">
                  Proposed allocation actions and governance status
                </div>
              </div>
              <LiveIndicator label="REBALANCE" tone="amber" />
            </div>
            <div className="space-y-2 text-xs">
              {actions.length > 0 ? (
                actions.slice(0, 8).map((a, idx) => (
                  <div key={idx} className="grid grid-cols-[1fr_90px_80px_80px] border-b border-[#172231] py-2 last:border-b-0">
                    <div className="truncate text-slate-300">{BRICK_LABELS[a.brick] || a.brick || "—"}</div>
                    <div className="text-slate-300">{a.action || a.type || "—"}</div>
                    <div className="text-slate-400">{a.status || "—"}</div>
                    <div className="text-right text-sky-300">{pct(a.approved_delta ?? a.delta ?? 0)}</div>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-slate-400">
                  No rebalance action proposed.
                </div>
              )}
            </div>
          </Box>

          <Box className="p-3 border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(16,185,129,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Open Positions</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">
                  Position exposure, PnL and execution mode
                </div>
              </div>
              <LiveIndicator label="POSITIONS" tone="emerald" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Positions" value={positionStats.count} />
              <Metric label="Exposure" value={eur(positionStats.exposure)} tone="blue" />
              <Metric label="PnL" value={eur(positionStats.pnl)} tone={positionStats.pnl >= 0 ? "green" : "red"} />
            </div>

            <div className="mt-3 space-y-2 text-xs">
              {positions.length > 0 ? (
                positions.slice(0, 6).map((p, idx) => {
                  const pnl = pickPnl(p);
                  return (
                    <div key={idx} className="grid grid-cols-[1fr_90px_70px_70px_80px] items-center border-b border-[#172231] py-2 last:border-b-0">
                      <div className="truncate text-slate-200">{String(pickSymbol(p)).toUpperCase()}</div>
                      <div className="text-right">
                        <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                          /SIMULATED/i.test(String(p?.execution_mode || p?.action || ""))
                            ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        }`}>
                          {p?.execution_mode || p?.action || p?.action_policy || p?.mode || "UNAVAILABLE"}
                        </span>
                      </div>
                      <div className="text-right text-slate-400">{p?.closed ? "CLOSED" : "OPEN"}</div>
                      <div className="text-right text-slate-300">{eur(pickValue(p))}</div>
                      <div className={`text-right ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>{eur(pnl)}</div>
                    </div>
                  );
                })
              ) : (
                <div className="mt-3 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-slate-400">
                  No open position.
                </div>
              )}
            </div>
          </Box>
        </div>

        <div className="text-[10px] text-slate-600">
          Sources: {apiUrl("/api/portfolio-state")} · {apiUrl("/api/portfolio-target")} · {apiUrl("/api/rebalance-plan")} · {apiUrl("/api/funding-plan")}
        </div>
      </main>
    </div>
  );
}
