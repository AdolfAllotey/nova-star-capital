import { buildApiUrl as apiUrl } from "../lib/apiBase";
import React, { useEffect, useState } from "react";


import { Link, useLocation } from "react-router-dom";
import {
  Home, Gauge, ShieldCheck, Wallet, ServerCog, Activity,
  AlertTriangle, CircleCheck, Briefcase, Layers, Brain
} from "lucide-react";
import { formatMode, formatRegime, formatPolicy, formatStatus, humanizeLabel } from "../system/systemLabels";
import { classifyDrift, driftToneClasses } from "../system/driftIntelligence";

function eur(v) {
  const n = Number(v || 0);
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
}

function pct(v) {
  const n = Number(v || 0);
  return `${(n * 100).toFixed(1)}%`;
}

function getDriftIntelligence(row = {}, governance = {}) {
  const target =
    row.target ??
    row.target_weight ??
    row.targetWeight ??
    row.allocation_target ??
    0;

  const current =
    row.current ??
    row.current_weight ??
    row.currentWeight ??
    row.live_weight ??
    row.allocation_current ??
    0;

  const drift =
    row.drift ??
    row.allocation_drift ??
    Number(current || 0) - Number(target || 0);

  return classifyDrift({
    drift,
    target,
    current,
    policy: governance?.action_policy || governance?.policy || "",
    mode: row.mode || row.execution_mode || "",
    reason: row.reason || row.status_reason || row.explanation || "",
  });
}

function DriftBadge({ row, governance }) {
  const drift = getDriftIntelligence(row, governance);
  const classes = driftToneClasses(drift.tone);

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${classes}`} title={drift.description}>
      <span>{drift.label}</span>
      <span className="opacity-70">{drift.severity}/100</span>
    </div>
  );
}


function Box({ children, className = "" }) {
  return <div className={`rounded-xl border border-[#1f2a37] bg-[#09111a]/95 transition-all duration-300 hover:border-cyan-500/25 hover:shadow-[0_0_32px_rgba(34,211,238,0.08)] ${className}`}>{children}</div>;
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

function CompactKpi({ title, label, value, tone = "blue", children }) {
  const toneMap = {
    green: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    red: "border-red-400/25 bg-red-400/10 text-red-300",
    amber: "border-amber-400/25 bg-amber-400/10 text-amber-300",
    blue: "border-sky-400/25 bg-sky-400/10 text-sky-300",
    slate: "border-slate-600/40 bg-slate-800/40 text-slate-200",
  };

  return (
    <Box className="p-2 min-h-[108px]">
      <div className="text-[9px] uppercase tracking-[0.18em] text-slate-500">{title}</div>
      <div className={`mt-1.5 rounded-lg border px-2 py-1 ${toneMap[tone] || toneMap.blue}`}>
        <div className="text-[8px] uppercase tracking-[0.14em] opacity-70">{label}</div>
        <div className="mt-0.5 truncate text-[13px] font-semibold">{value}</div>
      </div>
      <div className="mt-1 grid gap-0.5 text-[10px] leading-snug text-slate-400">
        {children}
      </div>
    </Box>
  );
}

function confidenceTone(v) {
  const n = Number(v || 0);
  if (n >= 0.8) return "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]";
  if (n >= 0.6) return "text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]";
  if (n >= 0.4) return "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]";
  return "text-red-400";
}

function gapTone(v) {
  const n = Number(v || 0);
  if (Math.abs(n) < 0.0001) return "text-slate-300";
  if (n > 0) return "text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]";
  return "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]";
}


function getMarketSessionState() {
  const now = new Date();

  const utc = now.toLocaleTimeString("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const paris = now.toLocaleTimeString("en-GB", {
    timeZone: "Europe/Paris",
    hour: "2-digit",
    minute: "2-digit",
  });

  const ny = now.toLocaleTimeString("en-GB", {
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
  });

  const tokyo = now.toLocaleTimeString("en-GB", {
    timeZone: "Asia/Tokyo",
    hour: "2-digit",
    minute: "2-digit",
  });

  const nyHour = Number(
    now.toLocaleString("en-US", {
      timeZone: "America/New_York",
      hour: "2-digit",
      hour12: false,
    })
  );

  const nyMinute = Number(
    now.toLocaleString("en-US", {
      timeZone: "America/New_York",
      minute: "2-digit",
    })
  );

  const nyMinutes = nyHour * 60 + nyMinute;
  const usOpen = 9 * 60 + 30;
  const usClose = 16 * 60;

  const usSession =
    nyMinutes >= usOpen && nyMinutes < usClose
      ? "US Market Open"
      : nyMinutes < usOpen
        ? "Pre-Market"
        : "After-Hours";

  const cryptoIntensity =
    nyMinutes >= usOpen && nyMinutes < usClose
      ? "High"
      : nyMinutes >= 7 * 60 && nyMinutes < 22 * 60
        ? "Moderate"
        : "Low";

  return {
    utc,
    paris,
    ny,
    tokyo,
    usSession,
    cryptoIntensity,
  };
}

function timeAgoLabel(value) {
  if (!value) return "Unknown";

  const ts = new Date(value).getTime();
  if (!Number.isFinite(ts)) return "Unknown";

  const diffSeconds = Math.max(0, Math.floor((Date.now() - ts) / 1000));

  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;

  return `${Math.floor(diffSeconds / 86400)}d ago`;
}

function TelemetryMetric({ label, value, status = "ok" }) {
  const statusClass =
    status === "critical"
      ? "text-red-400 border-red-500/30 bg-red-500/10"
      : status === "watch"
        ? "text-cyan-300 border-cyan-500/30 bg-cyan-500/10"
        : status === "caution"
          ? "text-amber-300 border-amber-500/30 bg-amber-500/10"
          : "text-emerald-300 border-emerald-500/30 bg-emerald-500/10";

  return (
    <div className={`rounded-xl border px-3 py-2 transition-all duration-300 hover:scale-[1.015] hover:shadow-[0_0_18px_rgba(34,211,238,0.10)] ${statusClass}`}>
      <div className="text-[9px] uppercase tracking-widest opacity-70">{label}</div>
      <div className="mt-1 text-[13px] font-semibold">{value}</div>
    </div>
  );
}

function Heartbeat({ status = "ok" }) {
  const dotClass =
    status === "critical"
      ? "bg-red-400 shadow signals-[0_0_12px_rgba(248,113,113,0.8)]"
      : status === "caution"
        ? "bg-amber-300 shadow signals-[0_0_12px_rgba(251,191,36,0.75)]"
        : "bg-emerald-400 shadow signals-[0_0_12px_rgba(52,211,153,0.75)]";

  return (
    <div className="flex items-center gap-2 rounded-xl border border-[#1f2a37] bg-[#0d1520] px-3 py-2">
      <span className={`h-2.5 w-2.5 animate-pulse rounded-full ${dotClass}`} />
      <div>
        <div className="text-[9px] uppercase tracking-widest text-slate-500">System Heartbeat</div>
        <div className="text-[13px] font-semibold text-white">{status === "critical" ? "Degraded" : status === "caution" ? "Under Watch" : "Live"}</div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "white" }) {
  const tones = {
    white: "text-white",
    green: "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]",
    amber: "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]",
    red: "text-red-400",
    blue: "text-sky-300",
  };
  return (
    <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${tones[tone] || tones.white}`}>{value}</div>
    </div>
  );
}

function Title({ children }) {
  return <h3 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-white">{children}</h3>;
}

function SidebarItem({ icon: Icon, label, path }) {
  const location = useLocation();
  const active = path && location.pathname === path;

  const content = (
    <div className={`flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-xs transition-all ${
      active ? "bg-[#16213a] text-white shadow signals-[inset_3px_0_0_#3b82f6]" : "text-slate-300 hover:bg-[#111827]"
    }`}>
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </div>
  );

  return path ? <Link to={path}>{content}</Link> : content;
}

function SidebarSection({ title, items }) {
  return (
    <div className="mt-5">
      <div className="mb-2 px-3 text-[9px] uppercase tracking-widest text-slate-500">{title}</div>
      <div className="space-y-1">{items}</div>
    </div>
  );
}


function normalizeBrickKey(key) {
  const k = String(key || "").toLowerCase();

  if (k === "defensive") return "equities_defensive";
  if (k === "metals") return "precious_metals";
  if (k === "options_us") return "options_us";

  return k;
}

function getBrickConfidence(key, confidence, pt, bricks) {
  const k = normalizeBrickKey(key);

  return Number(
    confidence?.[k] ??
    pt?.brick_confidence?.[k] ??
    bricks?.[k]?.confidence ??
    0
  );
}


const humanBrickName = (key) => {
  const map = {
    crypto: "Crypto",
    equities_offensive: "Offensive Equities",
    equities_defensive: "Defensive Equities",
    defensive: "Defensive Equities",
    bonds: "Bonds",
    precious_metals: "Precious Metals",
    metals: "Precious Metals",
    options_v2_shadow: "Options V2 · Shadow",
    options_us: "Options US · Simulated",
    long_term: "Long Term",
  };

  return map[key] || key;
};

const modeBadgeClass = (mode) => {
  const m = String(mode || "").toUpperCase();

  if (m.includes("SHADOW")) {
    return "border-violet-500/30 bg-violet-500/10 text-violet-300";
  }

  if (m.includes("PATRIMONIAL")) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]";
  }

  if (m.includes("SIMULATED_ONLY")) {
    return "border-amber-400/30 bg-amber-400/10 text-amber-200";
  }

  if (m.includes("SIMULATED_EXECUTION")) {
    return "border-cyan-500/30 bg-cyan-500/10 text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]";
  }

  return "border-[#1f2a37] bg-[#0d1520] text-slate-300";
};

function getReason(key, target, raw, regime) {
  const r = String(regime || "").toLowerCase();
  if (target > 0) {
    if (r === "risk_on") return "Active: offensive allocation enabled";
    if (r === "risk_off") return "Active: defensive capital preservation";
    return "Active allocation";
  }
  if (key === "equities_defensive") return "Inactive: risk_on favors offensive allocation";
  if (key === "bonds") return "Inactive: macro defensive sleeve dormant";
  if (key === "precious_metals") return "Inactive: no systemic stress detected";
  if (key === "options_v2_shadow") return "Shadow mode: observed but not deployed";
  if (raw > 0) return "Capped to 0 by current regime";
  return "Inactive in current regime";
}


async function fetchControlRoomSource(path) {
  const url = path.startsWith("/api/")
    ? apiUrl(path)
    : apiUrl(path);

  try {
    const response = await fetch(url, {
      credentials: "include",
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error: `HTTP ${response.status}`,
      };
    }

    return {
      ok: true,
      status: response.status,
      data: await response.json(),
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: String(error?.message || error || "fetch error"),
    };
  }
}

export default function ControlRoom() {
  const [dashboard, setDashboard] = useState(null);
  const [portfolioState, setPortfolioState] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [longRunDailyReport, setLongRunDailyReport] = useState(null);
  const [productionReadiness, setProductionReadiness] = useState(null);
  const [weeklyReview, setWeeklyReview] = useState(null);
  const [committeeReview, setCommitteeReview] = useState(null);
  const [dynamicMetricsAudit, setDynamicMetricsAudit] = useState(null);
  const [executionOrders, setExecutionOrders] = useState(null);
  const [activityDashboard, setActivityDashboard] = useState(null);
  const [sourceState, setSourceState] = useState({
    loading: true,
    online: false,
    available: 0,
    total: 10,
    failures: [],
    lastRefresh: null,
  });

  useEffect(() => {
    async function load() {
      const endpoints = [
        ["dashboard", "/dashboard/v3"],
        ["portfolioState", "/api/portfolio-state"],
        ["portfolioTarget", "/api/portfolio-target"],
        ["longRunDailyReport", "/api/portfolio/global-preprod-long-run-daily-report"],
        ["productionReadiness", "/api/portfolio/global-preprod-production-readiness"],
        ["weeklyReview", "/api/portfolio/global-preprod-weekly-review"],
        ["committeeReview", "/api/portfolio/global-preprod-committee-review"],
        ["dynamicMetricsAudit", "/api/portfolio/global-dynamic-metrics-audit"],
        ["executionOrders", "/api/execution-orders"],
        ["activityDashboard", "/api/activity-dashboard"],
      ];

      setSourceState((previous) => ({
        ...previous,
        loading: true,
      }));

      const results = await Promise.all(
        endpoints.map(async ([name, endpoint]) => ({
          name,
          endpoint,
          result: await fetchControlRoomSource(endpoint),
        }))
      );

      const byName = Object.fromEntries(
        results.map((item) => [item.name, item.result])
      );

      setDashboard(byName.dashboard?.ok ? byName.dashboard.data : null);
      setPortfolioState(
        byName.portfolioState?.ok
          ? byName.portfolioState.data
          : null
      );
      setPortfolioTarget(
        byName.portfolioTarget?.ok
          ? byName.portfolioTarget.data
          : null
      );
      setLongRunDailyReport(
        byName.longRunDailyReport?.ok
          ? byName.longRunDailyReport.data
          : null
      );
      setProductionReadiness(
        byName.productionReadiness?.ok
          ? byName.productionReadiness.data
          : null
      );
      setWeeklyReview(
        byName.weeklyReview?.ok
          ? byName.weeklyReview.data
          : null
      );
      setCommitteeReview(
        byName.committeeReview?.ok
          ? byName.committeeReview.data
          : null
      );
      setDynamicMetricsAudit(
        byName.dynamicMetricsAudit?.ok
          ? byName.dynamicMetricsAudit.data
          : null
      );
      setExecutionOrders(
        byName.executionOrders?.ok
          ? byName.executionOrders.data
          : null
      );
      setActivityDashboard(
        byName.activityDashboard?.ok
          ? byName.activityDashboard.data
          : null
      );

      const failures = results
        .filter((item) => !item.result.ok)
        .map((item) => ({
          name: item.name,
          endpoint: item.endpoint,
          status: item.result.status,
          error: item.result.error,
        }));

      const available = results.length - failures.length;

      setSourceState({
        loading: false,
        online: available > 0,
        available,
        total: results.length,
        failures,
        lastRefresh: new Date().toISOString(),
      });
    }
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  
const global = dashboard?.global || {};
const strategies = Array.isArray(dashboard?.strategies) ? dashboard.strategies : [];

const pt = portfolioTarget && Object.keys(portfolioTarget?.data || {}).length ? portfolioTarget.data : (portfolioTarget || {});
const ps = portfolioState && Object.keys(portfolioState?.data || {}).length ? portfolioState.data : (portfolioState || {});

const pamSummary = activityDashboard?.summary || {};
const pamEngines = Array.isArray(activityDashboard?.engines) ? activityDashboard.engines : [];
const pamEngineById = Object.fromEntries(pamEngines.map(e => [e.id, e]));

function pamCapitalPct(id, fallback = 0) {
  const v = pamEngineById?.[id]?.capital_pct;
  return Number.isFinite(Number(v)) ? Number(v) / 100 : fallback;
}

function pamTargetPct(id, fallback = 0) {
  const v = pamEngineById?.[id]?.target_pct;
  return Number.isFinite(Number(v)) ? Number(v) / 100 : fallback;
}

function pamConfidencePct(id, fallback = 0) {
  const v = pamEngineById?.[id]?.confidence_pct;
  return Number.isFinite(Number(v)) ? Number(v) : fallback;
}

function pamOrdersCount(id, fallback = 0) {
  const v = pamEngineById?.[id]?.orders_count;
  return Number.isFinite(Number(v)) ? Number(v) : fallback;
}

function pamPositionsCount(id, fallback = 0) {
  const v = pamEngineById?.[id]?.positions_count;
  return Number.isFinite(Number(v)) ? Number(v) : fallback;
}

function pamCapitalGapPct(id, fallback = 0) {
  const v = pamEngineById?.[id]?.capital_gap_pct;
  return Number.isFinite(Number(v)) ? Number(v) : fallback;
}

const pamCapitalDeploymentPct = Number(pamSummary?.capital_deployment_pct ?? 0);
const pamGrossExposurePct = Number(pamSummary?.gross_exposure_pct ?? pamCapitalDeploymentPct);
const pamCashBufferPct = Math.max(0, 100 - pamCapitalDeploymentPct);


const bricks = ps?.bricks || {};
const weights = pt?.final_brick_weights || portfolioTarget?.final_brick_weights || portfolioTarget?.data?.final_brick_weights || {};
const rawWeights = pt?.raw_brick_weights || portfolioTarget?.raw_brick_weights || portfolioTarget?.data?.raw_brick_weights || {};
const confidence = pt?.brick_confidence || portfolioTarget?.brick_confidence || portfolioTarget?.data?.brick_confidence || {};

const regime =
  pt?.portfolio_regime ||
  ps?.portfolio_regime ||
  global.regime ||
  "unknown";

const riskFlags = Number(global.riskFlags || 0);
const hardBlock = global.governanceMode === "SIMULATED ONLY";
const actionPolicy =
  global.actionPolicy ||
  global.action_policy ||
  dashboard?.actionPolicy ||
  dashboard?.action_policy ||
  "UNAVAILABLE";

const orchestrationStatus = global.orchestrationStatus || "UNKNOWN";
const orchestrationReasons = Array.isArray(global.orchestrationReasons)
  ? global.orchestrationReasons
  : [];
const masterGuardrailStatus = global.masterGuardrailStatus || "UNKNOWN";
const masterStaleStatus = global.masterStaleStatus || "UNKNOWN";

const orchestrationTone =
  orchestrationStatus === "OK"
    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
    : orchestrationStatus === "WARNING"
      ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
      : "border-red-400/30 bg-red-400/10 text-red-300";

const globalAuditStatus = global.globalAuditStatus || "UNKNOWN";
const globalAuditAlertLevel = global.globalAuditAlertLevel || "UNKNOWN";
const globalAuditBlocking = Boolean(global.globalAuditBlocking);
const globalAuditSummary = global.globalAuditSummary || {};

const globalAuditTone =
  globalAuditStatus === "OK" && !globalAuditBlocking
    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
    : globalAuditAlertLevel === "WARNING"
      ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
      : "border-red-400/30 bg-red-400/10 text-red-300";

const supervisionGateOpen = Boolean(global.supervisionGateOpen);
const supervisionGateMode = global.supervisionGateMode || "UNKNOWN";
const supervisionGateActions = global.supervisionGateActions || {};

const allowRealExecution = Boolean(supervisionGateActions.allow_real_execution);
const allowSimulatedExecution = Boolean(supervisionGateActions.allow_simulated_execution);

const systemDecision = hardBlock
  ? "TRADING BLOCKED"
  : allowRealExecution && riskFlags === 0
    ? "LIVE TRADING ALLOWED"
    : allowSimulatedExecution
      ? "SIMULATION ALLOWED"
      : "RESTRICTED";

const systemDecisionTone = hardBlock
  ? "red"
  : allowRealExecution && riskFlags === 0
    ? "green"
    : allowSimulatedExecution
      ? "amber"
      : "amber";

const canTrade = allowRealExecution && !hardBlock && riskFlags === 0;

const supervisionGateTone =
  supervisionGateOpen && supervisionGateMode === "NORMAL"
    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
    : supervisionGateMode === "SAFE"
      ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
      : "border-red-400/30 bg-red-400/10 text-red-300";

const stressTests = global.globalPreprodStressTests || {};
const stressSummary = stressTests.summary || {};
const stressStatus = stressTests.status || "UNKNOWN";
const stressPassed = Number(stressSummary.passed || 0);
const stressTotal = Number(stressSummary.total_scenarios || 0);
const stressFailed = Number(stressSummary.failed || 0);

const preprodHistory = global.globalPreprodHistorySummary || {};
const preprodHistorySummary = preprodHistory.summary || {};
const preprodLastRun = preprodHistory.last_run || {};
const preprodTotalRuns = Number(preprodHistorySummary.total_runs || 0);
const preprodSuccessfulRuns = Number(preprodHistorySummary.successful_runs || 0);
const preprodFailedRuns = Number(preprodHistorySummary.failed_runs || 0);
const preprodDegradedRuns = Number(preprodHistorySummary.degraded_runs || 0);
const preprodLastRunOk =
  preprodLastRun.status === "ok" &&
  preprodLastRun.global_status === "OK" &&
  preprodLastRun.gate_mode === "NORMAL" &&
  Number(preprodLastRun.stress_failed || 0) === 0;
const preprodHistoryTone =
  preprodLastRunOk && preprodFailedRuns === 0 && preprodDegradedRuns === 0
    ? "green"
    : preprodLastRunOk && preprodFailedRuns > 0
      ? "amber"
      : "red";

const trendMonitor = global.globalPreprodTrendMonitor || {};
const trendMetrics = trendMonitor.metrics || {};
const trendStatus = trendMonitor.trend_status || "UNKNOWN";
const trendAlerts = trendMonitor.alerts || [];

const anomalyDetector = global.globalPreprodAnomalyDetector || {};
const anomalySummary = anomalyDetector.summary || {};
const anomalyStatus = anomalyDetector.anomaly_status || "UNKNOWN";
const anomalyTotal = Number(anomalySummary.total_anomalies || 0);
const anomalyCritical = Number(anomalySummary.critical || 0);
const anomalyWarning = Number(anomalySummary.warning || 0);

const longRunReadiness = global.globalPreprodLongRunReadiness || {};
const longRunSummary = longRunReadiness.summary || {};
const longRunDecision = longRunReadiness.decision || {};
const longRunStatus = longRunReadiness.readiness_status || "UNKNOWN";
const longRunPassed = Number(longRunSummary.passed || 0);
const longRunTotal = Number(longRunSummary.total_checks || 0);
const longRunFailed = Number(longRunSummary.failed || 0);

const longRunDailyHeadline = longRunDailyReport?.headline || {};
const longRunDailyKpis = longRunDailyReport?.kpis || {};
const longRunDailyDecision = longRunDailyReport?.decision || {};
const longRunProgress = longRunDailyReport?.progress || {};
const longRunActivePhase = longRunProgress?.active_phase || {};
const longRunPhases = Array.isArray(longRunProgress?.phases) ? longRunProgress.phases : [];
const longRunCanContinue =
  longRunDailyDecision?.continue_60d_global_preprod === true ||
  longRunDailyHeadline?.can_continue_long_run === true;
const longRunRealExecution = longRunDailyHeadline?.real_execution_authorized === true;
const longRunSimulatedExecution = longRunDailyHeadline?.simulated_execution_authorized === true;
const simulatedOrdersCount = Number(executionOrders?.orders_count ?? global?.ordersCount ?? 0);
const activeEntryOrders = Number(global?.activeEntryOrders ?? 0);
const exitOrders = Number(global?.exitOrders ?? 0);
const shadowSignals = Number(global?.shadowSignals ?? 0);
const blockedSimulatedOrdersCount = Number(executionOrders?.blocked_orders_count ?? 0);
const simulatedOrderSymbols = Array.isArray(executionOrders?.symbols) ? executionOrders.symbols : [];

const executionEngineStatus = hardBlock ? "BLOCKED" : allowSimulatedExecution ? "WATCH" : "OK";
const executionPlanStatus = blockedSimulatedOrdersCount > 0 ? "WATCH" : simulatedOrdersCount > 0 ? "OK" : "IDLE";
const ordersStatus = activeEntryOrders + exitOrders + shadowSignals > 0 ? "OK" : "IDLE";

const pipelineStatus = globalAuditStatus === "OK" && !globalAuditBlocking ? "PIPELINE OK" : "PIPELINE WATCH";
const kernelStatus = orchestrationStatus === "OK" ? "KERNEL OK" : "KERNEL WATCH";
const governanceStatusLabel = hardBlock ? "GOVERNANCE BLOCKED" : "GOVERNANCE OK";
const executionSafetyLabel = hardBlock ? "EXECUTION BLOCKED" : actionPolicy.includes("SIMULATED") ? "EXECUTION SAFE" : "EXECUTION LIVE";
const blockersLabel = globalAuditBlocking || hardBlock ? "BLOCKERS" : "NO BLOCKERS";
const auditStatusLabel = blockedSimulatedOrdersCount > 0 || globalAuditBlocking ? "AUDIT WATCH" : "AUDIT OK";

const longRunManualFunding = longRunDailyHeadline?.manual_funding_required === true;
const longRunDailyFailed = Number(longRunDailyKpis?.daily_checks_failed || 0);
const longRunBlocking = Number(longRunDailyKpis?.orchestration_blocking_checks || 0);
const longRunProgressPct = Number(longRunProgress?.progress_pct || 0);
const longRunCurrentDay = Number(longRunProgress?.current_day ?? 0);
const longRunTargetDays = Number(longRunProgress?.target_duration_days || 60);
const longRunRemainingDays = Math.max(0, longRunTargetDays - longRunCurrentDay);

const longRunStartedAt = longRunProgress?.started_at
  ? new Date(longRunProgress.started_at)
  : null;

const longRunEtaDate = longRunStartedAt
  ? new Date(longRunStartedAt.getTime() + (longRunTargetDays * 86400000))
  : null;

const longRunEta =
  longRunEtaDate
    ? longRunEtaDate.toLocaleDateString("en-GB")
    : "UNKNOWN";

const longRunHealthScore = Math.max(
  0,
  Math.min(
    100,
    100
      - (longRunBlocking * 15)
      - (longRunDailyFailed * 10)
      - (anomalyCritical * 8)
      - (trendAlerts.length * 3)
  )
);

const productionDecision = productionReadiness?.decision || "UNKNOWN";
const productionScore = Number(productionReadiness?.readiness_score || 0);
const productionRecommendation = productionReadiness?.recommendation || "Production readiness not available yet.";

const weeklySummary = weeklyReview?.summary || {};
const weeklyDecision = weeklyReview?.decision || {};
const weeklyInstitutional = weeklyReview?.institutional_review || {};
const weeklyHealth = Number(weeklySummary?.global_health_score || 0);
const weeklyStability = weeklySummary?.stability || "UNKNOWN";
const weeklyRecommendation = weeklyDecision?.recommendation || "UNKNOWN";

const committeeProgress = committeeReview?.progress || {};
const committeeStatuses = committeeReview?.committees || {};
const committeeTrajectory = committeeReview?.trajectory || {};
const committeeProjection = committeeTrajectory?.projection || "UNKNOWN";
const committeeConfidenceTrend = committeeTrajectory?.confidence_trend || "UNKNOWN";

const dynamicMetricsResults = Array.isArray(dynamicMetricsAudit?.results) ? dynamicMetricsAudit.results : [];
const dynamicMetricsStatus = dynamicMetricsAudit?.global_status || "UNKNOWN";
const dynamicMetricsOk = Number(dynamicMetricsAudit?.ok_metrics || 0);
const dynamicMetricsWarnings = Number(dynamicMetricsAudit?.warning_metrics || 0);
const dynamicMetricsFreshnessAvg = dynamicMetricsResults.length
  ? Math.round(dynamicMetricsResults.reduce((sum, r) => sum + Number(r.freshness_sec || 0), 0) / dynamicMetricsResults.length)
  : 0;

const longRunTimeline =
  longRunTargetDays <= 30
    ? [
        { day: 0, label: "Official RC2 launch" },
        { day: 7, label: "Week 1 stability review" },
        { day: 14, label: "Mid-cycle strategy & risk review" },
        { day: 21, label: "Performance & explainability review" },
        { day: 30, label: "RC2 final observation review" },
      ]
    : [
        { day: 1, label: "Runtime stability validation" },
        { day: 3, label: "API/UI consistency supervision" },
        { day: 7, label: "Governance drift review" },
        { day: 10, label: "Robustness checkpoint" },
        { day: 20, label: "Strategy quality review" },
        { day: 30, label: "Risk & governance audit" },
        { day: 40, label: "Funding & rebalance validation" },
        { day: 50, label: "Explainability review" },
        { day: 60, label: "Production readiness decision" },
      ];


const shadowSignals48h = global.globalPreprod48hShadowSupervisor || {};
const shadowSignalsProgress = shadowSignals48h.progress || {};
const shadowSignalsSummary = shadowSignals48h.summary || {};
const shadowSignalsDecision = shadowSignals48h.decision || {};
const shadowSignalsStatus = shadowSignals48h.shadow_status || "UNKNOWN";
const shadowSignalsProgressPct = Number(shadowSignalsProgress.progress_pct || 0);
const shadowSignalsPassed = Number(shadowSignalsSummary.passed || 0);
const shadowSignalsTotal = Number(shadowSignalsSummary.total_checks || 0);
const shadowSignalsFailed = Number(shadowSignalsSummary.failed || 0);


const allocatorDriftRows = (Object.keys(weights).length ? Object.keys(weights) : Object.keys(bricks)).map((key) => {

  const normalizedKey = String(key)
    .toLowerCase()
    .replace(/\s+/g, "_");

  const target = Number(
    weights?.[normalizedKey] ??
    pt?.final_brick_weights?.[normalizedKey] ??
    portfolioTarget?.final_brick_weights?.[normalizedKey] ??
    portfolioTarget?.data?.final_brick_weights?.[normalizedKey] ??
    weights?.[key] ??
    0
  );

  const current = Number(
    bricks?.[key]?.current_weight_estimate ??
    bricks?.[key]?.target_weight_snapshot ??
    target
  );

  const drift = current - target;
  const absDrift = Math.abs(drift);

  const status =
    absDrift >= 0.05 ? "REBALANCE" :
    absDrift >= 0.02 ? "WATCH" :
    "STABLE";

  const threshold = 0.02;

  return {
    key,
    target,
    current,
    drift,
    absDrift,
    threshold,
    status,
  };
});

const explainabilityMessages = [
  {
    level: regime === "risk_off" ? "WATCH" : "INFO",
    text:
      regime === "risk_on"
        ? "Risk-on regime keeps offensive and crypto allocation active."
        : regime === "risk_off"
          ? "Risk-off regime prioritizes capital preservation and defensive exposure."
          : "Neutral regime keeps allocation balanced and monitored."
  },

  {
    level: hardBlock ? "BLOCKED" : "INFO",
    text: hardBlock
      ? "Hard block is active: execution must remain blocked."
      : "No hard block detected by governance."
  },

  {
    level: actionPolicy.includes("SIMULATED") ? "WATCH" : "INFO",
    text: actionPolicy.includes("SIMULATED")
      ? `Execution remains constrained by ${actionPolicy} policy.`
      : `Execution policy currently reads ${actionPolicy}.`
  },

  {
    level: riskFlags > 0 ? "WATCH" : "INFO",
    text: riskFlags > 0
      ? `${riskFlags} soft governance constraint(s) active; system remains under watch.`
      : "No soft governance constraint detected."
  },

  {
    level:
      Number(
        pt?.cash_buffer ??
        portfolioTarget?.cash_buffer ??
        portfolioTarget?.data?.cash_buffer ??
        ps?.cash_buffer ??
        0
      ) > 0.1 ? "INFO" : "CAUTION",

    text:
      Number(
        pt?.cash_buffer ??
        portfolioTarget?.cash_buffer ??
        portfolioTarget?.data?.cash_buffer ??
        ps?.cash_buffer ??
        0
      ) > 0.1
        ? "Cash buffer remains above 10%, preserving funding flexibility."
        : "Cash buffer is below 10%; allocator should monitor liquidity pressure."
  },

  {
    level: "INFO",
    text: "Options shadow signals brick remains isolated from live execution flows."
  }
];


const marketSession = getMarketSessionState();

const telemetryGeneratedAt =
  dashboard?.generated_at ||
  dashboard?.timestamp ||
  dashboard?.updated_at ||
  global?.generated_at ||
  new Date().toISOString();

const telemetryStatus =
  hardBlock || riskFlags >= 3
    ? "critical"
    : riskFlags > 0 || actionPolicy.includes("SIMULATED")
      ? "watch"
      : "ok";

const signalFreshnessPct = Math.max(
  0,
  Math.min(
    100,
    Number(
      dashboard?.signal_freshness_pct ??
      global?.signal_freshness_pct ??
      94
    )
  )
);

const apiLatencyMs = Number(
  dashboard?.api_latency_ms ??
  global?.api_latency_ms ??
  42
);

const rebalanceReductions =
  Number(global.rebalanceReductions ?? global.rebalance_reductions ?? 0);

const globalConfidenceScore = Math.max(0, Math.min(100, Math.round(Number(global?.confidencePct ?? 0))));
const marketRegimeScore = globalConfidenceScore || (regime === "risk_on" ? 82 : regime === "risk_off" ? 38 : 55);
const governancePolicyScore = hardBlock ? 20 : actionPolicy.includes("SIMULATED") ? 72 : 88;
const riskFlagsScore = Math.max(20, Math.min(100, riskFlags > 0 ? 85 - riskFlags * 10 : 95));
const fundingConstraintScore = global?.masterFundingManualApprovalRequired ? 68 : 92;
const executionReadinessScore = hardBlock ? 20 : global?.globalAuditStatus === "OK" ? Math.max(80, globalConfidenceScore) : 65;
const metaScoreValue = Math.round((marketRegimeScore + governancePolicyScore + riskFlagsScore + executionReadinessScore) / 4);
const signalQualityScore = Math.round((globalConfidenceScore + riskFlagsScore) / 2);
const riskConsensusScore = riskFlagsScore;
const governanceConfidenceScore = governancePolicyScore;
const narrativeCoherenceScore = global?.orchestrationStatus === "OK" ? Math.max(80, globalConfidenceScore) : 65;

const liquidityPulseScore = 50;
const liquidityPulseState = "Neutral / stale";
const volatilityStateScore = 65;
const volatilityStateLabel = "Calm";
const correlationRegimeScore = 35;
const correlationRegimeLabel = "High corr";
const systemicStressScore = 70;
const systemicStressLabel = "Stress elevated";
const crossAssetFrictionScore = global?.masterFundingManualApprovalRequired ? 66 : 90;
const crossAssetFrictionLabel = global?.masterFundingManualApprovalRequired ? "Manual Funding" : "Clear";

const manualFundingRequired = Boolean(global?.masterFundingManualApprovalRequired);
const autoTransferAllowed = Boolean(global?.masterFundingAutoTransferAllowed);
const fundingLayerStatus = manualFundingRequired ? "WATCH" : "OK";
const fundingLayerMode = manualFundingRequired ? "MANUAL" : autoTransferAllowed ? "AUTO" : "CLEAR";
const fundingLayerSignal = manualFundingRequired
  ? "Cross-universe transfer requires manual approval"
  : autoTransferAllowed
    ? "Automatic transfer allowed"
    : "No funding constraint active";
const fundingEventMessage = manualFundingRequired
  ? "Manual inter-universe funding constraint enforced"
  : "Funding layer clear";
const fundingMonitorMessage = manualFundingRequired
  ? "Manual funding governance remains enforced: no automatic transfer between crypto venues and IBKR pool."
  : "Funding governance clear: no manual transfer required by current plan.";

const marketStabilityLabel = global?.globalAuditStatus === "OK" ? "Stable" : "Watch";
const marketStabilityTone = global?.globalAuditStatus === "OK" ? "emerald" : "amber";
const systemCoherenceLabel = global?.orchestrationStatus === "OK" ? "High" : "Watch";
const systemCoherenceScore = global?.orchestrationStatus === "OK" ? Math.max(80, globalConfidenceScore) : 60;
const systemCoherenceTone = global?.orchestrationStatus === "OK" ? "emerald" : "amber";


const totalTarget = Number(
  pt?.total_final_weight ??
  portfolioTarget?.total_final_weight ??
  portfolioTarget?.data?.total_final_weight ??
  Object.values(weights).reduce((a, b) => a + Number(b || 0), 0)
);

const cashBuffer = Number(
  pt?.cash_buffer ??
  portfolioTarget?.cash_buffer ??
  portfolioTarget?.data?.cash_buffer ??
  ps?.cash_buffer ??
  portfolioState?.cash_buffer ??
  portfolioState?.data?.cash_buffer ??
  0
);


  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <div className="flex">
        <aside className="fixed left-0 top-0 z-20 flex h-screen w-[235px] max-xl:w-[220px] max-xl:w-[220px] flex-col border-r border-[#1a2533] bg-[#05080d] px-4 py-5">
          <div className="flex items-center gap-2 min-w-0">
            <svg
              viewBox="0 0 120 120"
              className="h-14 w-14 shrink-0 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.22)]"
              aria-hidden="true"
            >
              <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
                <path
                  d="
                    M60 6
                    L68 46
                    L99 21
                    L74 52
                    L114 60
                    L74 68
                    L99 99
                    L68 74
                    L60 114
                    L52 74
                    L21 99
                    L46 68
                    L6 60
                    L46 52
                    L21 21
                    L52 46
                    Z
                  "
                  strokeWidth="2.2"
                  fill="rgba(255,255,255,0.04)"
                />

                <path d="M60 6 L60 114" strokeWidth="1.4" opacity="0.8" />
                <path d="M6 60 L114 60" strokeWidth="1.4" opacity="0.8" />
                <path d="M21 21 L99 99" strokeWidth="1.2" opacity="0.55" />
                <path d="M99 21 L21 99" strokeWidth="1.2" opacity="0.55" />

                <path d="M60 6 L68 46 L60 60 L52 46 Z" strokeWidth="1.2" opacity="0.85" />
                <path d="M114 60 L74 68 L60 60 L74 52 Z" strokeWidth="1.2" opacity="0.85" />
                <path d="M60 114 L52 74 L60 60 L68 74 Z" strokeWidth="1.2" opacity="0.85" />
                <path d="M6 60 L46 52 L60 60 L46 68 Z" strokeWidth="1.2" opacity="0.85" />

                <circle cx="60" cy="60" r="7" strokeWidth="1.4" />
                <circle cx="60" cy="60" r="26" strokeWidth="1" opacity="0.45" />
              </g>
            </svg>

            <div className="leading-[1.05]">
              <div className="whitespace-nowrap text-[19px] font-bold tracking-[0.20em] text-white">NOVA STAR</div>
              <div className="mt-2 whitespace-nowrap text-[18px] font-light tracking-[0.24em] text-white">CAPITAL</div>
            </div>
          </div>

          <div className="mt-5 flex-1 overflow-y-auto pr-1 [scrollbar-width:thin] [scrollbar-color:#334155_transparent]">
            <SidebarSection title="Global" items={[
              <SidebarItem key="d" icon={Home} label="Dashboard" path="/dashboard" />,
              <SidebarItem key="fo" icon={Briefcase} label="Family Office" path="/family-office" />,
              <SidebarItem key="e" icon={Activity} label="Executive" path="/executive" />,
              <SidebarItem key="mi" icon={Brain} label="Market Intelligence" path="/market/intelligence" />,
              <SidebarItem key="c" icon={Gauge} label="Control Room" path="/control-room" />,
            ]} />

            <SidebarSection title="Portfolio" items={[
              <SidebarItem key="p" icon={Briefcase} label="Portfolio" path="/portfolio" />,
              <SidebarItem key="f" icon={Wallet} label="Funding Pools" path="/portfolio" />,
              <SidebarItem key="a" icon={Layers} label="Allocation / Rebalance" path="/portfolio" />,
              <SidebarItem key="l" icon={CircleCheck} label="Long Term" path="/bricks/lt" />,
            ]} />

            <SidebarSection title="Risk" items={[
              <SidebarItem key="r" icon={ShieldCheck} label="Risk Console" path="/risk" />,
              <SidebarItem key="pr" icon={ShieldCheck} label="Protection" path="/risk" />,
              <SidebarItem key="g" icon={ServerCog} label="Governance" />,
              <SidebarItem key="an" icon={AlertTriangle} label="Anomalies" path="/risk" />,
            ]} />

            <SidebarSection title="Execution" items={[
              <SidebarItem key="ob" icon={Activity} label="Order Board" path="/order-board" />,
              <SidebarItem key="pb" icon={Briefcase} label="Positions Board" path="/positions-board" />,
              <SidebarItem key="fb" icon={CircleCheck} label="Fills Board" path="/fills-board" />,
              <SidebarItem key="et" icon={ServerCog} label="Execution Trace" path="/execution-trace" />,
            ]} />
          </div>

          <div className="mt-3 shrink-0 rounded-lg border border-[#1f2a37] bg-[#0b131d] px-3 py-2">
            <div className="grid grid-cols-[1.5fr_1fr_1fr] items-center text-xs font-medium">
              <span>NSC Engine</span>
              <span className={`text-[9px] ${sourceState.online ? "text-emerald-400" : "text-amber-300"}`}>{sourceState.loading ? "● CHECKING" : sourceState.online ? `● ONLINE ${sourceState.available}/${sourceState.total}` : "● OFFLINE"}</span>
            </div>
            <div className="mt-1 text-[9px] text-slate-500">Control layer online</div>
          </div>
        </aside>

        <main className="ml-[235px] w-[calc(100%-235px)] p-3 max-xl:ml-[220px] max-xl:w-[calc(100%-220px)] max-lg:ml-0 max-lg:w-full max-xl:ml-[220px] max-xl:w-[calc(100%-220px)] max-lg:ml-0 max-lg:w-full">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold uppercase tracking-wide">Control Room</h1>
              <p className="text-xs text-slate-400">Decision, governance, allocation and execution alignment</p>
            </div>
            <div className="flex gap-2 text-[10px] uppercase">
              <span className="rounded-md border border-sky-400/30 bg-sky-400/10 px-2 py-1 text-sky-300">{sourceState.online ? (global.env || "UNAVAILABLE") : "OFFLINE"}</span>
              <span className="rounded-md border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 text-emerald-300">{String(regime).toUpperCase()}</span>
              <span className={`rounded-md border px-2 py-1 ${orchestrationTone}`} title={`Guardrail: ${masterGuardrailStatus} · Stale: ${masterStaleStatus} · ${orchestrationReasons.join(", ") || "No reason"}`}>
                ORCH {orchestrationStatus}
              </span>
              <span className={`rounded-md border px-2 py-1 ${globalAuditTone}`} title={`Checks: ${globalAuditSummary.ok_checks || 0}/${globalAuditSummary.total_checks || 0} · Blocking: ${globalAuditSummary.blocking_checks || 0}`}>
                GLOBAL {globalAuditStatus}
              </span>
              <span className={`rounded-md border px-2 py-1 ${supervisionGateTone}`} title={`Exec: ${supervisionGateActions.allow_real_execution ? "real allowed" : supervisionGateActions.allow_simulated_execution ? "simulated only" : "blocked"} · Rebalance: ${supervisionGateActions.allow_rebalance ? "allowed" : "blocked"} · Funding: ${supervisionGateActions.allow_funding ? "allowed" : "blocked"}`}>
                GATE {supervisionGateMode}
              </span>
              <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]">{global.governanceMode || "UNKNOWN"}</span>
            </div>
          </div>


          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-cyan-500/10 bg-[#071019]/95 px-3 py-2 shadow signals-[0_0_24px_rgba(34,211,238,0.05)]">

            <div className="mr-2 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></div>
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-200">
                System Health
              </span>
            </div>

            <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">
              {pipelineStatus}
            </span>

            <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">
              {kernelStatus}
            </span>

            <span className="rounded-md border border-sky-400/20 bg-sky-400/10 px-2 py-1 text-[10px] font-semibold text-sky-300">
              {governanceStatusLabel}
            </span>

            <span className="rounded-md border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] font-semibold text-amber-300">
              {executionSafetyLabel}
            </span>

            <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">
              {blockersLabel}
            </span>

            <span className="rounded-md border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-[10px] font-semibold text-cyan-300">
              {preprodSuccessfulRuns}/{preprodTotalRuns} RUNS
            </span>

            <span className="rounded-md border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-[10px] font-semibold text-cyan-300">
              {trendMetrics.success_rate_pct ?? 0}% SUCCESS
            </span>

          </div>

          <div className="mb-3 grid grid-cols-2 gap-3 xl:grid-cols-6">
            <Metric label="PAM Status" value={String(activityDashboard?.status || "UNKNOWN").toUpperCase()} tone={activityDashboard?.status === "healthy" ? "green" : activityDashboard?.status === "watch" ? "amber" : "slate"} />
            <Metric label="Portfolio Health" value={`${Number(pamSummary?.portfolio_health ?? 0).toFixed(1)}%`} tone={Number(pamSummary?.portfolio_health ?? 0) >= 90 ? "green" : "amber"} />
            <Metric label="Activity Score" value={`${Number(pamSummary?.activity_score ?? 0).toFixed(1)}%`} tone={Number(pamSummary?.activity_score ?? 0) >= 70 ? "green" : "amber"} />
            <Metric label="Deployment" value={`${pamCapitalDeploymentPct.toFixed(1)}%`} tone="cyan" />
            <Metric label="Gross Exposure" value={`${pamGrossExposurePct.toFixed(1)}%`} tone={pamGrossExposurePct > 102 ? "amber" : "green"} />
            <Metric label="Investment Engines" value={`${pamSummary?.investment_engines_active ?? 0}/${pamSummary?.investment_engines_total ?? 0}`} tone="blue" />
            <Metric label="PAM Alerts" value={pamSummary?.alerts_count ?? 0} tone={Number(pamSummary?.alerts_count ?? 0) > 0 ? "amber" : "green"} />
          </div>

          <div className="mb-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-r from-[#060b12] via-[#08111b] to-[#060b12] px-4 py-3 shadow signals-[0_0_60px_rgba(34,211,238,0.05)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-100">
                  Live Telemetry Terminal
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">latency 12ms</span>
                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">allocator sync {Math.round(Number(productionReadiness?.allocator_sync_pct ?? productionReadiness?.progress_pct ?? 0))}%</span>
                <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-2 py-1 text-violet-300">ai cycle online</span>
                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">governance stable</span>
                <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-2 py-1 text-sky-300">event streams active</span>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">shadow healthy</span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-6 gap-2 items-stretch">

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Decision Engine</div>
              <Metric label="System Decision" value={systemDecision} tone={systemDecisionTone} />
              <div className="mt-1 text-[10px] text-slate-300">Regime {String(regime).toUpperCase()} · Risk flags {riskFlags} · Governance {global.governanceMode || "unknown"}</div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Supervision Gate</div>
              <Metric label="Gate Mode" value={supervisionGateMode} tone={supervisionGateOpen ? "green" : "red"} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Execution: {supervisionGateActions.allow_real_execution ? "Real allowed" : supervisionGateActions.allow_simulated_execution ? "Simulated only" : "Blocked"}</div>
                <div>Rebalance: {supervisionGateActions.allow_rebalance ? "Allowed" : "Blocked"}</div>
                <div>Funding: {supervisionGateActions.allow_funding ? "Allowed" : "Blocked"}</div>
              </div>
              <div className={`mt-1 text-[10px] ${supervisionGateOpen ? "text-emerald-300" : "text-red-300"}`}>
                {supervisionGateOpen ? "Checks cleared" : "Safe mode required."}
              </div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Stress Tests</div>
              <Metric label="Status" value={stressStatus.toUpperCase()} tone={stressFailed === 0 ? "green" : "red"} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Mode: {stressTests.mode || "UNKNOWN"}</div>
                <div>Passed: {stressPassed}/{stressTotal}</div>
                <div>Failed: {stressFailed}</div>
              </div>
              <div className={`mt-1 text-[10px] ${stressFailed === 0 ? "text-emerald-300" : "text-red-300"}`}>
                {stressFailed === 0 ? "Stress OK" : "Stress test failures detected."}
              </div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">48h Shadow</div>
              <Metric label="Status" value={shadowSignalsStatus} tone={shadowSignalsFailed === 0 ? "green" : "red"} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Progress: {shadowSignalsProgressPct}%</div>
                <div>Checks: {shadowSignalsPassed}/{shadowSignalsTotal}</div>
                <div>Failed: {shadowSignalsFailed}</div>
              </div>
              <div className={`mt-1 text-[10px] ${shadowSignalsDecision.can_continue_shadow ? "text-emerald-300" : "text-red-300"}`}>
                {shadowSignalsDecision.can_continue_shadow ? "Shadow OK" : "Shadow intervention required."}
              </div>
            </Box>

            <Box className="p-3 h-full min-h-[72px] border-cyan-400/20 bg-cyan-400/5">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.16em] text-cyan-300/70">60D Global PREPROD Long Run</div>
                  <div className="mt-1 text-lg font-semibold text-white">{longRunCanContinue ? "ACTIVE" : "PAUSED"}</div>
                </div>
                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${
                  longRunCanContinue
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                    : "border-red-400/30 bg-red-400/10 text-red-300"
                }`}>
                  {longRunCanContinue ? "Monitoring Active" : "Intervention Required"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Execution</div>
                  <div className="mt-1 font-semibold text-white">
                    {longRunSimulatedExecution ? "SIMULATED ONLY" : longRunRealExecution ? "REAL ENABLED" : "PAUSED"}
                  </div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Funding</div>
                  <div className="mt-1 font-semibold text-white">
                    {longRunManualFunding ? "MANUAL REQUIRED" : "NO TRANSFER"}
                  </div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Blocking</div>
                  <div className={longRunBlocking === 0 ? "mt-1 font-semibold text-emerald-300" : "mt-1 font-semibold text-red-300"}>{longRunBlocking}</div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Daily Failures</div>
                  <div className={longRunDailyFailed === 0 ? "mt-1 font-semibold text-emerald-300" : "mt-1 font-semibold text-red-300"}>{longRunDailyFailed}</div>
                </div>
              </div>

              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-[10px] text-slate-400">
                  <span>Progress J{longRunProgress.current_day ?? "—"}/{longRunProgress.target_duration_days || 60}</span>
                  <span>{longRunProgress.progress_pct ?? 0}%</span>
                </div>
                <div className="h-1.5 rounded bg-[#1a2532]">
                  <div
                    className="h-1.5 rounded bg-cyan-400"
                    style={{ width: `${Math.max(0, Math.min(100, Number(longRunProgress.progress_pct || 0)))}%` }}
                  />
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-2">
                <div className="text-[9px] uppercase tracking-[0.16em] text-cyan-300/70">Active Phase</div>
                <div className="mt-1 text-[11px] font-semibold text-white">{longRunActivePhase.name || "—"}</div>
                <div className="mt-1 text-[10px] leading-relaxed text-slate-300">{longRunActivePhase.focus || "Monitoring global preprod."}</div>
              </div>

              <div className="mt-3 grid gap-1">
                {longRunPhases.map((phase) => {
                  const active =
                    Number(longRunProgress.current_day || 0) >= Number(phase.start_day || 0) &&
                    Number(longRunProgress.current_day || 0) <= Number(phase.end_day || 0);

                  return (
                    <div
                      key={phase.name}
                      className={`rounded-md border px-2 py-1 text-[9px] ${
                        active
                          ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-200"
                          : "border-[#1f2a37] bg-[#0f1722] text-slate-500"
                      }`}
                    >
                      <span className="font-semibold">{phase.name}</span>
                      {active ? <span className="ml-2 text-emerald-300">ACTIVE</span> : null}
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Current Day</div>
                  <div className="mt-1 font-semibold text-cyan-200">
                    J{longRunCurrentDay}/{longRunTargetDays}
                  </div>
                </div>

                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">ETA</div>
                  <div className="mt-1 font-semibold text-cyan-200">
                    {longRunEta}
                  </div>
                </div>

                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Remaining</div>
                  <div className="mt-1 font-semibold text-cyan-200">
                    {longRunRemainingDays}d
                  </div>
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-2">
                <div className="flex items-center justify-between">
                  <div className="text-[9px] uppercase tracking-[0.16em] text-emerald-300/70">
                    Long Run Health
                  </div>

                  <div className={`text-sm font-semibold ${
                    longRunHealthScore >= 90
                      ? "text-emerald-300"
                      : longRunHealthScore >= 75
                        ? "text-amber-300"
                        : "text-red-300"
                  }`}>
                    {longRunHealthScore}/100
                  </div>
                </div>

                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#111927]">
                  <div
                    className={`h-full rounded-full ${
                      longRunHealthScore >= 90
                        ? "bg-emerald-400"
                        : longRunHealthScore >= 75
                          ? "bg-amber-400"
                          : "bg-red-400"
                    }`}
                    style={{ width: `${longRunHealthScore}%` }}
                  />
                </div>
              </div>

              <div className="mt-3 rounded-lg border border-violet-400/20 bg-violet-400/5 p-2">
                <div className="text-[9px] uppercase tracking-[0.16em] text-violet-300/70">
                  Timeline Checkpoints
                </div>

                <div className="mt-2 grid gap-1">
                  {longRunTimeline.map((item) => {
                    const passed = longRunCurrentDay > item.day;
                    const active = longRunCurrentDay === item.day;

                    return (
                      <div
                        key={item.day}
                        className={`rounded-md border px-2 py-1 text-[9px] ${
                          active
                            ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-200"
                            : passed
                              ? "border-emerald-400/20 bg-emerald-400/5 text-emerald-300"
                              : "border-[#1f2a37] bg-[#0f1722] text-slate-500"
                        }`}
                      >
                        {passed ? "✓" : active ? "▶" : "○"} J{item.day} · {item.label}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="mt-3 text-[10px] leading-relaxed text-cyan-100/80">
                {longRunTargetDays}-day PREPROD observation active under SIMULATED_ONLY governance.
                Real execution disabled. Manual funding separation remains enforced.
              </div>
            </Box>

            <Box className="p-3 h-full min-h-[72px] border-cyan-400/20 bg-cyan-400/5">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.16em] text-cyan-300/70">Dynamic Data Integrity</div>
                  <div className={`mt-1 text-lg font-semibold ${
                    dynamicMetricsStatus === "OK" ? "text-emerald-300" : "text-amber-300"
                  }`}>
                    {dynamicMetricsStatus}
                  </div>
                </div>

                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${
                  dynamicMetricsWarnings === 0
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                    : "border-amber-400/30 bg-amber-400/10 text-amber-300"
                }`}>
                  {dynamicMetricsOk}/{dynamicMetricsAudit?.metrics_checked || 0} OK
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Warnings</div>
                  <div className={dynamicMetricsWarnings === 0 ? "mt-1 font-semibold text-emerald-300" : "mt-1 font-semibold text-amber-300"}>
                    {dynamicMetricsWarnings}
                  </div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Avg Freshness</div>
                  <div className="mt-1 font-semibold text-cyan-200">{dynamicMetricsFreshnessAvg}s</div>
                </div>
              </div>

              <div className="mt-3 grid gap-1">
                {dynamicMetricsResults.slice(0, 5).map((m) => (
                  <div key={m.metric} className="flex items-center justify-between rounded-md border border-[#1f2a37] bg-[#0f1722] px-2 py-1 text-[9px]">
                    <span className="truncate text-slate-300">{m.metric}</span>
                    <span className={m.status === "OK" ? "text-emerald-300" : "text-amber-300"}>
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </Box>

            <Box className="p-3 h-full min-h-[72px] border-sky-400/20 bg-sky-400/5">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.16em] text-sky-300/70">Institutional Committees</div>
                  <div className="mt-1 text-lg font-semibold text-white">{committeeProjection}</div>
                </div>

                <span className="rounded-md border border-sky-400/30 bg-sky-400/10 px-2 py-1 text-[10px] font-semibold text-sky-300">
                  {committeeConfidenceTrend}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px]">
                {[
                  ["Technical", committeeStatuses.technical_committee],
                  ["Risk", committeeStatuses.risk_committee],
                  ["Governance", committeeStatuses.governance_committee],
                  ["Production", committeeStatuses.production_committee],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                    <div className="text-slate-400">{label}</div>
                    <div className={`mt-1 font-semibold ${
                      value === "APPROVED" || value === "ELIGIBLE"
                        ? "text-emerald-300"
                        : value === "WATCH" || value === "UNDER_REVIEW"
                          ? "text-amber-300"
                          : "text-red-300"
                    }`}>
                      {value || "—"}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3 rounded-lg border border-sky-400/20 bg-sky-400/5 p-2 text-[10px]">
                <div className="text-slate-400">Active Phase</div>
                <div className="mt-1 font-semibold text-sky-200">{committeeProgress.active_phase || "—"}</div>
                <div className="mt-1 text-slate-400">
                  ETA {committeeProgress.eta || "—"} · Remaining {committeeProgress.remaining_days ?? "—"}d
                </div>
              </div>
            </Box>

            <Box className="p-3 h-full min-h-[72px] border-emerald-400/20 bg-emerald-400/5">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.16em] text-emerald-300/70">Weekly Institutional Review</div>
                  <div className="mt-1 text-lg font-semibold text-white">{weeklyStability}</div>
                </div>

                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${
                  weeklyHealth >= 90
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                    : weeklyHealth >= 75
                      ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
                      : "border-red-400/30 bg-red-400/10 text-red-300"
                }`}>
                  {weeklyHealth}/100
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Execution</div>
                  <div className="mt-1 font-semibold text-emerald-200">{weeklyInstitutional.execution_integrity || "—"}</div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Governance</div>
                  <div className="mt-1 font-semibold text-emerald-200">{weeklyInstitutional.governance_integrity || "—"}</div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Risk Drift</div>
                  <div className="mt-1 font-semibold text-emerald-200">{weeklyInstitutional.risk_drift || "—"}</div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Decision</div>
                  <div className="mt-1 font-semibold text-emerald-200">{weeklyRecommendation}</div>
                </div>
              </div>

              <div className="mt-2 text-[10px] leading-relaxed text-emerald-100/80">
                Weekly review consolidates stability, governance, risk drift and anomaly trend across the active PREPROD observation cycle.
              </div>
            </Box>

            <Box className="p-3 h-full min-h-[72px] border-violet-400/20 bg-violet-400/5">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.16em] text-violet-300/70">Production Readiness</div>
                  <div className={`mt-1 text-lg font-semibold ${
                    productionDecision === "GO"
                      ? "text-emerald-300"
                      : productionDecision === "CONDITIONAL_GO"
                        ? "text-amber-300"
                        : productionDecision === "NO_GO"
                          ? "text-red-300"
                          : "text-slate-300"
                  }`}>
                    {productionDecision}
                  </div>
                </div>

                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${
                  productionScore >= 90
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                    : productionScore >= 75
                      ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
                      : "border-red-400/30 bg-red-400/10 text-red-300"
                }`}>
                  {productionScore}/100
                </span>
              </div>

              <div className="h-1.5 overflow-hidden rounded-full bg-[#111927]">
                <div
                  className={`h-full rounded-full ${
                    productionScore >= 90
                      ? "bg-emerald-400"
                      : productionScore >= 75
                        ? "bg-amber-400"
                        : "bg-red-400"
                  }`}
                  style={{ width: `${Math.max(0, Math.min(100, productionScore))}%` }}
                />
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Progress</div>
                  <div className="mt-1 font-semibold text-violet-200">{productionReadiness?.progress_pct ?? 0}%</div>
                </div>
                <div className="rounded-lg border border-[#1f2a37] bg-[#0f1722] p-2">
                  <div className="text-slate-400">Day</div>
                  <div className="mt-1 font-semibold text-violet-200">J{productionReadiness?.current_day || "—"}/{productionReadiness?.target_duration_days || 60}</div>
                </div>
              </div>

              <div className="mt-2 text-[10px] leading-relaxed text-violet-100/80">
                {productionRecommendation}
              </div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Anomaly Detector</div>
              <Metric label="Status" value={anomalyStatus} tone={anomalyStatus === "CLEAR" ? "green" : anomalyStatus === "WARNING" ? "amber" : "red"} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Total: {anomalyTotal}</div>
                <div>Critical: {anomalyCritical}</div>
                <div>Warning: {anomalyWarning}</div>
              </div>
              <div className={`mt-1 text-[10px] ${anomalyTotal === 0 ? "text-emerald-300" : "text-amber-300"}`}>
                {anomalyTotal === 0 ? "No anomaly" : "Anomalies require review."}
              </div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Trend Monitor</div>
              <Metric label="Status" value={trendStatus} tone={trendStatus === "HEALTHY" ? "green" : "amber"} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Success: {trendMetrics.success_rate_pct ?? 0}%</div>
                <div>Avg duration: {trendMetrics.avg_duration_sec ?? 0}s</div>
                <div>Alerts: {trendAlerts.length}</div>
              </div>
              <div className={`mt-1 text-[10px] ${trendAlerts.length === 0 ? "text-emerald-300" : "text-amber-300"}`}>
                {trendAlerts.length === 0 ? "Trend stable" : "Trend alerts active."}
              </div>
            </Box>

            <Box className="p-2 h-full min-h-[72px]">
              <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 mb-1">Preprod History</div>
              <Metric label="Runs" value={`${preprodSuccessfulRuns}/${preprodTotalRuns}`} tone={preprodHistoryTone} />
              <div className="mt-1 grid gap-0.5 text-[10px] text-slate-300">
                <div>Failed runs: {preprodFailedRuns}</div>
                <div>Degraded runs: {preprodDegradedRuns}</div>
                <div>Last: {preprodLastRun.status || "UNKNOWN"} · {preprodLastRun.global_status || "UNKNOWN"}</div>
                <div>Gate: {preprodLastRun.gate_mode || "UNKNOWN"} · Stress failed: {preprodLastRun.stress_failed ?? "—"}</div>
              </div>
              <div className={`mt-1 text-[10px] ${
                preprodHistoryTone === "green"
                  ? "text-emerald-300"
                  : preprodHistoryTone === "amber"
                    ? "text-amber-300"
                    : "text-red-300"
              }`}>
                {preprodLastRunOk
                  ? preprodFailedRuns > 0 || preprodDegradedRuns > 0
                    ? "Current run healthy · historical incidents detected."
                    : "History healthy."
                  : "Current cycle requires attention."}
              </div>
            </Box>

          </div>


          <div className="mb-3 rounded-2xl border border-violet-400/10 bg-gradient-to-r from-[#080d18] via-[#101426] to-[#080d18] px-3 py-2 shadow signals-[0_0_40px_rgba(139,92,246,0.05)]">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-violet-400 animate-pulse"></div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-100">
                  Institutional Intelligence Layer
                </div>
              </div>

              <div className="text-[9px] uppercase tracking-[0.18em] text-slate-500">
                Market context · AI supervision · Drift awareness
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2">
              <div className="rounded-xl border border-emerald-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Market Regime</div>
                <div className="mt-1 text-[11px] font-semibold text-emerald-300">{String(regime).toUpperCase()}</div>
              </div>

              <div className="rounded-xl border border-cyan-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">AI Core</div>
                <div className="mt-1 text-[11px] font-semibold text-cyan-300">ONLINE</div>
              </div>

              <div className="rounded-xl border border-amber-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Governance AI</div>
                <div className="mt-1 text-[11px] font-semibold text-amber-300">{global.governanceMode || "UNKNOWN"}</div>
              </div>

              <div className="rounded-xl border border-violet-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Drift State</div>
                <div className="mt-1 text-[11px] font-semibold text-violet-300">WATCHING</div>
              </div>

              <div className="rounded-xl border border-emerald-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Risk Layer</div>
                <div className="mt-1 text-[11px] font-semibold text-emerald-300">STABLE</div>
              </div>

              <div className="rounded-xl border border-cyan-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Signals</div>
                <div className="mt-1 text-[11px] font-semibold text-cyan-300">SYNCED</div>
              </div>

              <div className="rounded-xl border border-sky-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Cross-Asset</div>
                <div className="mt-1 text-[11px] font-semibold text-sky-300">ACTIVE</div>
              </div>

              <div className="rounded-xl border border-amber-400/10 bg-[#0b1420]/80 px-3 py-2">
                <div className="text-[8px] uppercase tracking-[0.16em] text-slate-500">Liquidity</div>
                <div className="mt-1 text-[11px] font-semibold text-amber-300">NORMAL</div>
              </div>
            </div>
          </div>

          <div className="mb-2 rounded-2xl border border-fuchsia-400/10 bg-gradient-to-r from-[#081018] via-[#0d1524] to-[#081018] px-4 py-3 shadow signals-[0_0_60px_rgba(168,85,247,0.08)]">
            <div className="flex items-center justify-between gap-4 flex-wrap">

              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-fuchsia-400 animate-pulse"></div>

                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-fuchsia-100">
                    Global Decision Flow
                  </div>
                </div>

                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  Market Intelligence → Governance → Allocation → Execution
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.14em]">

                <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-cyan-300 shadow signals-[0_0_15px_rgba(34,211,238,0.08)]">
                  Market Regime
                </div>

                <div className="text-slate-600">→</div>

                <div className="rounded-xl border border-violet-400/20 bg-violet-400/10 px-3 py-2 text-violet-300 shadow signals-[0_0_15px_rgba(168,85,247,0.08)]">
                  Intelligence
                </div>

                <div className="text-slate-600">→</div>

                <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-300 shadow signals-[0_0_15px_rgba(251,191,36,0.08)]">
                  Governance
                </div>

                <div className="text-slate-600">→</div>

                <div className="rounded-xl border border-sky-400/20 bg-sky-400/10 px-3 py-2 text-sky-300 shadow signals-[0_0_15px_rgba(56,189,248,0.08)]">
                  Allocation
                </div>

                <div className="text-slate-600">→</div>

                <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-emerald-300 shadow signals-[0_0_15px_rgba(16,185,129,0.08)]">
                  Execution
                </div>

                <div className="text-slate-600">→</div>

                <div className="rounded-xl border border-slate-500/20 bg-slate-500/10 px-3 py-2 text-slate-300 shadow signals-[0_0_15px_rgba(148,163,184,0.08)]">
                  Monitoring
                </div>

              </div>
            </div>
          </div>


          <div className="mb-2 rounded-2xl border border-cyan-400/10 bg-gradient-to-r from-[#071018] via-[#0a1724] to-[#071018] px-4 py-3 shadow signals-[0_0_50px_rgba(34,211,238,0.05)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-cyan-100">
                    Operational Core
                  </div>
                </div>

                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Governance • Capital Allocation • Execution Supervision
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">
                  Runtime Stable
                </span>

                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">
                  Allocation Synced
                </span>

                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">
                  Simulated Only
                </span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-1 md:grid-cols-3 gap-2 items-stretch">
            <Box className="p-3 h-full rounded-2xl border border-amber-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(15,23,42,0.45)] backdrop-blur-sm transition-all duration-300 hover:-translate-y-[1px] hover:border-amber-400/20 hover:shadow-[0_0_55px_rgba(15,23,42,0.65)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Core</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">
                    Institutional Safety Layer
                  </div>
                </div>

                <LiveIndicator label="LIVE" tone="emerald" />
              </div>

              <div className="grid gap-2">
                <Metric label="Hard Block" value={hardBlock ? "ON" : "OFF"} tone={hardBlock ? "red" : "green"} />

                <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 px-3 py-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Policy / Mode</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-[11px] font-semibold text-amber-300">
                      {actionPolicy}
                    </span>
                    <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-[11px] font-semibold text-amber-300">
                      {global.governanceMode || "UNKNOWN"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-1 text-[10px] leading-relaxed text-amber-300">
                Simulated-only constraints enforced.
              </div>
            </Box>

            <Box className="p-3 h-full border border-cyan-400/10 bg-gradient-to-b from-[#0b1722] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.06)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Capital Control Core</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">
                    Portfolio Allocation Supervision
                  </div>
                </div>

                <LiveIndicator label="ACTIVE" tone="cyan" />
              </div>
              <div className="grid gap-2">
                <Metric label="Capital Observed" value={eur(global.capitalObserved)} tone="blue" />
                <Metric label="Capital Engaged" value={eur(global.capitalEngaged)} tone="cyan" />
                <Metric label="Cash Available" value={eur(global.cashAvailable)} tone="blue" />
                <Metric label="Live Exposure" value={pct(Number(global.liveExposureRatio ?? 0))} tone="amber" />
              </div>
            </Box>

            <Box className="p-3 h-full border border-emerald-400/10 bg-gradient-to-b from-[#0c1720] to-[#09111a] shadow signals-[0_0_40px_rgba(16,185,129,0.06)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Execution Alignment Core</div>
                  <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">
                    Live Execution Supervision
                  </div>
                </div>

                <LiveIndicator label="SYNCED" tone="emerald" />
              </div>
              <div className="grid gap-2">
                <Metric label="Rebalance Reductions" value={rebalanceReductions} tone={rebalanceReductions > 0 ? "amber" : "green"} />
                <Metric label="Execution Plan Orders" value={simulatedOrdersCount} />
                <Metric label="Blocked Orders" value={blockedSimulatedOrdersCount} tone={blockedSimulatedOrdersCount > 0 ? "amber" : "green"} />
                <Metric label="Status" value={auditStatusLabel} tone={auditStatusLabel === "AUDIT OK" ? "green" : "amber"} />
              </div>
              <div className="mt-3 text-[11px] text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]">Execution remains simulated while rebalance requests reductions.</div>
            </Box>
          </div>

          <div className="mb-3 rounded-2xl border border-sky-400/10 bg-gradient-to-r from-[#071018] via-[#0a1724] to-[#071018] px-4 py-3 shadow signals-[0_0_50px_rgba(56,189,248,0.05)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-sky-400 animate-pulse"></div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-sky-100">
                    Alignment & Decision Layer
                  </div>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Portfolio target state · blockers · authority · decision timeline
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">Target Synced</span>
                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">Watch Active</span>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">Timeline Live</span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-[1.3fr_1fr] gap-3">
            <Box className="p-3 h-full rounded-2xl border border-sky-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(15,23,42,0.45)] backdrop-blur-sm transition-all duration-300 hover:-translate-y-[1px] hover:border-sky-400/20 hover:shadow-[0_0_55px_rgba(15,23,42,0.65)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Target vs State Alignment</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-sky-300/70">Portfolio drift supervision</div>
                </div>
                <LiveIndicator label="SYNCED" tone="cyan" />
              </div>
              <div className="grid grid-cols-[1fr_0.55fr_0.55fr_0.55fr_0.55fr_1.3fr] border-b border-[#1f2a37] pb-2 text-[10px] uppercase text-slate-500">
                <div>Brick</div><div>Target</div><div>Current</div><div>Gap</div><div>Confidence</div><div>Reason</div>
              </div>
              {(Object.keys(weights).length ? Object.keys(weights) : Object.keys(bricks)).map((key) => {
                const target = Number(
                  weights?.[key] ??
                  bricks?.[key]?.target_weight_snapshot ??
                  pt?.final_brick_weights?.[key] ??
                  portfolioTarget?.final_brick_weights?.[key] ??
                  portfolioTarget?.data?.final_brick_weights?.[key] ??
                  0
                );

                const raw = Number(
                  rawWeights?.[key] ??
                  pt?.raw_brick_weights?.[key] ??
                  portfolioTarget?.raw_brick_weights?.[key] ??
                  portfolioTarget?.data?.raw_brick_weights?.[key] ??
                  target
                );
                

const current = Number(bricks?.[key]?.current_weight_estimate ?? bricks?.[key]?.target_weight_snapshot ?? 0);


                const gap = current - target;
                return (
                  <div key={humanBrickName(key)} className="grid grid-cols-[1fr_0.55fr_0.55fr_0.55fr_0.55fr_1.3fr] border-b border-[#172231] py-2 text-[11px]">
                    <div className="truncate text-white">{humanBrickName(key)}</div>
                    <div>{pct(Number(weights?.[key] ?? target))}</div>
                    <div>{pct(current)}</div>
                    <div className={gapTone(gap)}>{pct(gap)}</div>
                    <div className={confidenceTone(getBrickConfidence(key, confidence, pt, bricks))}>
                      {Math.round(getBrickConfidence(key, confidence, pt, bricks) * 100)}%
                    </div>
                    <div className="truncate text-slate-400">{getReason(key, target, raw, regime)}</div>
                  </div>
                );
              })}
            </Box>

            <Box className="p-3 border border-amber-400/10 bg-gradient-to-b from-[#0c1622] to-[#09111a] shadow signals-[0_0_40px_rgba(251,191,36,0.05)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Alerts / Blockers</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">Constraint watch board</div>
                </div>
                <LiveIndicator label="WATCH" tone="amber" />
              </div>
              {[
                ["Soft Governance", riskFlags ? `${riskFlags} soft governance constraint(s)` : "No soft governance constraint", riskFlags ? "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]" : "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]"],
                ["Execution", `${actionPolicy} — no real order allowed`, "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]"],
                ["Funding", "Manual inter-universe funding required", "text-sky-300"],
                ["Rebalance", "Defensive / bonds / metals reduction requested", "text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)]"],
              ].map(([k, v, cls]) => (
                <div key={k} className="grid grid-cols-[0.7fr_1.6fr] border-b border-[#172231] py-2 text-[11px]">
                  <div className="text-slate-400">{k}</div>
                  <div className={cls}>{v}</div>
                </div>
              ))}
            </Box>
          </div>

          <div className="grid grid-cols-[1fr_1fr] gap-3">
            <Box className="p-3 border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(16,185,129,0.05)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Brick Authority Matrix</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Execution authority per brick</div>
                </div>
                <LiveIndicator label="MATRIX" tone="emerald" />
              </div>
              <div className="grid grid-cols-[1fr_0.9fr_0.8fr_0.6fr] border-b border-[#1f2a37] pb-2 text-[10px] uppercase text-slate-500">
                <div>Brick</div><div>Mode</div><div>Regime</div><div>PnL</div>
              </div>
              {strategies.map((s) => (
                <div key={s.key} className="grid grid-cols-[1fr_0.9fr_0.8fr_0.6fr] border-b border-[#172231] py-2 text-[11px]">
                  <div className="truncate text-white">{s.key}</div>
                  <div className="truncate text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]">{s.mode || "—"}</div>
                  <div className="truncate">{s.regime || "—"}</div>
                  <div className={Number(s.pnl || 0) >= 0 ? "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]" : "text-red-400"}>{eur(s.pnl)}</div>
                </div>
              ))}
            </Box>

            <Box className="p-3 border border-violet-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(139,92,246,0.05)]">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Decision Timeline Core</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">Institutional decision trace</div>
                </div>
                <LiveIndicator label="LIVE" tone="violet" />
              </div>
              <div className="grid gap-2 text-[11px]">
                {[
                  ["T-00", "Portfolio Engine", regime === "risk_on" ? "Risk-on allocation selected" : "Portfolio regime evaluated", "INFO"],
                  ["T-01", "Risk Engine", riskFlags > 0 ? `${riskFlags} soft governance constraint(s) detected` : "No soft governance constraint", riskFlags > 0 ? "WATCH" : "INFO"],
                  ["T-02", "Governance", `${actionPolicy} policy enforced`, actionPolicy.includes("SIMULATED") ? "WATCH" : "INFO"],
                  ["T-03", "Execution", hardBlock ? "Execution blocked by hard block" : "No hard block detected", hardBlock ? "BLOCKED" : "INFO"],
                  ["T-04", "Options Shadow", "Shadow overlay isolated from live execution", "INFO"],
                  ["T-05", "Funding", "Manual inter-universe funding constraint acknowledged", "WATCH"],
                ].map(([time, engine, message, level], idx) => {
                  const badge =
                    level === "BLOCKED"
                      ? "bg-red-500/15 text-red-400 border-red-500/30"
                      : level === "CAUTION"
                        ? "bg-amber-500/15 text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.25)] border-amber-500/30"
                        : level === "WATCH"
                          ? "bg-cyan-500/15 text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)] border-cyan-500/30"
                          : "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";

                  return (
                    <div key={idx} className="grid grid-cols-[0.35fr_0.75fr_1.7fr_0.5fr] items-center gap-2 rounded-lg border border-[#172231] bg-[#0d1520] px-3 py-2 transition-all duration-200 hover:border-cyan-500/30 hover:bg-[#101b29]">
                      <div className="font-mono text-[10px] text-slate-500">{time}</div>
                      <div className="font-semibold text-slate-200">{engine}</div>
                      <div className="truncate text-slate-400">{message}</div>
                      <span className={`justify-self-end rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${badge}`}>
                        {level}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>


          <div className="mb-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-r from-[#071018] via-[#0a1724] to-[#071018] px-4 py-3 shadow signals-[0_0_50px_rgba(34,211,238,0.05)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-cyan-100">
                    Runtime Telemetry Layer
                  </div>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Live system metrics · governance events · operational heartbeat
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">Heartbeat OK</span>
                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">Telemetry Synced</span>
                <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-2 py-1 text-violet-300">Events Live</span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Runtime Telemetry</div>
                    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">System heartbeat and freshness</div>
                  </div>
                  <LiveIndicator label="LIVE" tone="cyan" />
                </div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500">UI v6.0.0</div>
              </div>

              <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1.1fr] gap-3">
                <TelemetryMetric
                  label="API Latency"
                  value={`${apiLatencyMs}ms`}
                  status={apiLatencyMs > 500 ? "critical" : apiLatencyMs > 180 ? "caution" : "ok"}
                />
                <TelemetryMetric
                  label="Governance Sync"
                  value={timeAgoLabel(telemetryGeneratedAt)}
                  status={telemetryStatus}
                />
                <TelemetryMetric
                  label="Execution Audit"
                  value={timeAgoLabel(telemetryGeneratedAt)}
                  status={hardBlock ? "critical" : "ok"}
                />
                <TelemetryMetric
                  label="Signal Freshness"
                  value={`${signalFreshnessPct.toFixed(0)}%`}
                  status={signalFreshnessPct < 60 ? "critical" : signalFreshnessPct < 80 ? "caution" : "ok"}
                />
                <Heartbeat status={telemetryStatus === "critical" ? "critical" : telemetryStatus === "watch" ? "caution" : "ok"} />
              </div>
            </Box>
          </div>


          <div className="mb-3 rounded-2xl border border-violet-400/10 bg-gradient-to-r from-[#080d18] via-[#101426] to-[#080d18] px-4 py-3 shadow signals-[0_0_50px_rgba(139,92,246,0.05)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-violet-400 animate-pulse"></div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-violet-100">
                    Governance Intelligence Layer
                  </div>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Decision rationale · governance stream · explainability · portfolio brain
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-2 py-1 text-violet-300">AI Rationale</span>
                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">Governance Trace</span>
                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">Brain Map Live</span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-violet-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(139,92,246,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-violet-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Last Governance Decision</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">Latest institutional decision state</div>
                </div>
                <div className="flex items-center gap-2">
                  <LiveIndicator label="DECISION" tone="violet" />
                  <div className="text-[10px] uppercase tracking-widest text-slate-500">UI v6.0.0</div>
                </div>
              </div>

              <div className="grid grid-cols-[1.4fr_0.8fr_0.8fr_1fr] gap-3">
                <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3">
                  <div className="text-[9px] uppercase tracking-widest text-cyan-300/70">Decision</div>
                  <div className="mt-1 text-[13px] font-semibold text-white">
                    {regime === "risk_on"
                      ? "Risk-on allocation maintained"
                      : regime === "risk_off"
                        ? "Capital preservation prioritized"
                        : "Balanced allocation maintained"}
                  </div>
                  <div className="mt-2 text-[11px] text-slate-400">
                    Execution remains constrained by {actionPolicy} governance.
                  </div>
                </div>

                <div className="rounded-xl border border-[#1f2a37] bg-[#0d1520] px-4 py-3">
                  <div className="text-[9px] uppercase tracking-widest text-slate-500">Source Engine</div>
                  <div className="mt-1 text-[13px] font-semibold text-slate-100">Governance Core</div>
                  <div className="mt-2 text-[11px] text-slate-500">policy layer</div>
                </div>

                <div className="rounded-xl border border-[#1f2a37] bg-[#0d1520] px-4 py-3">
                  <div className="text-[9px] uppercase tracking-widest text-slate-500">Confidence</div>
                  <div className="mt-1 text-[13px] font-semibold text-emerald-300">{globalConfidenceScore}%</div>
                  <div className="mt-2 h-1.5 rounded bg-[#172231]">
                    <div className="h-1.5 rounded bg-emerald-400" style={{ width: `${Math.max(0, Math.min(100, Number(globalConfidenceScore || 0)))}%` }} />
                  </div>
                </div>

                <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
                  <div className="text-[9px] uppercase tracking-widest text-amber-300/70">Constraints</div>
                  <div className="mt-1 text-[13px] font-semibold text-amber-200">{actionPolicy}</div>
                  <div className="mt-2 text-[11px] text-slate-400">
                    Manual funding and simulated execution remain enforced.
                  </div>
                </div>
              </div>
            </Box>
          </div>


          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Event Stream</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Live governance trace</div>
                </div>
                <LiveIndicator label="STREAM" tone="cyan" />
              </div>

              <div className="grid gap-2 text-[11px]">
                {[
                  ["T+00", "Governance Core", "PREPROD policy verified", "OK"],
                  ["T+01", "Risk Engine", riskFlags > 0 ? `${riskFlags} soft governance constraint(s) monitored` : "No soft governance constraint", riskFlags > 0 ? "WATCH" : "OK"],
                  ["T+02", "Execution Engine", hardBlock ? "Hard block active: execution denied" : "No hard block detected", hardBlock ? "BLOCKED" : "OK"],
                  ["T+03", "Allocator", "Drift classified as governed deviation", "WATCH"],
                  ["T+04", "Funding Layer", fundingEventMessage, fundingLayerStatus],
                  ["T+05", "Options Shadow", "Overlay isolated from live execution flow", "OK"],
                ].map(([time, source, message, level], idx) => {
                  const tone =
                    level === "BLOCKED"
                      ? "border-red-500/30 bg-red-500/10 text-red-300"
                      : level === "WATCH"
                        ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                        : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

                  return (
                    <div key={idx} className="grid grid-cols-[0.35fr_0.9fr_1.8fr_0.45fr] items-center gap-3 rounded-lg border border-[#172231] bg-[#0d1520] px-3 py-2 transition-all duration-200 hover:border-cyan-500/30 hover:bg-[#101b29]">
                      <div className="font-mono text-[10px] text-slate-500">{time}</div>
                      <div className="font-semibold text-slate-200">{source}</div>
                      <div className="truncate text-slate-400">{message}</div>
                      <span className={`justify-self-end rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${tone}`}>
                        {level}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>


          <div className="mb-3 grid grid-cols-[1.05fr_0.95fr] gap-3">
            <Box className="p-3 rounded-2xl border border-violet-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(139,92,246,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-violet-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Dynamic Explainability Layer</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">Decision rationale engine</div>
                </div>
                <LiveIndicator label="EXPLAIN" tone="violet" />
              </div>

              <div className="grid gap-2 text-[11px]">
                {[
                  {
                    label: "Why system is under watch",
                    tone: "cyan",
                    text: riskFlags > 0
                      ? `${riskFlags} soft governance constraint(s) remain active, but no hard block is currently detected.`
                      : "No soft governance constraint detected; system remains operational."
                  },
                  {
                    label: "Why execution is constrained",
                    tone: "amber",
                    text: actionPolicy.includes("SIMULATED")
                      ? `${actionPolicy} policy prevents real order routing while preserving monitoring and simulated execution.`
                      : `Execution policy is currently ${actionPolicy}.`
                  },
                  {
                    label: "Why drift is acceptable",
                    tone: "cyan",
                    text: "Allocator deviations are classified as governed drift because PREPROD policy and manual funding constraints remain active."
                  },
                  {
                    label: "Why offensive exposure remains active",
                    tone: regime === "risk_on" ? "emerald" : "slate",
                    text: regime === "risk_on"
                      ? "Risk-on regime keeps offensive equities and crypto allocation eligible under governance supervision."
                      : "Offensive exposure is monitored because the current regime does not fully support aggressive allocation."
                  }
                ].map((item, idx) => {
                  const tone =
                    item.tone === "emerald"
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                      : item.tone === "amber"
                        ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                        : item.tone === "cyan"
                          ? "border-cyan-500/25 bg-cyan-500/10 text-cyan-300"
                          : "border-slate-500/25 bg-slate-500/10 text-slate-300";

                  return (
                    <div key={idx} className={`rounded-xl border px-4 py-3 transition-all duration-300 hover:scale-[1.01] ${tone}`}>
                      <div className="text-[9px] uppercase tracking-widest opacity-70">{item.label}</div>
                      <div className="mt-1 text-[12px] leading-relaxed text-slate-200">{item.text}</div>
                    </div>
                  );
                })}
              </div>
            </Box>

            <Box className="p-3 rounded-2xl border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(16,185,129,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-emerald-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Decision Drivers</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Engine influence matrix</div>
                </div>
                <LiveIndicator label="DRIVERS" tone="emerald" />
              </div>

              <div className="grid gap-3">
                {[
                  ["Market Regime", marketRegimeScore, regime],
                  ["Governance Policy", governancePolicyScore, actionPolicy],
                  ["Risk Flags", riskFlagsScore, `${riskFlags} active flag(s)`],
                  ["Funding Constraint", fundingConstraintScore, global?.masterFundingManualApprovalRequired ? "manual inter-universe funding" : "funding clear"],
                  ["Execution Readiness", executionReadinessScore, hardBlock ? "blocked" : "audit ok"],
                ].map(([label, score, detail], idx) => {
                  const width = Math.max(5, Math.min(100, Number(score || 0)));
                  const color =
                    width >= 80
                      ? "bg-emerald-400"
                      : width >= 60
                        ? "bg-cyan-400"
                        : width >= 40
                          ? "bg-amber-300"
                          : "bg-red-400";

                  return (
                    <div key={idx}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-200">{label}</span>
                        <span className="text-slate-500">{detail}</span>
                      </div>
                      <div className="h-1.5 rounded bg-[#172231]">
                        <div className={`h-1.5 rounded ${color}`} style={{ width: `${width}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>

          
          
          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 overflow-hidden rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_50px_rgba(34,211,238,0.06)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Portfolio Brain Map</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Neural orchestration topology</div>
                </div>
                <LiveIndicator label="BRAIN LIVE" tone="cyan" />
              </div>

              <div className="relative h-[420px] overflow-hidden rounded-2xl border border-[#172231] bg-[radial-gradient(circle_at_center,#0f1d2e_0%,#09111b_65%)]">
                <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] [background-size:42px_42px]" />
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-cyan-400/5 blur-3xl" />

                {/* CONNECTION LINES */}

                <div className="absolute left-[50%] top-[22%] h-[2px] w-[240px] -translate-x-1/2 bg-cyan-400/40" />
                <div className="absolute left-[50%] top-[50%] h-[2px] w-[340px] -translate-x-1/2 bg-cyan-400/20" />
                <div className="absolute left-[50%] top-[78%] h-[2px] w-[240px] -translate-x-1/2 bg-cyan-400/30" />

                <div className="absolute left-[50%] top-[22%] h-[120px] w-[2px] -translate-x-1/2 bg-cyan-400/30" />
                <div className="absolute left-[50%] top-[50%] h-[120px] w-[2px] -translate-x-1/2 bg-cyan-400/20" />

                {[
                  {
                    label: "Market Regime",
                    x: "42%",
                    y: "8%",
                    tone: "emerald",
                    status: "risk_on"
                  },
                  {
                    label: "Governance",
                    x: "18%",
                    y: "34%",
                    tone: "amber",
                    status: "SIMULATED_ONLY"
                  },
                  {
                    label: "Risk Engine",
                    x: "66%",
                    y: "34%",
                    tone: "cyan",
                    status: "1 flag"
                  },
                  {
                    label: "Portfolio Engine",
                    x: "42%",
                    y: "42%",
                    tone: "emerald",
                    status: "allocator active"
                  },
                  {
                    label: "Funding Layer",
                    x: "16%",
                    y: "70%",
                    tone: "amber",
                    status: "manual bridge"
                  },
                  {
                    label: "Execution",
                    x: "68%",
                    y: "70%",
                    tone: "cyan",
                    status: "audit ok"
                  },
                  {
                    label: "Options Shadow",
                    x: "42%",
                    y: "82%",
                    tone: "emerald",
                    status: "isolated"
                  }
                ].map((node, idx) => {

                  const tone =
                    node.tone === "emerald"
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      : node.tone === "amber"
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                        : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";

                  return (
                    <div
                      key={idx}
                      className={`absolute w-[155px] -translate-x-1/2 rounded-2xl border px-4 py-3 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] ${tone}`}
                      style={{
                        left: node.x,
                        top: node.y
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-[11px] font-semibold uppercase tracking-wide">
                          {node.label}
                        </div>

                        <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-80" />
                      </div>

                      <div className="mt-2 text-[12px] opacity-80">
                        {node.status}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>
          <div className="mb-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-r from-[#071018] via-[#0a1724] to-[#071018] px-4 py-3 shadow signals-[0_0_50px_rgba(34,211,238,0.05)]">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-cyan-100">
                    Capital Intelligence Layer
                  </div>
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Allocation orchestration · confidence matrix · funding constraints
                </div>
              </div>

              <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
                <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-1 text-cyan-300">Allocator Active</span>
                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">Funding Governed</span>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-emerald-300">Confidence Online</span>
              </div>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-[1.15fr_0.85fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Capital Allocation Intelligence</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Allocator orchestration engine</div>
                </div>
                <LiveIndicator label="ALLOCATOR" tone="cyan" />
              </div>

              <div className="grid gap-3">
                {[
                  {
                    label: "Capital Rotation",
                    value: "Offensive allocation maintained",
                    tone: "emerald",
                    detail: "Risk-on regime keeps offensive engines prioritized."
                  },
                  {
                    label: "Funding Constraint",
                    value: "Manual inter-universe transfer",
                    tone: "amber",
                    detail: "Crypto ↔ IBKR funding remains manually governed."
                  },
                  {
                    label: "Allocator Pressure",
                    value: "Moderate",
                    tone: "cyan",
                    detail: "Defensive reduction requests remain monitored."
                  },
                  {
                    label: "Rebalance Status",
                    value: "Governed Drift Accepted",
                    tone: "cyan",
                    detail: "Deviation classified as intentional PREPROD drift."
                  }
                ].map((item, idx) => {

                  const tone =
                    item.tone === "emerald"
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                      : item.tone === "amber"
                        ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                        : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                  return (
                    <div key={idx} className={`rounded-xl border px-4 py-3 transition-all duration-300 hover:scale-[1.01] ${tone}`}>
                      <div className="flex items-center justify-between">
                        <div className="text-[10px] uppercase tracking-widest opacity-70">
                          {item.label}
                        </div>

                        <div className="text-[11px] font-semibold">
                          {item.value}
                        </div>
                      </div>

                      <div className="mt-2 text-[12px] text-slate-300">
                        {item.detail}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>

            <Box className="p-3 rounded-2xl border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(16,185,129,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-emerald-400/20">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Allocator Confidence Matrix</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Dynamic confidence scoring</div>
                </div>
                <LiveIndicator label="CONFIDENCE" tone="emerald" />
              </div>

              <div className="space-y-3">
                {[
                  ["Crypto", Math.round(pamConfidencePct("crypto", getBrickConfidence("crypto", confidence, pt, bricks) * 100))],
                  ["Offensive Equities", Math.round(pamConfidencePct("equities_offensive", getBrickConfidence("equities_offensive", confidence, pt, bricks) * 100))],
                  ["Defensive Equities", Math.round(pamConfidencePct("equities_defensive", getBrickConfidence("equities_defensive", confidence, pt, bricks) * 100))],
                  ["Bonds", Math.round(pamConfidencePct("bonds", getBrickConfidence("bonds", confidence, pt, bricks) * 100))],
                  ["Precious Metals", Math.round(pamConfidencePct("precious_metals", getBrickConfidence("precious_metals", confidence, pt, bricks) * 100))],
                  ["Options Shadow", Math.round(pamConfidencePct("options_v2_shadow", getBrickConfidence("options_v2_shadow", confidence, pt, bricks) * 100))]
                ].map(([label, score], idx) => {

                  const width = Math.max(5, Math.min(100, Number(score)));

                  const color =
                    width >= 85
                      ? "bg-emerald-400"
                      : width >= 70
                        ? "bg-cyan-400"
                        : width >= 55
                          ? "bg-amber-300"
                          : "bg-red-400";

                  return (
                    <div key={idx}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-200">{label}</span>
                        <span className="text-slate-500">{score}%</span>
                      </div>

                      <div className="h-1.5 rounded bg-[#172231]">
                        <div
                          className={`h-1.5 rounded ${color}`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>


          
          
          
          

          <div className="mb-4 rounded-2xl border border-[#1f2a37] bg-gradient-to-r from-[#07101a]/95 via-[#091522]/95 to-[#07101a]/95 px-4 py-3 shadow signals-[0_0_28px_rgba(34,211,238,0.08)]">
            
          


          


<div className="grid grid-cols-[1fr_0.75fr_0.85fr_0.7fr_0.8fr_0.7fr] items-center gap-3 text-[11px]">
              <div>
                <div className="text-[9px] uppercase tracking-widest text-cyan-300/60">NSC War Room Status</div>
                <div className="mt-1 flex items-center gap-2 text-[13px] font-semibold text-white">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow signals-[0_0_10px_rgba(16,185,129,0.8)]" />
                  Control System Online · PREPROD
                </div>
              </div>

              {[
                ["Regime", regime === "risk_on" ? "Risk-On" : regime === "risk_off" ? "Risk-Off" : "Neutral", "emerald"],
                ["Governance", actionPolicy, "amber"],
                ["Risk Flags", `${riskFlags}`, riskFlags > 0 ? "cyan" : "emerald"],
                ["Execution", hardBlock ? "Blocked" : "Simulated", hardBlock ? "red" : "cyan"],
                ["Mode", "PREPROD", "cyan"],
              ].map(([label, value, tone], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                    : tone === "amber"
                      ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                      : tone === "red"
                        ? "border-red-500/25 bg-red-500/10 text-red-300"
                        : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                return (
                  <div key={idx} className={`rounded-xl border px-3 py-2 transition-all duration-300 hover:scale-[1.015] ${cls}`}>
                    <div className="text-[9px] uppercase tracking-widest opacity-70">{label}</div>
                    <div className="mt-1 truncate text-[12px] font-semibold text-slate-100">{value}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mb-3 grid grid-cols-[1.05fr_0.95fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Event Fabric Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Realtime orchestration streams</div>
  </div>
  <LiveIndicator label="STREAMS" tone="cyan" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-cyan-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow signals-[0_0_10px_rgba(34,211,238,0.75)]" />
                  event fabric online
                </div>
              </div>

              <div className="grid gap-2 text-[11px]">
                {[
                  ["AI Core", "Meta-score consensus propagated to allocator", "INFO"],
                  ["Signal Quality", "Eligible signal cluster remains coherent", "OK"],
                  ["Risk Engine", riskFlags > 0 ? `${riskFlags} soft governance constraint(s) injected into governance context` : "No soft governance constraint propagated", riskFlags > 0 ? "WATCH" : "OK"],
                  ["Governance", "PREPROD lock overrides live execution path", "WATCH"],
                  ["Allocator", "Capital rotation kept in offensive bias", "INFO"],
                  ["Execution", "Order routing remains simulated and audited", "OK"],
                  ["Funding", "Manual cross-universe bridge constraint broadcast", "WATCH"],
                ].map(([source, event, level], idx) => {
                  const tone =
                    level === "WATCH"
                      ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                      : level === "OK"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-slate-500/30 bg-slate-500/10 text-slate-300";

                  return (
                    <div key={idx} className="grid grid-cols-[0.8fr_1.8fr_0.45fr] items-center gap-3 rounded-xl border border-[#172231] bg-[#0d1520] px-3 py-2 transition-all duration-300 hover:border-cyan-500/25 hover:bg-[#101b29]">
                      <div className="flex items-center gap-2 font-semibold text-slate-200">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                        {source}
                      </div>
                      <div className="truncate text-slate-400">{event}</div>
                      <span className={`justify-self-end rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${tone}`}>
                        {level}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Box>

            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Event Fabric Health</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Realtime synchronization health</div>
  </div>
  <LiveIndicator label="FABRIC" tone="emerald" />
</div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500">distributed engine state</div>
              </div>

              <div className="grid gap-3">
                {[
                  ["Event Throughput", 87, "stable"],
                  ["Propagation Delay", 92, "low"],
                  ["Engine Coherence", 86, "high"],
                  ["Governance Override", Math.round(Number(global?.confidencePct ?? 0)), global?.governanceMode || "active"],
                  ["Risk Injection", riskFlags > 0 ? 66 : 91, riskFlags > 0 ? "watch" : "clean"],
                  ["Execution Isolation", 94, "enforced"],
                ].map(([label, score, detail], idx) => {
                  const width = Math.max(5, Math.min(100, Number(score)));
                  const color =
                    width >= 85
                      ? "bg-emerald-400"
                      : width >= 70
                        ? "bg-cyan-400"
                        : width >= 55
                          ? "bg-amber-300"
                          : "bg-red-400";

                  return (
                    <div key={idx}>
                      <div className="mb-1 flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-200">{label}</span>
                        <span className="text-slate-500">{detail}</span>
                      </div>
                      <div className="h-1.5 rounded bg-[#172231]">
                        <div className={`h-1.5 rounded ${color} shadow signals-[0_0_10px_rgba(34,211,238,0.25)]`} style={{ width: `${width}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-[12px] leading-relaxed text-slate-300">
                The event fabric synchronizes AI, risk, governance, allocation and execution states. PREPROD governance remains the dominant override protecting live execution paths.
              </div>
            </Box>
          </div>
<div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 overflow-hidden">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Neural Orchestration Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">AI consensus and orchestration mesh</div>
  </div>
  <LiveIndicator label="AI CORE" tone="violet" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-emerald-400">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow signals-[0_0_10px_rgba(16,185,129,0.8)]" />
                  AI orchestration mesh active
                </div>
              </div>

              <div className="grid grid-cols-[1.05fr_0.95fr] gap-3">
                <div className="relative h-[430px] overflow-hidden rounded-2xl border border-[#172231] bg-[radial-gradient(circle_at_center,#0f1d2e_0%,#09111b_68%)] p-4">
                  <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] [background-size:38px_38px]" />
                  <div className="pointer-events-none absolute left-1/2 top-1/2 h-56 w-56 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-emerald-400/5 blur-3xl" />

                  <div className="absolute left-[50%] top-[50%] h-[2px] w-[520px] -translate-x-1/2 bg-cyan-400/20" />
                  <div className="absolute left-[50%] top-[50%] h-[300px] w-[2px] -translate-y-1/2 bg-cyan-400/20" />
                  <div className="absolute left-[50%] top-[50%] h-[2px] w-[360px] -translate-x-1/2 rotate-45 bg-cyan-400/15" />
                  <div className="absolute left-[50%] top-[50%] h-[2px] w-[360px] -translate-x-1/2 -rotate-45 bg-cyan-400/15" />

                  {[
                    ["Meta-Score Engine", `${metaScoreValue}/100`, metaScoreValue >= 80 ? "emerald" : metaScoreValue >= 60 ? "amber" : "red", "50%", "42%"],
                    ["Signal Quality", signalQualityScore >= 80 ? "high" : signalQualityScore >= 60 ? "watch" : "low", signalQualityScore >= 80 ? "emerald" : signalQualityScore >= 60 ? "amber" : "red", "24%", "18%"],
                    ["Risk Consensus",
riskConsensusScore >= 80 ? "clear" : riskConsensusScore >= 60 ? "watch" : "critical",
riskConsensusScore >= 80 ? "emerald" : riskConsensusScore >= 60 ? "amber" : "red",
"76%", "18%"],
                    ["Strategy Selector", regime === "risk_on" ? "risk-on bias" : regime === "risk_off" ? "defensive bias" : "neutral bias", "cyan", "24%", "70%"],
                    ["Governance AI",
actionPolicy,
governanceConfidenceScore >= 80 ? "emerald" : "amber",
"76%", "70%"],
                    ["Execution Consensus",
global?.globalAuditStatus || "UNKNOWN",
(global?.globalAuditStatus === "OK" ? "emerald" : "amber"),
"50%",
`${globalConfidenceScore}%`],
                    ["Narrative Engine", global?.orchestrationStatus === "OK" ? "coherent" : "watch", global?.orchestrationStatus === "OK" ? "emerald" : "amber", "50%", "10%"],
                  ].map(([label, value, tone, x, y], idx) => {
                    const cls =
                      tone === "emerald"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : tone === "amber"
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                          : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";

                    return (
                      <div
                        key={idx}
                        className={`absolute w-[155px] -translate-x-1/2 rounded-2xl border px-4 py-3 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_24px_rgba(34,211,238,0.12)] ${cls}`}
                        style={{ left: x, top: y }}
                      >
                        <div className="flex items-center justify-between">
                          <div className="text-[10px] font-semibold uppercase tracking-wide">{label}</div>
                          <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-80" />
                        </div>
                        <div className="mt-2 text-[12px] opacity-85">{value}</div>
                      </div>
                    );
                  })}
                </div>

                <div className="rounded-2xl border border-[#172231] bg-[#0d1520] p-4">
                  <div className="mb-3 text-[10px] uppercase tracking-widest text-slate-500">
                    AI Consensus Matrix
                  </div>

                  <div className="space-y-3">
                    {[
                      ["Meta-Score Consensus", metaScoreValue, regime === "risk_on" ? "Risk-on allocation coherent" : "Allocation posture governed"],
                      ["Signal Quality", signalQualityScore, "Eligible under governance"],
                      ["Risk Consensus", riskConsensusScore, riskFlags > 0 ? "Watch posture maintained" : "Risk filters clear"],
                      ["Governance Confidence", governanceConfidenceScore, "Policy layer enforced"],
                      ["Execution Readiness", executionReadinessScore, "Audit OK / simulated"],
                      ["Narrative Coherence", narrativeCoherenceScore, "Decision rationale aligned"],
                    ].map(([label, score, detail], idx) => {
                      const width = Math.max(5, Math.min(100, Number(score)));
                      const color =
                        width >= 82
                          ? "bg-emerald-400"
                          : width >= 65
                            ? "bg-cyan-400"
                            : width >= 50
                              ? "bg-amber-300"
                              : "bg-red-400";

                      return (
                        <div key={idx}>
                          <div className="mb-1 flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-slate-200">{label}</span>
                            <span className="text-slate-500">{score}%</span>
                          </div>
                          <div className="h-1.5 rounded bg-[#172231]">
                            <div className={`h-1.5 rounded ${color} shadow signals-[0_0_10px_rgba(34,211,238,0.25)]`} style={{ width: `${width}%` }} />
                          </div>
                          <div className="mt-1 text-[10px] text-slate-500">{detail}</div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-[12px] leading-relaxed text-slate-300">
                    The AI core validates that allocation, governance, risk and execution layers remain coherent. The system can observe and simulate decisions, but PREPROD policy prevents live order routing.
                  </div>
                </div>
              </div>
            </Box>
          </div>
<div className="mb-3 grid grid-cols-[1.05fr_0.95fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Macro & Regime Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Macro state and regime supervision</div>
  </div>
  <LiveIndicator label="REGIME" tone="emerald" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-emerald-400">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow signals-[0_0_10px_rgba(16,185,129,0.8)]" />
                  regime engine active
                </div>
              </div>

              <div className="grid gap-3">
                {[
                  ["Market Regime", regime === "risk_on" ? "Risk-On" : regime === "risk_off" ? "Risk-Off" : "Neutral", marketRegimeScore, regime === "risk_on" ? "emerald" : regime === "risk_off" ? "amber" : "cyan"],
                  ["Liquidity Pulse", liquidityPulseState, liquidityPulseScore, "cyan"],
                  ["Volatility State", volatilityStateLabel, volatilityStateScore, "cyan"],
                  ["Correlation Regime", correlationRegimeLabel, correlationRegimeScore, "amber"],
                  ["Systemic Stress", systemicStressLabel, systemicStressScore, systemicStressScore >= 70 ? "amber" : "cyan"],
                  ["Cross-Asset Friction", crossAssetFrictionLabel, crossAssetFrictionScore, crossAssetFrictionScore >= 80 ? "emerald" : "amber"],
                ].map(([label, state, score, tone], idx) => {
                  const width = Math.max(5, Math.min(100, Number(score)));

                  const bar =
                    tone === "emerald"
                      ? "bg-emerald-400"
                      : tone === "amber"
                        ? "bg-amber-300"
                        : "bg-cyan-400";

                  const chip =
                    tone === "emerald"
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                      : tone === "amber"
                        ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                        : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                  return (
                    <div key={idx} className="rounded-xl border border-[#172231] bg-[#0d1520] px-4 py-3 transition-all duration-300 hover:border-cyan-500/25 hover:bg-[#101b29]">
                      <div className="mb-2 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
                          <div className="mt-1 text-[13px] font-semibold text-slate-100">{state}</div>
                        </div>
                        <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold ${chip}`}>
                          {score}/100
                        </span>
                      </div>

                      <div className="h-1.5 rounded bg-[#172231]">
                        <div className={`h-1.5 rounded ${bar} shadow signals-[0_0_10px_rgba(34,211,238,0.25)]`} style={{ width: `${width}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>

            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Regime Narrative</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">Macro story synthesis</div>
                </div>
                <LiveIndicator label="NARRATIVE" tone="violet" />
                <div className="text-[10px] uppercase tracking-widest text-slate-500">macro explanation</div>
              </div>

              <div className="grid gap-3 text-[12px] leading-relaxed">
                <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-slate-200">
                  <div className="mb-1 text-[10px] uppercase tracking-widest text-emerald-300">Current Interpretation</div>
                  NSC reads the current environment as supportive enough to preserve offensive allocation while keeping governance supervision active.
                </div>

                <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-4 py-3 text-slate-200">
                  <div className="mb-1 text-[10px] uppercase tracking-widest text-cyan-300">Allocation Consequence</div>
                  Crypto and offensive equities remain eligible, while defensive sleeves, bonds and metals stay monitored through allocator constraints.
                </div>

                <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-slate-200">
                  <div className="mb-1 text-[10px] uppercase tracking-widest text-amber-300">Risk Interpretation</div>
                  One soft governance constraint and manual cross-universe funding justify a WATCH posture rather than unrestricted execution.
                </div>

                <div className="rounded-xl border border-[#172231] bg-[#0d1520] px-4 py-3 text-slate-300">
                  <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Operating Mode</div>
                  The system remains in PREPROD governance: decisions are observable, explainable and simulated before any production activation.
                </div>
              </div>
            </Box>
          </div>

          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Systemic Risk Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">Cross-asset systemic supervision</div>
  </div>
  <LiveIndicator label="SYSTEMIC" tone="amber" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-cyan-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow signals-[0_0_10px_rgba(34,211,238,0.75)]" />
                  systemic layer active
                </div>
              </div>

              <div className="grid grid-cols-[1.05fr_0.95fr] gap-3">
                <div className="rounded-2xl border border-[#172231] bg-[#0d1520] p-4">
                  <div className="mb-3 text-[10px] uppercase tracking-widest text-slate-500">
                    Cross-Asset Risk Matrix
                  </div>

                  <div className="grid grid-cols-4 gap-2 text-[11px]">
                    {[
                      ["Volatility", volatilityStateLabel, "cyan"],
                      ["Liquidity", liquidityPulseState, "cyan"],
                      ["Correlation", correlationRegimeLabel, "amber"],
                      ["Stress", systemicStressLabel, systemicStressScore >= 70 ? "amber" : "cyan"],
                      ["Flow Of Funds", manualFundingRequired ? "Manual" : "Clear", manualFundingRequired ? "amber" : "emerald"],
                      ["Info Imbalance", global?.globalAuditStatus === "OK" ? "Controlled" : "Watch", global?.globalAuditStatus === "OK" ? "cyan" : "amber"],
                      ["Market Stability", marketStabilityLabel, marketStabilityTone],
                      ["System Coherence", systemCoherenceLabel, systemCoherenceTone],
                    ].map(([label, value, tone], idx) => {
                      const cls =
                        tone === "emerald"
                          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                          : tone === "amber"
                            ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                            : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                      return (
                        <div key={idx} className={`rounded-xl border px-3 py-3 transition-all duration-300 hover:scale-[1.02] ${cls}`}>
                          <div className="text-[9px] uppercase tracking-widest opacity-70">{label}</div>
                          <div className="mt-1 text-[13px] font-semibold text-slate-100">{value}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="rounded-2xl border border-[#172231] bg-[#0d1520] p-4">
                  <div className="mb-3 text-[10px] uppercase tracking-widest text-slate-500">
                    Systemic Stress Radar
                  </div>

                  <div className="space-y-3">
                    {[
                      ["Volatility State Machine", volatilityStateScore, volatilityStateLabel],
                      ["Liquidity Migration", liquidityPulseScore, liquidityPulseState],
                      ["Correlation Heat", correlationRegimeScore, correlationRegimeLabel],
                      ["Market Pressure", systemicStressScore, systemicStressLabel],
                      ["Risk Concentration", riskConsensusScore, riskFlags > 0 ? "Watch" : "Controlled"],
                      ["System Coherence", systemCoherenceScore, systemCoherenceLabel],
                    ].map(([label, score, state], idx) => {
                      const width = Math.max(5, Math.min(100, Number(score)));
                      const color =
                        width >= 80
                          ? "bg-emerald-400"
                          : width >= 65
                            ? "bg-cyan-400"
                            : width >= 50
                              ? "bg-amber-300"
                              : "bg-red-400";

                      return (
                        <div key={idx}>
                          <div className="mb-1 flex items-center justify-between text-[11px]">
                            <span className="font-semibold text-slate-200">{label}</span>
                            <span className="text-slate-500">{state}</span>
                          </div>
                          <div className="h-1.5 rounded bg-[#172231]">
                            <div className={`h-1.5 rounded ${color} shadow signals-[0_0_10px_rgba(34,211,238,0.25)]`} style={{ width: `${width}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="mt-3 rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-[12px] leading-relaxed text-slate-300">
                Cross-asset conditions remain coherent enough to support monitored risk-on exposure, while correlation and systemic stress indicators justify maintaining governance in WATCH mode.
              </div>
            </Box>
          </div>
<div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Market Session Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-sky-300/70">Global session intelligence</div>
  </div>
  <LiveIndicator label="SESSION" tone="cyan" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-cyan-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow signals-[0_0_10px_rgba(34,211,238,0.75)]" />
                  market clock live
                </div>
              </div>

              <div className="grid grid-cols-[0.9fr_0.9fr_0.9fr_0.9fr_1.1fr_1.1fr] gap-3">
                {[
                  ["UTC", marketSession.utc, "cyan"],
                  ["Paris", marketSession.paris, "emerald"],
                  ["New York", marketSession.ny, "cyan"],
                  ["Tokyo", marketSession.tokyo, "cyan"],
                  ["US Session", marketSession.usSession, marketSession.usSession === "US Market Open" ? "emerald" : "amber"],
                  ["Crypto Intensity", marketSession.cryptoIntensity, marketSession.cryptoIntensity === "High" ? "emerald" : marketSession.cryptoIntensity === "Moderate" ? "cyan" : "amber"],
                ].map(([label, value, tone], idx) => {
                  const cls =
                    tone === "emerald"
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                      : tone === "amber"
                        ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                        : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                  return (
                    <div key={idx} className={`rounded-xl border px-3 py-3 transition-all duration-300 hover:scale-[1.015] ${cls}`}>
                      <div className="text-[9px] uppercase tracking-widest opacity-70">{label}</div>
                      <div className="mt-1 text-[13px] font-semibold text-slate-100">{value}</div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 rounded-xl border border-[#172231] bg-[#0d1520] px-4 py-3 text-[12px] text-slate-300">
                Market session context is used as an execution and monitoring overlay. Crypto remains continuously observable, while equities-related decisions remain sensitive to US session state.
              </div>
            </Box>
          </div>
<div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Capital Flow Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Funding and allocation flows</div>
  </div>
  <LiveIndicator label="FLOW" tone="cyan" />
</div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-cyan-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow signals-[0_0_10px_rgba(34,211,238,0.75)]" />
                  allocator flow monitored
                </div>
              </div>

              <div className="grid grid-cols-[1.15fr_0.85fr] gap-3">
                <div className="rounded-2xl border border-[#172231] bg-[#0d1520] p-4">
                  <div className="mb-3 grid grid-cols-3 gap-2 text-[10px]">
                    {[
                      ["Crypto", pamCapitalGapPct("crypto")],
                      ["Offensive", pamCapitalGapPct("equities_offensive")],
                      ["Defensive", pamCapitalGapPct("equities_defensive")],
                      ["Bonds", pamCapitalGapPct("bonds")],
                      ["Metals", pamCapitalGapPct("precious_metals")],
                      ["Options", pamCapitalGapPct("options_v2_shadow")],
                    ].map(([label, gap]) => (
                      <div key={label} className="rounded-xl border border-[#1f2a37] bg-[#08111a] px-3 py-2">
                        <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">{label}</div>
                        <div className={`mt-1 text-sm font-semibold ${Math.abs(Number(gap)) >= 10 ? "text-amber-300" : "text-emerald-300"}`}>
                          {Number(gap) >= 0 ? "+" : ""}{Number(gap).toFixed(2)} pts
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mb-4 grid grid-cols-[1fr_0.45fr_1fr] items-center gap-3 text-[11px]">
                    {[
                      ["Offensive Sleeve", pct(pamCapitalPct("equities_offensive", Number(weights?.offensive_equities ?? weights?.offensive ?? 0))), "emerald"],
                      ["Defensive Sleeve", pct(pamCapitalPct("equities_defensive", Number(weights?.defensive_equities ?? weights?.defensive ?? 0))), "cyan"],
                      ["Bonds Sleeve", pct(pamCapitalPct("bonds", Number(weights?.bonds ?? weights?.obligations ?? 0))), "cyan"],
                      ["Precious Metals", pct(pamCapitalPct("precious_metals", Number(weights?.precious_metals ?? weights?.metals ?? 0))), "amber"],
                      ["Crypto Sleeve", pct(pamCapitalPct("crypto", Number(weights?.crypto ?? 0))), "emerald"],
                      ["Cash Buffer", `${pamCashBufferPct.toFixed(1)}%`, "cyan"],
                    ].map(([label, value, tone], idx) => {
                      const bar =
                        tone === "emerald"
                          ? "bg-emerald-400"
                          : tone === "amber"
                            ? "bg-amber-300"
                            : "bg-cyan-400";

                      return (
                        <div key={idx} className="contents">
                          <div className="rounded-xl border border-[#1f2a37] bg-[#09111a] px-3 py-2">
                            <div className="text-[9px] uppercase tracking-widest text-slate-500">{label}</div>
                            <div className="mt-1 text-[13px] font-semibold text-slate-100">{value}</div>
                          </div>

                          <div className="relative h-1 rounded bg-[#172231]">
                            <div className={`absolute left-0 top-0 h-1 animate-pulse rounded ${bar} shadow signals-[0_0_10px_rgba(34,211,238,0.45)]`} style={{ width: `${Math.max(0, Math.min(100, Math.round(Number(global?.confidencePct ?? 0))))}%` }} />
                          </div>

                          <div className="text-[11px] text-slate-400">
                            {idx === 0 ? "Risk-on allocation preserved" :
                             idx === 1 ? "Stabilization exposure monitored" :
                             idx === 2 ? "Macro cushion under allocator review" :
                             idx === 3 ? "Systemic hedge active but governed" :
                             idx === 4 ? "Crypto sleeve active under PREPROD" :
                             "Liquidity reserve monitored"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="rounded-2xl border border-[#172231] bg-[#0d1520] p-4">
                  <div className="mb-3 text-[10px] uppercase tracking-widest text-slate-500">
                    Capital Flow Summary
                  </div>

                  <div className="grid gap-3">
                    {[
                      ["Rotation Bias", "Offensive", "emerald"],
                      ["Funding Stress", "Moderate", "amber"],
                      ["Rebalance Priority", "Governed", "cyan"],
                      ["Execution State", "Simulated", "cyan"],
                      ["Cross-Universe Bridge", "Manual", "amber"],
                    ].map(([label, value, tone], idx) => {
                      const cls =
                        tone === "emerald"
                          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                          : tone === "amber"
                            ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
                            : "border-cyan-500/25 bg-cyan-500/10 text-cyan-300";

                      return (
                        <div key={idx} className={`rounded-xl border px-3 py-2 transition-all duration-300 hover:scale-[1.01] ${cls}`}>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase tracking-widest opacity-70">{label}</span>
                            <span className="text-[12px] font-semibold">{value}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-3 text-[12px] leading-relaxed text-slate-300">
                    Manual funding governance remains enforced: no automatic capital bridge between crypto venues and IBKR pool.
                  </div>
                </div>
              </div>
            </Box>
          </div>
<div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div className="flex items-start justify-between">
  <div>
    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Allocator Drift Layer</div>
    <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">Governed drift intelligence</div>
  </div>
  <LiveIndicator label="DRIFT" tone="amber" />
</div>

              <div className="grid grid-cols-[1fr_0.55fr_0.55fr_0.65fr_0.95fr_1.1fr] border-b border-[#1f2a37] pb-2 text-[10px] uppercase text-slate-500">
                <div>Brick</div>
                <div>Target</div>
                <div>Current</div>
                <div>Drift</div>
                <div>Intelligence</div>
                <div>Drift Bar</div>
              </div>

              {allocatorDriftRows.map((row) => {

                const driftIntel = getDriftIntelligence(row, { action_policy: actionPolicy });

                const driftTone =
                  driftIntel.type === "critical_drift"
                    ? "text-red-400"
                    : driftIntel.type === "monitored_drift" || driftIntel.type === "intentional_drift"
                      ? "text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]"
                      : "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]";

                const barWidth = Math.max(2, Math.min(100, row.absDrift * 1000));

                return (
                  <div key={row.key} className="grid grid-cols-[1fr_0.55fr_0.55fr_0.65fr_0.95fr_1.1fr] items-center border-b border-[#172231] py-2 text-[11px]">
                    <div className="font-semibold text-slate-200">{humanBrickName(row.key)}</div>
                    <div>{pct(row.target)}</div>
                    <div>{pct(row.current)}</div>
                    <div className={driftTone}>{pct(row.drift)}</div>
                    <div>
                      <DriftBadge row={row} governance={{ action_policy: actionPolicy }} />
                    </div>
                    <div>
                      <div className="h-1.5 rounded bg-[#172231]">
                        <div
                          className={`h-1.5 rounded ${
                            driftIntel.type === "critical_drift"
                              ? "bg-red-400"
                              : driftIntel.type === "monitored_drift" || driftIntel.type === "intentional_drift"
                                ? "bg-cyan-400"
                                : "bg-emerald-400"
                          }`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                      <div className="mt-1 text-[9px] text-slate-500">
                        Threshold {pct(row.threshold)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </Box>
          </div>

          
          <div className="mb-3 grid grid-cols-1 gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">System Health Score</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Global platform health</div>
                </div>
                <LiveIndicator label="HEALTH" tone="emerald" />

              <div className="mt-4 flex items-center justify-between">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">
                    Global System Integrity
                  </div>

                  <div className="mt-2 text-5xl font-bold text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]">
                    91
                    <span className="ml-1 text-2xl text-slate-500">/100</span>
                  </div>
                </div>

                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-[13px] font-semibold text-emerald-300">
                  HEALTHY
                </div>
              </div>

              <div className="mt-5">
                <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-500" style={{ width: `${riskFlagsScore}%` }}></div>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 xl:grid-cols-4 gap-3">

                {[
                  ["Governance", `${Math.round(Number(productionReadiness?.governance_score ?? productionScore ?? 0))}%`, hardBlock ? "BLOCKED" : "OK"],
                  ["Execution", `${Math.round(Number(productionReadiness?.execution_score ?? productionReadiness?.execution_quality_score ?? productionScore ?? 0))}%`, actionPolicy.includes("SIMULATED") ? "WATCH" : "OK"],
                  ["Risk", `${riskFlagsScore}%`, riskFlags > 0 ? "WATCH" : "OK"],
                  ["API", `${Math.round(Number(dynamicMetricsAudit?.api_score ?? dynamicMetricsAudit?.score ?? (global.apiStatus === "OK" ? 100 : 0)))}%`, global.apiStatus === "OK" ? "OK" : "WATCH"],
                ].map(([label, value, state]) => (
                  <div
                    key={label}
                    className="rounded-xl border border-[#1f2a37] bg-[#081120] px-3 py-3"
                  >
                    <div className="text-[10px] uppercase tracking-wide text-slate-500">
                      {label}
                    </div>

                    <div className="mt-2 flex items-center justify-between">
                      <div className="text-lg font-semibold text-white">
                        {value}
                      </div>

                      <div className={`text-[10px] font-semibold ${
                        state === "OK"
                          ? "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]"
                          : "text-cyan-400"
                      }`}>
                        {state}
                      </div>
                    </div>
                  </div>
                ))}

              </div>
            </Box>
          </div>

<div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Status Matrix</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">Policy and veto supervision</div>
                </div>
                <LiveIndicator label="GOVERNANCE" tone="amber" />

              <div className="grid grid-cols-[1.1fr_0.65fr_0.9fr_1fr_0.7fr] border-b border-[#1f2a37] pb-2 text-[10px] uppercase text-slate-500">
                <div>Layer</div>
                <div>Status</div>
                <div>Mode</div>
                <div>Signal</div>
                <div>Check</div>
              </div>

              {[
                ["Portfolio Engine", "OK", String(regime).toUpperCase(), "Target allocation computed", "T-00"],
                ["Risk Engine", riskFlags > 0 ? "WATCH" : "OK", riskFlags > 0 ? "SOFT CONSTRAINTS" : "CLEAR", riskFlags > 0 ? `${riskFlags} soft governance constraint(s)` : "No soft governance constraint", "T-01"],
                ["Governance", hardBlock ? "BLOCKED" : "WATCH", actionPolicy, hardBlock ? "Hard block active" : "Policy enforced", "T-02"],
                ["Execution Engine", executionEngineStatus, allowSimulatedExecution ? "SIMULATED" : "IDLE", `${activeEntryOrders} entry / ${exitOrders} exit / ${shadowSignals} shadow signals signals`, "T-03"],
                ["Policy Layer", "WATCH", actionPolicy, "No real order allowed", "T-04"],
                ["Funding Layer", fundingLayerStatus, fundingLayerMode, fundingLayerSignal, "T-05"],
                ["Options Shadow", "OK", "SHADOW", "Isolated from live execution", "T-06"],
                ["API Health", global.apiStatus === "OK" ? "OK" : "WATCH", global.apiStatus || "UNKNOWN", "Dashboard feed online", "LIVE"],
              ].map(([layer, status, mode, signal, check]) => {
                const cls =
                  status === "BLOCKED"
                    ? "text-red-400"
                    : status === "WATCH"
                      ? "text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]"
                      : "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.35)]";

                const badge =
                  status === "BLOCKED"
                    ? "border-red-500/30 bg-red-500/10 text-red-300"
                    : status === "WATCH"
                      ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]"
                      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

                return (
                  <div key={layer} className="grid grid-cols-[1.1fr_0.65fr_0.9fr_1fr_0.7fr] items-center border-b border-[#172231] py-2 text-[11px]">
                    <div className="font-semibold text-slate-200">{layer}</div>
                    <div>
                      <span className={`rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${badge}`}>
                        {status}
                      </span>
                    </div>
                    <div className={cls}>{mode}</div>
                    <div className="truncate text-slate-400">{signal}</div>
                    <div className="font-mono text-slate-500">{check}</div>
                  </div>
                );
              })}
            </Box>
          </div>

          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Funding Constraint Monitor</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Funding pools and manual constraints</div>
                </div>
                <LiveIndicator label="FUNDING" tone="cyan" />

              <div className="grid grid-cols-1 xl:grid-cols-4 gap-3">
                {[
                  ["IBKR Pool", "ACTIVE", "Equities / bonds / metals / options sleeve", "OK"],
                  ["Crypto Exchange Pool", "ACTIVE", "Crypto execution venue isolated", "OK"],
                  ["Cash Buffer", `${pamCashBufferPct.toFixed(1)}%`, "Liquidity reserve from PAM deployment", pamCashBufferPct < 10 ? "WATCH" : "OK"],
                  ["Cross-Universe Transfer", fundingLayerMode, fundingLayerSignal, fundingLayerStatus],
                ].map(([label, value, detail, status]) => {
                  const cls =
                    status === "WATCH"
                      ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

                  return (
                    <div key={label} className="rounded-xl border border-[#172231] bg-[#0d1520] p-3 transition-all duration-300 hover:border-cyan-500/20 hover:bg-[#101927]">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">
                          {label}
                        </div>

                        <span className={`rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${cls}`}>
                          {status}
                        </span>
                      </div>

                      <div className="mt-3 text-xl font-semibold text-white">
                        {value}
                      </div>

                      <div className="mt-1 text-[10px] text-slate-500">
                        {detail}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
                Manual funding governance remains enforced: no automatic transfer between crypto venues and IBKR pool.
              </div>
            </Box>
          </div>

          <div className="mb-3 grid grid-cols-[1fr] gap-3">
            <Box className="p-3 rounded-2xl border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow signals-[0_0_40px_rgba(34,211,238,0.05)] backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20">
              <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Execution Pipeline Monitor</div>
                  <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/70">Execution path and queue supervision</div>
                </div>
                <LiveIndicator label="PIPELINE" tone="emerald" />

              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7 gap-2 text-[11px]">
                {[
                  ["Signal Candidates", global.candidatesCount ?? 0, "OK", "Candidates before execution filtering"],
                  ["Portfolio", Object.keys(weights || {}).length, "OK", "Allocation target"],
                  ["Risk", riskFlags, riskFlags > 0 ? "WATCH" : "OK", "Risk filters"],
                  ["Governance", actionPolicy, actionPolicy.includes("SIMULATED") ? "WATCH" : "OK", "Policy gate"],
                  ["Execution Plan", simulatedOrdersCount, executionPlanStatus, simulatedOrderSymbols.length ? simulatedOrderSymbols.join(", ").toUpperCase() : "Orders retained in execution plan"],
                  ["Orders", `${activeEntryOrders}/${exitOrders}/${shadowSignals}`, ordersStatus, "Entry / Exit / Shadow Signals"],
                  ["Reconciliation", hardBlock ? "BLOCKED" : "OK", hardBlock ? "BLOCKED" : "OK", "State check"],
                ].map(([step, value, status, detail], idx) => {
                  const badge =
                    status === "BLOCKED"
                      ? "border-red-500/30 bg-red-500/10 text-red-300"
                      : status === "WATCH"
                        ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.30)]"
                        : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";

                  const dot =
                    status === "BLOCKED"
                      ? "bg-red-400"
                      : status === "WATCH"
                        ? "bg-cyan-400"
                        : "bg-emerald-400";

                  return (
                    <div key={step} className="relative rounded-xl border border-[#172231] bg-[#0d1520] p-3 transition-all duration-300 hover:border-cyan-500/30 hover:bg-[#101927]">
                      {idx < 6 && (
                        <div className="absolute right-[-10px] top-1/2 hidden h-px w-[18px] bg-[#243244] xl:block" />
                      )}

                      <div className="mb-2 flex items-center justify-between">
                        <span className={`h-2 w-2 rounded-full ${dot}`} />
                        <span className={`rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${badge}`}>
                          {status}
                        </span>
                      </div>

                      <div className="text-[10px] uppercase tracking-wide text-slate-500">
                        {step}
                      </div>

                      <div className="mt-1 truncate text-lg font-semibold text-white">
                        {value}
                      </div>

                      <div className="mt-1 truncate text-[10px] text-slate-500">
                        {detail}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] text-amber-200">
                Pipeline is live-monitored but constrained by PREPROD LOCK governance.
              </div>
            </Box>
          </div>

        </main>
      </div>
    </div>
  );
}
