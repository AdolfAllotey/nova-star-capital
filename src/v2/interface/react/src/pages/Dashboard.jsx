import { buildApiUrl as apiUrl } from "../lib/apiBase";
import { Link } from "react-router-dom";
import NscSidebar from "../components/layout/NscSidebar";
import React, { useEffect, useMemo, useState } from "react";

import {
  Home, Brain, ShieldCheck, Activity, Wallet, BarChart3, LineChart,
  RefreshCcw, Target, ServerCog, AlertTriangle, Layers, Briefcase,
  Gauge, CircleCheck, CircleDot
} from "lucide-react";



async function fetchDashboardSource(path) {
  try {
    const response = await fetch(
      apiUrl(path),
      {
        credentials: "include",
        cache: "no-store",
      }
    );

    if (!response.ok) {
      return {
        state: "error",
        status: response.status,
        data: null,
        error: `HTTP ${response.status}`,
      };
    }

    const data = await response.json();

    return {
      state: "online",
      status: response.status,
      data,
      error: null,
    };
  } catch (error) {
    return {
      state: "unavailable",
      status: 0,
      data: null,
      error: String(error?.message || error || "fetch error"),
    };
  }
}

function sourceValue(source, selector) {
  if (!source || source.state !== "online") {
    return null;
  }

  try {
    const value = selector(source.data);
    return value === undefined ? null : value;
  } catch {
    return null;
  }
}

function displayNumber(value, formatter = null) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return "N/A";
  }

  return formatter ? formatter(numeric) : numeric;
}

function normalizeBrickKey(key) {
  const k = String(key || "").toLowerCase();
  if (k === "defensive") return "equities_defensive";
  if (k === "metals") return "precious_metals";
  if (k === "options_us") return "options_us";
  return k;
}

function humanBrickName(key, fallback = "") {
  const k = normalizeBrickKey(key);
  const map = {
    crypto: "Crypto",
    equities_offensive: "Offensive Equities",
    equities_defensive: "Defensive Equities",
    bonds: "Bonds",
    precious_metals: "Precious Metals",
    long_term: "Long Term",
    options_us: "Options US · Simulated",
  };
  return map[k] || fallback || key || "—";
}

function modeBadgeClass(mode) {
  const m = String(mode || "").toUpperCase();
  if (m.includes("SHADOW")) return "border-violet-500/30 bg-violet-500/10 text-violet-300";
  if (m.includes("PATRIMONIAL")) return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  if (m.includes("SIMULATED_ONLY")) return "border-amber-400/30 bg-amber-400/10 text-amber-200";
  if (m.includes("SIMULATED_EXECUTION")) return "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";
  return "border-[#1f2a37] bg-[#0d1520] text-slate-300";
}

function confidenceClass(v) {
  const n = Number(v || 0);
  if (n >= 0.85) return "text-emerald-400";
  if (n >= 0.7) return "text-cyan-300";
  if (n >= 0.4) return "text-amber-300";
  return "text-slate-500";
}


import {
  AreaChart, Area, LineChart as RLineChart, Line, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Tooltip
} from "recharts";

function eur(v) {
  if (v === null || v === undefined || v === "") {
    return "N/A";
  }

  const n = Number(v);

  if (!Number.isFinite(n)) {
    return "N/A";
  }

  return `${n.toLocaleString("fr-FR", {
    maximumFractionDigits: 0,
  })} €`;
}

function pct(v) {
  const n = Number(v || 0);
  return `${(n * 100).toFixed(1)}%`;
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
  };
  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    violet: "bg-violet-400",
  };

  return (
    <div className={`mb-3 rounded-2xl border bg-gradient-to-r px-4 py-3 shadow signals-[0_0_50px_rgba(34,211,238,0.05)] ${toneMap[tone] || toneMap.cyan}`}>
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

function StatusBox({ label, value, tone = "green" }) {
  const tones = { green: "text-emerald-400", blue: "text-sky-400", purple: "text-violet-400", red: "text-red-400", white: "text-white", amber: "text-amber-300" };
  return (
    <div className="min-h-[62px] rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
      <div className="text-[9px] uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`mt-0.5 text-sm font-bold ${tones[tone] || tones.white}`}>{value}</div>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, sub, tone = "white" }) {
  const tones = { green: "text-emerald-400", red: "text-red-400", blue: "text-sky-400", amber: "text-amber-300", white: "text-white" };
  return (
    <div className="flex min-h-[68px] items-start gap-2 border-r border-[#1f2a37] px-3 py-2 last:border-r-0">
      <Icon className="mt-0.5 h-4 w-4 text-violet-300" />
      <div>
        <div className="text-[9px] uppercase tracking-wider text-slate-400">{label}</div>
        <div className={`mt-1 text-lg font-semibold ${tones[tone] || tones.white}`}>{value}</div>
        <div className="mt-0.5 text-[9px] text-slate-500">{sub}</div>
      </div>
    </div>
  );
}

function Title({ children, right }) {
  return (
    <div className="mb-2 grid grid-cols-[1.5fr_1fr_1fr] items-center">
      <h3 className="text-[13px] font-semibold uppercase tracking-wide text-white">{children}</h3>
      {right ? <div className="text-[11px] text-slate-500">{right}</div> : null}
    </div>
  );
}

function SidebarItem({ icon: Icon, label, path, active }) {
  const content = (
    <div
      className={`cursor-pointer flex items-center gap-2 rounded-md px-3 py-2 text-xs transition-all ${
        active
          ? "bg-[#16213a] text-white shadow signals-[inset_3px_0_0_#3b82f6]"
          : "text-slate-300 hover:bg-[#111827]"
      }`}
    >
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

function MiniTable({ rows }) {
  return (
    <div className="overflow-hidden text-xs">
      {rows.map((r, i) => (
        <div key={i} className="grid grid-cols-5 border-b border-[#172231] py-2 last:border-b-0">
          {r.map((c, j) => <div key={j} className={j === 0 ? "text-slate-300" : "text-slate-400"}>{c}</div>)}
        </div>
      ))}
    </div>
  );
}

function AllocationRow({ name, target, current }) {
  const width = Math.max(0, Math.min(100, Number(current || 0) * 100));
  const gap = Number(current || 0) - Number(target || 0);
  return (
    <div className="grid grid-cols-[1.6fr_48px_48px_65px_48px] items-center gap-2 text-xs">
      <div className="truncate text-slate-300">{name}</div>
      <div className="text-slate-300">{pct(target)}</div>
      <div className="text-slate-300">{pct(current)}</div>
      <div className="h-1.5 rounded bg-[#1a2532]">
        <div className="h-1.5 rounded bg-blue-500" style={{ width: `${width}%` }} />
      </div>
      <div className={gap < 0 ? "text-red-400" : "text-emerald-400"}>{`${(gap * 100).toFixed(1)}%`}</div>
    </div>
  );
}


function normalizeProtectionStatus(value) {
  if (Array.isArray(value)) {
    return String(value[0] || "NONE").toUpperCase();
  }

  const raw = String(value || "NONE").toUpperCase();

  if (raw.includes("PROTECTED")) return "PROTECTED";
  if (raw.includes("NONE")) return "NONE";

  return raw.split(",").map((x) => x.trim()).filter(Boolean)[0] || "NONE";
}

function formatDashboardDateTime(value) {
  const d = value ? new Date(value) : new Date();
  if (Number.isNaN(d.getTime())) return "—";
  return d
    .toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
    .replace(",", " · ");
}

function formatApiStatus(value) {
  const v = String(value || "").toUpperCase();
  if (v === "OK" || v === "HEALTHY") return "HEALTHY";
  return value || "UNKNOWN";
}

export default function DashboardV4() {
  const [dashboardSource, setDashboardSource] = useState({
    state: "loading",
    status: null,
    data: null,
    error: null,
  });
  const [portfolioStateSource, setPortfolioStateSource] = useState({
    state: "loading",
    status: null,
    data: null,
    error: null,
  });
  const [portfolioTargetSource, setPortfolioTargetSource] = useState({
    state: "loading",
    status: null,
    data: null,
    error: null,
  });
  const [marketRegimeSource, setMarketRegimeSource] = useState({
    state: "loading",
    status: null,
    data: null,
    error: null,
  });

  const [dashboard, setDashboard] = useState(null);
  const [chartRange, setChartRange] = useState("1D");
  const [portfolioState, setPortfolioState] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [marketRegime, setMarketRegime] = useState(null);

  useEffect(() => {
    async function load() {
      const [
        dashboardResult,
        portfolioStateResult,
        portfolioTargetResult,
        marketRegimeResult,
      ] = await Promise.all([
        fetchDashboardSource("/dashboard/v3"),
        fetchDashboardSource("/api/portfolio-state"),
        fetchDashboardSource("/api/portfolio-target"),
        fetchDashboardSource("/dashboard/market_regime"),
      ]);

      setDashboardSource(dashboardResult);
      setPortfolioStateSource(portfolioStateResult);
      setPortfolioTargetSource(portfolioTargetResult);
      setMarketRegimeSource(marketRegimeResult);

      setDashboard(dashboardResult.data);
      setPortfolioState(portfolioStateResult.data);
      setPortfolioTarget(portfolioTargetResult.data);
      setMarketRegime(marketRegimeResult.data);
    }
    load();
    const id = setInterval(load, 15000);
  return () => clearInterval(id);
  }, []);

  const dashboardOnline =
    dashboardSource.state === "online";

  const portfolioStateOnline =
    portfolioStateSource.state === "online";

  const portfolioTargetOnline =
    portfolioTargetSource.state === "online";

  const marketRegimeOnline =
    marketRegimeSource.state === "online";

  const sourceStates = {
    dashboard: dashboardSource.state,
    portfolioState: portfolioStateSource.state,
    portfolioTarget: portfolioTargetSource.state,
    marketRegime: marketRegimeSource.state,
  };


  const global = dashboard?.global || {};
  const strategies = Array.isArray(dashboard?.strategies) ? dashboard.strategies : [];
  const bricks = portfolioState?.bricks || portfolioState?.data?.bricks || {};
  const finalWeights = portfolioTarget?.final_brick_weights || portfolioTarget?.data?.final_brick_weights || {};

  const filteredChartHistory = useMemo(() => {
    const raw = Array.isArray(dashboard?.equityCurve?.history)
      ? dashboard.equityCurve.history
      : [];

    const validRaw = raw
      .filter((row) => row && typeof row === "object")
      .filter(
        (row) =>
          "active_pnl_eur" in row &&
          "unrealized_pnl_eur" in row
      )
      .filter((row) =>
        Number.isFinite(
          Number(
            row.total_pnl_eur ??
            row.total_pnl_including_options_eur ??
            row.total_pnl_including_shadow_eur ??
            row.realized_pnl_eur ??
            0
          )
        )
      )
      .filter((row) => {
        if (!row.ts) return false;
        return Number.isFinite(new Date(row.ts).getTime());
      })
      .sort(
        (a, b) =>
          new Date(a.ts).getTime() -
          new Date(b.ts).getTime()
      );

    if (chartRange === "ALL") {
      return validRaw;
    }

    const now = Date.now();

    let cutoff = null;

    if (chartRange === "1D") {
      cutoff = now - 24 * 60 * 60 * 1000;
    } else if (chartRange === "7D") {
      cutoff = now - 7 * 24 * 60 * 60 * 1000;
    } else if (chartRange === "30D") {
      cutoff = now - 30 * 24 * 60 * 60 * 1000;
    } else if (chartRange === "90D") {
      cutoff = now - 90 * 24 * 60 * 60 * 1000;
    } else if (chartRange === "YTD") {
      cutoff = new Date(
        new Date().getFullYear(),
        0,
        1
      ).getTime();
    }

    if (cutoff === null) {
      return validRaw;
    }

    return validRaw.filter(
      (row) =>
        new Date(row.ts).getTime() >= cutoff
    );
  }, [dashboard?.equityCurve?.history, chartRange]);

  const equityCurve = useMemo(() => {
    return filteredChartHistory.map((row, idx) => {
      const date = row.ts
        ? new Date(row.ts)
        : null;

      const label =
        idx === filteredChartHistory.length - 1
          ? "Now"
          : date
            ? date.toLocaleDateString("fr-FR", {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })
            : String(idx + 1);

      return {
        d: label,
        v: Math.round(
          Number(
            row.total_pnl_eur ??
            row.total_pnl_including_options_eur ??
            row.total_pnl_including_shadow_eur ??
            row.realized_pnl_eur ??
            0
          )
        ),
        realized: Math.round(
          Number(row.realized_pnl_eur ?? 0)
        ),
        ts: row.ts,
      };
    });
  }, [filteredChartHistory]);

  const ddCurve = useMemo(() => {
    let peak = null;

    return filteredChartHistory.map((row, idx) => {
      const date = row.ts
        ? new Date(row.ts)
        : null;

      const label =
        idx === filteredChartHistory.length - 1
          ? "Now"
          : date
            ? date.toLocaleDateString("fr-FR", {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })
            : String(idx + 1);

      const value = Number(
        row.total_pnl_eur ??
        row.total_pnl_including_options_eur ??
        row.total_pnl_including_shadow_eur ??
        row.realized_pnl_eur ??
        0
      );

      peak =
        peak === null
          ? value
          : Math.max(peak, value);

      const dd =
        peak > 0
          ? ((value - peak) / peak) * 100
          : 0;

      return {
        d: label,
        v: Number(dd.toFixed(2)),
        ts: row.ts,
      };
    });
  }, [filteredChartHistory]);

  const chartPointsCount = equityCurve?.length || 0;

  const latestCurveTs =
    equityCurve?.length
      ? equityCurve[equityCurve.length - 1]?.ts
      : null;

  const latestCurveLabel = latestCurveTs
    ? new Date(latestCurveTs).toLocaleTimeString(
        "fr-FR",
        {
          hour: "2-digit",
          minute: "2-digit",
        }
      )
    : "—";

  const currentDrawdown = ddCurve?.length ? Number(ddCurve[ddCurve.length - 1]?.v || 0) : 0;
  const maxDrawdown = ddCurve?.length
    ? Math.min(...ddCurve.map((x) => Number(x.v || 0)))
    : 0;

  const protectionSummary =

Array.isArray(global.protectionSummary) ? global.protectionSummary : [];

const telemetryFreshnessSec = (() => {
  try {
    const ts = global?.lastRefresh;
    if (!ts) return null;

    return Math.max(
      0,
      Math.floor(
        (Date.now() - new Date(ts).getTime()) / 1000
      )
    );
  } catch {
    return null;
  }
})();

const telemetryFreshnessLabel =
  telemetryFreshnessSec == null
    ? "UNKNOWN"
    : telemetryFreshnessSec < 20
    ? "LIVE"
    : telemetryFreshnessSec < 90
    ? "FRESH"
    : "STALE";

const telemetryFreshnessClass =
  telemetryFreshnessLabel === "LIVE"
    ? "text-emerald-400"
    : telemetryFreshnessLabel === "FRESH"
    ? "text-amber-300"
    : "text-red-400";

const preferredPortfolioOrder = [
  "crypto",
  "equities_offensive",
  "equities_defensive",
  "bonds",
  "precious_metals",
  "long_term",
  "options_us",
];

const excludedPortfolioKeys = new Set([
  "cash",
  "cash_buffer",
  "options_v2_shadow",
  "options_v3_shadow",
]);

const portfolioKeys = Array.from(
  new Set([
    ...Object.keys(finalWeights || {}),
    ...Object.keys(bricks || {}),
  ])
)
  .filter((key) => key && !excludedPortfolioKeys.has(key))
  .filter((key) => !String(key).endsWith("_shadow"))
  .filter((key) => {
    const target = Number(
      finalWeights?.[key] ??
      bricks?.[key]?.target_weight_snapshot ??
      0
    );
    const current = Number(
      bricks?.[key]?.current_weight_estimate ??
      bricks?.[key]?.target_weight_snapshot ??
      0
    );

    return target !== 0 || current !== 0;
  })
  .sort((a, b) => {
    const indexA = preferredPortfolioOrder.indexOf(a);
    const indexB = preferredPortfolioOrder.indexOf(b);

    if (indexA === -1 && indexB === -1) {
      return String(a).localeCompare(String(b));
    }

    if (indexA === -1) return 1;
    if (indexB === -1) return -1;

    return indexA - indexB;
  });

const driftRows = portfolioKeys.map((key) => {
  const b = bricks?.[key] || {};
  const target = Number(
    finalWeights?.[key] ??
    b.target_weight_snapshot ??
    0
  );
  const current = Number(
    b.current_weight_estimate ??
    b.target_weight_snapshot ??
    0
  );

  return {
    key,
    target,
    current,
    drift: Math.abs(current - target),
  };
});

const maxDrift = driftRows.length
  ? Math.max(...driftRows.map((r) => Number(r.drift || 0)))
  : 0;

const driftTrend =
  maxDrift >= 0.25
    ? "WORSENING"
    : maxDrift >= 0.10
    ? "WATCH"
    : "STABLE";

const driftTrendClass =
  driftTrend === "WORSENING"
    ? "text-red-400"
    : driftTrend === "WATCH"
    ? "text-amber-300"
    : "text-emerald-400";

const executionReadiness =
  Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock)
    ? 25
    : maxDrift >= 0.25
    ? 75
    : 92;

const executionReadinessClass =
  executionReadiness < 40
    ? "text-red-400"
    : executionReadiness < 80
    ? "text-emerald-300"
    : "text-emerald-400";


const riskSeverityScore = Math.min(
  100,
  Math.max(
    Boolean(
      global?.globalAuditBlocking ||
      global?.masterAuditHardBlock ||
      global?.institutionalSummaryStatus === "BLOCKING" ||
      global?.supervisionGateMode === "SAFE"
    ) ? 85 : 0,
    Math.round(
      Math.abs(maxDrift || 0) +
      (Number(global?.riskFlags || 0) * 12) +
      (Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock) ? 35 : 0)
    )
  )
);

const riskHeatClass =
  effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
    ? "border-red-500/35 bg-red-500/[0.06] shadow signals-[0_0_28px_rgba(239,68,68,0.14)]"
    : riskSeverityScore >= 70
    ? "border-red-500/35 bg-red-500/[0.06] shadow signals-[0_0_28px_rgba(239,68,68,0.14)]"
    : riskSeverityScore >= 35
    ? "border-amber-500/30 bg-amber-500/[0.05] shadow signals-[0_0_24px_rgba(245,158,11,0.10)]"
    : "border-emerald-500/25 bg-emerald-500/[0.04] shadow signals-[0_0_22px_rgba(16,185,129,0.08)]";

const riskPulseClass =
  effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK" || riskSeverityScore >= 70
    ? "animate-pulse"
    : "";

const driftHeatClass =
  Math.abs(maxDrift || 0) >= 0.25
    ? "border-red-500/35 bg-red-500/[0.06] shadow signals-[0_0_28px_rgba(239,68,68,0.14)]"
    : Math.abs(maxDrift || 0) >= 0.10
    ? "border-amber-500/30 bg-amber-500/[0.05]"
    : "border-emerald-500/25 bg-emerald-500/[0.04]";


  const protectedBrick = protectionSummary[0];

  const ordersExecuted = Number(global.ordersExecuted ?? Math.max(0, Number(global.ordersCount ?? 0) - Number(global.ordersRejected ?? 0)));
  const ordersRejected = Number(global.ordersRejected ?? 0);
  const activeEntryOrders = Number(global.activeEntryOrders ?? 0);
  const exitOrders = Number(global.exitOrders ?? 0);
  const optionsSignals = Number(
    global.optionsSignals ??
    global.optionsUsSignals ??
    global.shadowSignals ??
    0
  );
  const fillRatio = Number(global.fillRatio ?? (Number(global.ordersCount ?? 0) > 0 ? Math.round((ordersExecuted / Number(global.ordersCount ?? 1)) * 100) : 0));

  const dailyPnl = dashboardOnline
    ? Number(global.pnlDaily ?? global.pnlGlobal ?? 0)
    : null;
  const tradingPnl = dashboardOnline
    ? Number(global.pnlGlobal ?? 0)
    : null;
  const optionsPnl = Number(
    global.pnlOptionsUs ??
    global.optionsUsPnl ??
    global.pnlShadow ??
    0
  );
  const longTermPnl = dashboardOnline
    ? Number(global.pnlLongTerm ?? 0)
    : null;
  const totalPatrimonialPnl = Number(
    global.pnlTotalPatrimonial ??
    global.pnlTotalIncludingLongTermAndOptions ??
    global.pnlTotalIncludingLongTerm ??
    global.pnlTotalIncludingLongTermAndShadow ??
    global.pnlTotalIncludingShadow ??
    global.pnlGlobal ??
    0
  );
  const mtdPnl = dashboardOnline
    ? Number(global.pnlMTD ?? global.pnlGlobal ?? 0)
    : null;
  const ytdPnl = dashboardOnline
    ? Number(global.pnlYTD ?? global.pnlGlobal ?? 0)
    : null;
  const latestDrawdownPct = ddCurve?.length ? Number(ddCurve[ddCurve.length - 1].v || 0) : 0;
  const drawdownPct = Number(global.drawdown ?? latestDrawdownPct);
  const drawdownValue = dashboardOnline
    ? Number(global.drawdownValue ?? 0)
    : null;

  

const allocationRows = portfolioKeys.map((key) => {
    const b = bricks?.[key] || {};

    return {
      key,
      target: Number(
        finalWeights?.[key] ??
        b.target_weight_snapshot ??
        0
      ),
      current: Number(
        b.current_weight_estimate ??
        b.target_weight_snapshot ??
        0
      ),
    };
  });

  const portfolioConfidence = useMemo(() => {
    const entries = Object.entries(finalWeights || {});
    let weighted = 0;
    let total = 0;

    entries.forEach(([key, weight]) => {
      const w = Number(weight || 0);
      const c = Number(
        portfolioTarget?.brick_confidence?.[key] ??
        portfolioTarget?.data?.brick_confidence?.[key] ??
        bricks?.[key]?.confidence ??
        0
      );

      if (w > 0 && c > 0) {
        weighted += w * c;
        total += w;
      }
    });

    if (total > 0) return weighted / total;

    const strategyRows = Array.isArray(strategies) ? strategies : [];
    let sWeighted = 0;
    let sTotal = 0;

    strategyRows.forEach((s) => {
      const w = Number(s.targetExposure || 0);
      const c = Number(s.confidence || s.conf || 0);
      if (w > 0 && c > 0) {
        sWeighted += w * c;
        sTotal += w;
      }
    });

    return sTotal > 0 ? sWeighted / sTotal : 0;
  }, [finalWeights, portfolioTarget, bricks, strategies]);

  const marketRegimeConfidence = Number(
    marketRegime?.confidence ??
    marketRegime?.score ??
    global?.confidence ??
    portfolioConfidence ??
    0
  );

  const riskModeScore = (() => {
    const mode = String(
      global?.riskMode ||
      global?.riskLimits?.risk_mode ||
      global?.governance?.inputs?.risk_limits?.risk_mode ||
      ""
    ).toLowerCase();

    if (mode.includes("blocked") || mode.includes("hard")) return 0.2;
    if (mode.includes("reduced")) return 0.55;
    if (mode.includes("caution")) return 0.65;
    if (mode.includes("normal")) return 0.85;
    return 0.6;
  })();

  const governanceScore = (() => {
    if (global?.masterAuditHardBlock || global?.globalAuditBlocking) return 0.15;
    const mode = String(global?.governanceMode || "").toLowerCase();
    if (mode.includes("ok") || mode.includes("open")) return 0.9;
    if (mode.includes("caution") || mode.includes("watch")) return 0.65;
    if (mode.includes("blocked")) return 0.2;
    return 0.6;
  })();

  const correlationScore = (() => {
    const gate =
      global?.correlationGate ||
      global?.correlation_gate_state ||
      global?.governance?.correlation_gate_state ||
      null;

    if (!gate) return 0.65;
    if (gate.active === true) return 0.35;
    return 0.85;
  })();

  const nscBrainConfidence = Number(
    global?.confidence ??
    global?.confidencePct / 100 ??
    portfolioConfidence ??
    (
      marketRegimeConfidence * 0.4 +
      riskModeScore * 0.3 +
      governanceScore * 0.15 +
      correlationScore * 0.15
    )
  );

  const rawPortfolioConfidencePct = Math.round(Math.max(0, Math.min(1, nscBrainConfidence)) * 100);

  const blockingPenalty =
    global?.globalAuditBlocking || global?.institutionalSummaryStatus === "BLOCKING"
      ? 25
      : global?.globalAuditStatus === "BLOCKING"
        ? 25
        : global?.orchestrationStatus === "WARNING"
          ? 10
          : 0;

  const portfolioConfidencePct = Math.max(0, Math.min(100, rawPortfolioConfidencePct - blockingPenalty));

  const portfolioRegimeRaw = String(
    marketRegime?.regime ||
    marketRegime?.mode ||
    global?.regime ||
    global?.portfolioRegime ||
    "UNKNOWN"
  ).toUpperCase();

  const effectivePortfolioRegime =
    global?.globalAuditBlocking || global?.institutionalSummaryStatus === "BLOCKING"
      ? "BLOCKING"
      : global?.orchestrationStatus === "WARNING"
        ? "RISK_CONTROLLED"
        : portfolioRegimeRaw;

  const safetyMode = String(global?.governanceMode || global?.supervisionGateMode || "UNKNOWN").toUpperCase();


  
  const effectiveRegimeTone =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? "text-red-400"
      : effectivePortfolioRegime === "SAFE_MODE"
        ? "text-orange-300"
        : effectivePortfolioRegime === "RISK_CONTROLLED"
          ? "text-amber-300"
          : effectivePortfolioRegime === "RISK_ON"
            ? "text-emerald-400"
            : "text-cyan-300";

  const effectiveDecision =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? ["Governance blocked", "Execution restricted", "Manual review required"]
      : effectivePortfolioRegime === "SAFE_MODE"
        ? ["Safe mode active", "Execution constrained", "Funding manual only"]
        : effectivePortfolioRegime === "RISK_CONTROLLED"
          ? ["Controlled deployment", "Risk adjusted", "Hedges monitored"]
          : effectivePortfolioRegime === "RISK_OFF"
            ? ["Defensive posture", "Capital preserved", "Exposure reduced"]
            : ["Offensive active", "Defensive maintained", "Hedges monitored"];

  
  const effectiveRegimeBarClass =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? "bg-red-400"
      : effectivePortfolioRegime === "SAFE_MODE"
        ? "bg-amber-300"
        : effectivePortfolioRegime === "RISK_CONTROLLED"
          ? "bg-cyan-300"
          : "bg-emerald-400";

  const marketRegimeDelta = Number(global?.confidenceDelta ?? global?.confidenceHistory?.delta ?? 
    marketRegime?.delta ??
    marketRegime?.confidence_delta ??
    marketRegime?.score_delta ??
    0
  );

  

  const labelMap = {
    crypto: "Crypto",
    equities_offensive: "Offensive",
    equities_defensive: "Defensive",
    bonds: "Bonds",
    precious_metals: "Metals",
    long_term: "Long Term",
    options_us: "Options",
    metals: "Metals",
  };

  const cleanLabel = (v) => labelMap[v] || String(v || "—").replace(/_/g, " ");
  const cleanMode = (v) => {
    const s = String(v || "—").toUpperCase();
    if (s.includes("SHADOW")) return "SHADOW";
    if (s.includes("SIMULATED")) return "SIMULATED";
    if (s.includes("PATRIMONIAL")) return "PATRIMONIAL";
    if (s.includes("BLOCK")) return "BLOCKED";
    return s;
  };

  const cashBufferPct = Number(global?.capitalObserved || 0) > 0
    ? Number(global?.cashAvailable || 0) / Number(global?.capitalObserved || 1)
    : Number(
        portfolioTarget?.cash_buffer ??
        portfolioTarget?.data?.cash_buffer ??
        portfolioTarget?.summary?.cash_buffer ??
        portfolioState?.cash_buffer ??
        portfolioState?.data?.cash_buffer ??
        0
      );

  const dashboardRegime = String(
    marketRegime?.regime ||
    marketRegime?.mode ||
    portfolioTarget?.portfolio_regime ||
    portfolioState?.portfolio_regime ||
    global.regime ||
    "unknown"
  ).toLowerCase();

  const brainDecision = effectiveDecision ||
    dashboardRegime === "risk_on"
      ? ["Offensive active", "Defensive maintained", "Hedges monitored"]
      : dashboardRegime === "risk_off"
        ? ["Defensive priority", "Offensive reduced", "Hedges active"]
        : ["Balanced posture", "Allocation monitored", "No regime override"];


  const effectiveBrainDecision =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? ["Execution blocked", "Manual review required", "Governance intervention"]
      : effectivePortfolioRegime === "SAFE_MODE"
        ? ["Safe mode active", "Deployment paused", "Manual controls required"]
        : brainDecision;

  const effectiveCapitalPosture =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? ["Governance", "restricted"]
      : effectivePortfolioRegime === "SAFE_MODE"
        ? ["Deployment", "paused"]
        : ["Deployed", "selectively"];

  const brainReasoning = [
    {
      label: effectivePortfolioRegime === "RISK_ON" ? "Risk-On regime confirmed" : effectivePortfolioRegime === "RISK_OFF" ? "Risk-Off preservation active" : effectivePortfolioRegime === "RISK_CONTROLLED" ? "Risk-controlled posture active" : effectivePortfolioRegime === "BLOCKING" ? "Blocking regime detected" : "Portfolio regime monitored",
      tone: effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK" ? "red" : effectivePortfolioRegime === "RISK_CONTROLLED" ? "amber" : "green",
    },
    {
      label: Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock) ? "Governance intervention required" : safetyMode.includes("SAFE") || String(global.masterAuditGovernancePolicy || global.governanceMode || "").toUpperCase().includes("SIMULATED") ? "Governance constraints respected" : "Governance state monitored",
      tone: Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock) ? "red" : "green",
    },
    {
      label: global?.masterFundingManualApprovalRequired ? "Funding transfers require manual approval" : "Funding policy compliant",
      tone: global?.masterFundingManualApprovalRequired ? "amber" : "green",
    },
    {
      label: cashBufferPct > 0.1 ? "Cash buffer above flexibility threshold" : "Cash buffer under monitoring",
      tone: cashBufferPct > 0.1 ? "green" : "amber",
    },
  ];


  const riskFlagsCount = Number(global.riskFlags || 0);
  const governancePolicy = String(global.masterAuditGovernancePolicy || global.governanceMode || "").toUpperCase();
  const hardBlock = Boolean(global.masterAuditHardBlock || global.globalAuditBlocking);

  const onlyShadowRisk =
    riskFlagsCount === 1 &&
    Array.isArray(global.riskFlagsDetails) &&
    global.riskFlagsDetails.every((x) =>
      Array.isArray(x.softVetos) && x.softVetos.every((v) => String(v).toLowerCase().includes("shadow"))
    );

  const actionableRiskFlagsCount = onlyShadowRisk ? 0 : riskFlagsCount;
  const hasBlocking = Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock || hardBlock || governancePolicy === "BLOCKED");
  const hasWarning = !hasBlocking && actionableRiskFlagsCount > 0;

  const riskLevel =
    effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
      ? "BLOCKING"
      : Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock)
        ? "HIGH"
        : hasWarning
          ? "WATCH"
          : "LOW";
  const riskNeedleClass =
    riskLevel === "BLOCKING"
      ? "rotate-[62deg]"
      : riskLevel === "HIGH"
        ? "rotate-[50deg]"
        : riskLevel === "WATCH"
          ? "rotate-[0deg]"
          : "-rotate-[58deg]";

  const riskGaugeArcClass =
    "border-l-emerald-400 border-t-amber-400 border-r-red-500";

  const systemicStressLabel = Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock) ? "BLOCKING" : hasWarning ? "WATCH" : "NONE";

  const brainSignals = [
    {
      label: effectivePortfolioRegime === "RISK_ON" ? "RISK-ON" : effectivePortfolioRegime === "RISK_OFF" ? "RISK-OFF" : effectivePortfolioRegime === "RISK_CONTROLLED" ? "RISK WATCH" : effectivePortfolioRegime,
      tone: effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK" ? "red" : effectivePortfolioRegime === "RISK_CONTROLLED" ? "amber" : "green",
    },
    {
      label: global?.protectionLevel ? String(global.protectionLevel).toUpperCase() : "PROTECTION",
      tone: String(global?.protectionLevel || "").toUpperCase().includes("PROTECTED") ? "green" : "amber",
    },
    {
      label: cashBufferPct > 0.1 ? "CASH HEALTHY" : "CASH WATCH",
      tone: cashBufferPct > 0.1 ? "green" : "amber",
    },
    {
      label: global?.masterFundingManualApprovalRequired ? "FUNDING MANUAL" : "FUNDING OK",
      tone: global?.masterFundingManualApprovalRequired ? "amber" : "green",
    },
    {
      label: hasBlocking ? "BLOCKING ALERT" : hasWarning ? "RISK WATCH" : "NO BLOCKING",
      tone: hasBlocking ? "red" : hasWarning ? "amber" : "green",
    },
  ];

  const deploymentRatio = portfolioTargetOnline
    ? Number(
        portfolioTarget?.total_final_weight ??
        portfolioTarget?.data?.total_final_weight ??
        0
      )
    : null;
  const deployedCapital =
    dashboardOnline &&
    portfolioTargetOnline &&
    Number.isFinite(deploymentRatio)
      ? Number(global.capitalObserved || 0) * deploymentRatio
      : null;
  const reserveCapital =
    dashboardOnline &&
    Number.isFinite(cashBufferPct)
      ? Number(global.capitalObserved || 0) * cashBufferPct
      : null;
  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <div className="flex">
        <NscSidebar footerText="Dashboard layer online" />

        <main className="ml-[235px] w-[calc(100%-235px)] p-3">
          <div className="mb-2 grid grid-cols-[220px_1fr] items-center gap-2">
            <div>
              <h1 className="text-lg font-semibold uppercase tracking-wide">Dashboard</h1>
              <p className="text-sm text-slate-400">Executive Command Center</p>
            </div>
            <div className="mb-2 grid grid-cols-4 gap-2">
              {Object.entries(sourceStates).map(([name, state]) => (
                <div
                  key={name}
                  className={`rounded-lg border px-2 py-1 text-[10px] uppercase tracking-wide ${
                    state === "online"
                      ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                      : state === "loading"
                        ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-300"
                        : "border-red-400/20 bg-red-400/10 text-red-300"
                  }`}
                >
                  {name}: {state}
                </div>
              ))}
            </div>


            <div className="flex w-full items-stretch justify-between gap-2">
              <StatusBox label="Environment" value={dashboardOnline ? (global.env || "N/A") : "UNAVAILABLE"} tone={dashboardOnline ? "white" : "red"} />
              <StatusBox label="Mode" value="SIMULATED" tone="purple" />
              <StatusBox label="API Status" value={formatApiStatus(global.apiStatus)} />
              <StatusBox label="Last Update" value={formatDashboardDateTime(global.lastRefresh)} tone="white" />
              <StatusBox label="Refresh" value={<span className="flex items-center gap-2">15s <RefreshCcw className="h-3 w-3" /></span>} tone="white" />
              <StatusBox label="Governance" value={global.governanceMode || "—"} tone="amber" />
              <StatusBox label="Protection" value={global.protectionLevel || "—"} />
              <StatusBox label="UI Version" value="v6.2.0" tone="purple" />
            </div>
          </div>

          <Box className="mb-2 p-2">
            <Title>Portfolio Brain</Title>
            <div className="grid grid-cols-[230px_0.7fr_0.9fr_0.7fr_1fr_1.1fr] gap-4">
              <div className="flex items-center justify-center">
                <div className="relative flex h-32 w-68 items-center justify-center overflow-visible">
                  <div className="absolute inset-0 rounded-full bg-blue-600/25 blur-[95px] opacity-75" />
                  <div className="absolute left-6 top-8 h-24 w-60 rounded-full bg-sky-500/10 blur-[70px] opacity-80" />
                  <img
                    src="/assets/nsc-brain2.png"
                    alt="NSC Brain"
                    className="relative h-48 w-auto object-contain opacity-88 mix-blend-screen scale-[1.35] brightness-110 contrast-110 saturate-125 drop-shadow-[0_0_70px_rgba(59,130,246,0.9)]"
                  />
                </div>
              </div>

              <div className="border-l border-[#1f2a37] pl-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">Portfolio Regime</div>
                <div className={`mt-0.5 text-xl font-semibold ${
                  effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
                    ? "text-red-400"
                    : effectivePortfolioRegime === "RISK_CONTROLLED"
                        ? "text-yellow-300"
                        : dashboardRegime === "risk_off"
                          ? "text-cyan-300"
                          : "text-emerald-400"
                }`}>
                  {effectivePortfolioRegime}
                </div>
                <div className="mt-3 space-y-2.5">
                  {[
                    ["Strategic", Number(global?.strategicConfidencePct ?? global?.confidenceSplit?.strategic?.confidencePct ?? portfolioConfidencePct), "Allocation quality", "from-blue-500 to-cyan-300", Number(global?.confidenceDelta ?? 0) * 100],
                    ["Operational", Number(global?.operationalConfidencePct ?? global?.confidenceSplit?.operational?.confidencePct ?? 0), "System health", "from-emerald-500 to-teal-300", Number(global?.operationalConfidenceDelta ?? 0)],
                    ["Execution", Number(global?.executionConfidencePct ?? global?.confidenceSplit?.execution?.confidencePct ?? 0), "Execution readiness", "from-violet-500 to-fuchsia-300", Number(global?.executionConfidenceDelta ?? 0)],
                  ].map(([label, value, subtitle, gradient, delta]) => {
                    const pct = Math.max(0, Math.min(100, Math.round(Number(value || 0))));
                    const dRaw = Number(delta || 0);
                    const d = Math.abs(dRaw) < 0.01 ? 0 : Number(dRaw.toFixed(2));

                    return (
                      <div key={label} className="rounded-lg border border-white/5 bg-white/[0.025] px-2 py-1.5">
                        <div className="mb-1 flex items-center justify-between">
                          <div>
                            <div className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-300">{label}</div>
                            <div className="text-[8px] text-slate-500">{subtitle}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-[10px] font-bold text-slate-100">{pct}%</div>
                            {d !== 0 && (
                              <div className={`whitespace-nowrap text-[8px] font-semibold ${d > 0 ? "text-emerald-300" : d < -5 ? "text-red-300" : "text-amber-300"}`}>
                                {d > 0 ? "▲" : "▼"}{Math.abs(d).toFixed(2)}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="h-1.5 overflow-hidden rounded-full bg-slate-900/90 ring-1 ring-white/5">
                          <div
                            className={`h-full rounded-full bg-gradient-to-r ${gradient} shadow-[0_0_14px_rgba(34,211,238,0.35)]`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="border-l border-[#1f2a37] pl-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">Decision</div>
                <div className={`mt-0.5 text-xl font-semibold ${effectiveRegimeTone}`}>{effectiveBrainDecision[0]}</div>
                <div className="mt-1 text-lg text-slate-300">{effectiveBrainDecision[1]}</div>
                <div className="mt-1 text-lg text-slate-300">{effectiveBrainDecision[2]}</div>
              </div>

              <div className="border-l border-[#1f2a37] pl-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">Capital Posture</div>
                <div className="mt-2 text-xl font-semibold text-cyan-300">{effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK"
                    ? "Governance restricted"
                    : effectivePortfolioRegime === "SAFE_MODE"
                      ? "Deployment paused"
                      : effectivePortfolioRegime === "RISK_CONTROLLED"
                        ? "Controlled deployment"
                        : "Deployed selectively"}</div>
                <div className="mt-0.5 text-[9px] text-slate-400">Cash buffer</div>
                <div className="mt-1 text-lg text-sky-300">{pct(cashBufferPct)}</div>
              </div>

              <div className="border-l border-[#1f2a37] pl-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">Reasoning</div>
                <div className="mt-2 space-y-2 text-[12px] leading-4 text-slate-300 max-w-[320px]">
                  {brainReasoning.map((item) => (
                    <div key={item.label} className="flex items-start gap-2">
                      <span className={`mt-[5px] h-1.5 w-1.5 rounded-full ${
                        item.tone === "red" ? "bg-red-400" : item.tone === "amber" ? "bg-amber-300" : "bg-emerald-400"
                      }`} />
                      <span className={
                        item.tone === "red" ? "text-red-200" : item.tone === "amber" ? "text-amber-100" : "text-slate-300"
                      }>
                        {item.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-l border-[#1f2a37] pl-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-200">Key Signals</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {brainSignals.map((x) => (
                    <span
                      key={x.label}
                      className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                        x.tone === "red"
                          ? "border-red-400/25 bg-red-400/10 text-red-300"
                          : x.tone === "amber"
                            ? "border-amber-300/25 bg-amber-300/10 text-amber-200"
                            : "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
                      }`}
                    >
                      {x.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>

          </Box>

          <Box className="mb-2 border border-cyan-500/20 bg-[#07111d] p-3">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-cyan-300">
                  NSC Executive Summary
                </div>
                <div className="mt-1 text-[13px] leading-5 text-slate-300">
                  Portfolio operating in <span className="font-semibold text-emerald-300">{effectivePortfolioRegime}</span> regime.
                  Portfolio confidence remains <span className="font-semibold text-cyan-300">{portfolioConfidencePct >= 80 ? "HIGH" : portfolioConfidencePct >= 60 ? "ACCEPTABLE" : "UNDER WATCH"}</span>
                  <span className="text-slate-500"> ({portfolioConfidencePct}%)</span>.
                  {hasBlocking ? (
                    <span className="ml-1 font-semibold text-red-300">Blocking governance condition detected.</span>
                  ) : (
                    <span className="ml-1 font-semibold text-emerald-300">No blocking governance condition detected.</span>
                  )}
                  <span className="ml-1 text-slate-300">
                    Capital deployment remains governed under <span className="font-semibold text-violet-300">{safetyMode}</span>.
                  </span>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                  {effectivePortfolioRegime}
                </span>
                <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
                  Funding Manual
                </span>
                <span className="rounded-full border border-violet-400/25 bg-violet-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-violet-300">
                  Simulated Only
                </span>
              </div>
            </div>
          </Box>

          <Box className="mb-2 border border-[#1c2633] bg-[#07111d] p-3">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-cyan-300">
                  NSC Decision Drivers
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">
                  Core decision factors behind current portfolio posture
                </div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                DRIVER STACK ONLINE
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3">
              {[
                {
                  title: "Market Regime",
                  value: effectivePortfolioRegime,
                  meta1: `Confidence ${portfolioConfidencePct}%`,
                  meta2: "Engine Market Regime",
                  badge: effectivePortfolioRegime === "RISK_ON" ? "HEALTHY" : effectivePortfolioRegime === "RISK_OFF" ? "DEFENSIVE" : "WATCH",
                  tone: effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK" ? "red" : effectivePortfolioRegime === "RISK_CONTROLLED" ? "amber" : "green",
                },
                {
                  title: "Governance",
                  value: hasBlocking ? "BLOCKED" : "OPEN",
                  meta1: `Policy ${safetyMode}`,
                  meta2: global?.masterAuditGovernancePolicy || "UNAVAILABLE",
                  badge: hasBlocking ? "BLOCKED" : "SAFE",
                  tone: hasBlocking ? "red" : "green",
                },
                {
                  title: "Risk",
                  value: hasBlocking ? "HIGH" : hasWarning ? "WATCH" : "LOW",
                  meta1: `Flags ${Number(global?.riskFlags || 0)}`,
                  meta2: systemicStressLabel === "NONE" ? "Stress NONE" : `Stress ${systemicStressLabel}`,
                  badge: hasBlocking ? "ALERT" : hasWarning ? "WATCH" : "NO ALERT",
                  tone: hasBlocking ? "red" : hasWarning ? "amber" : "green",
                },
                {
                  title: "Funding",
                  value: global?.masterFundingManualApprovalRequired ? "MANUAL" : "OPEN",
                  meta1: `Cash Buffer ${pct(cashBufferPct)}`,
                  meta2: global?.masterFundingAutoTransferAllowed ? "Transfers Auto" : "Transfers Controlled",
                  badge: global?.masterFundingManualApprovalRequired ? "CONTROLLED" : "OPEN",
                  tone: global?.masterFundingManualApprovalRequired ? "amber" : "green",
                },
              ].map((d) => (
                <div key={d.title} className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">{d.title}</div>
                      <div className={`mt-1 text-lg font-semibold ${
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
                      {d.badge}
                    </span>
                  </div>

                  <div className="mt-2 space-y-1 text-[10px] text-slate-400">
                    <div>{d.meta1}</div>
                    <div>{d.meta2}</div>
                  </div>
                </div>
              ))}
            </div>
          </Box>

          <Box className="mb-2 border border-[#1c2633] bg-[#0b1220] p-3">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">
                  Explainability Layer
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">
                  Institutional decision narrative
                </div>
              </div>

              <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-cyan-300">
                LIVE SYSTEM REASONING
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">

              <div className="rounded-xl border border-[#1d2b3a] bg-[#0f1724] p-3">
                <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-300">
                  Why Current Posture
                </div>

                <div className="space-y-2 text-[11px] text-slate-300">

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                    <span>
                      Portfolio regime is
                      <span className="ml-1 font-semibold text-emerald-300">
                        adjusted by governance controls
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
                    <span>
                      Market regime confidence is
                      <span className="ml-1 font-semibold text-cyan-300">
                        {blockingPenalty > 0 ? "risk-adjusted under blocking controls" : portfolioConfidencePct >= 80 ? "strong" : portfolioConfidencePct >= 60 ? "acceptable" : "under watch"}
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-amber-300"></span>
                    <span>
                      Cash buffer requires
                      <span className="ml-1 font-semibold text-amber-300">
                        monitoring
                      </span>
                    </span>
                  </div>

                </div>
              </div>

              <div className="rounded-xl border border-[#1d2b3a] bg-[#0f1724] p-3">
                <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-violet-300">
                  Why No Rebalance
                </div>

                <div className="space-y-2 text-[11px] text-slate-300">

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-violet-400"></span>
                    <span>
                      Drift remains
                      <span className="ml-1 font-semibold text-violet-300">
                        within policy tolerance
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-blue-400"></span>
                    <span>
                      Funding transfers require
                      <span className="ml-1 font-semibold text-blue-300">
                        manual approval
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                    <span>
                      Governance engine keeps
                      <span className="ml-1 font-semibold text-slate-200">
                        controlled posture
                      </span>
                    </span>
                  </div>

                </div>
              </div>

              <div className="rounded-xl border border-[#1d2b3a] bg-[#0f1724] p-3">
                <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-red-300">
                  Governance Context
                </div>

                <div className="space-y-2 text-[11px] text-slate-300">

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                    <span>
                      Supervision gate currently
                      <span className="ml-1 font-semibold text-emerald-300">
                        OPEN
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-amber-300"></span>
                    <span>
                      System running under
                      <span className="ml-1 font-semibold text-amber-300">
                        SIMULATED_ONLY
                      </span>
                    </span>
                  </div>

                  <div className="flex items-start gap-2">
                    <span className="mt-[4px] h-1.5 w-1.5 rounded-full bg-red-400"></span>
                    <span>
                      Real execution remains
                      <span className="ml-1 font-semibold text-red-300">
                        disabled
                      </span>
                    </span>
                  </div>

                </div>
              </div>

            </div>
          </Box>

          <Box className="mb-2 grid grid-cols-8 gap-2">
            <Kpi icon={Activity} label="Trading PnL" value={eur(tradingPnl)} sub="Active strategies ex-LT" tone={tradingPnl >= 0 ? "green" : "red"} />
            <Kpi icon={BarChart3} label="Options US PnL" value={eur(optionsPnl)} sub="Funded simulation" tone={optionsPnl >= 0 ? "green" : "red"} />
            <Kpi icon={CircleCheck} label="LT PnL" value={eur(longTermPnl)} sub="Patrimonial assets" tone={longTermPnl >= 0 ? "green" : "red"} />
            <Kpi icon={LineChart} label="Drawdown" value={`${drawdownPct}%`} sub={eur(drawdownValue)} tone="red" />
            <Kpi icon={Briefcase} label="Open Positions" value={global.openPositions ?? 0} sub="Across bricks" />
            <Kpi 
  icon={ServerCog} 
  label="Orders Today" 
  value={global.ordersToday ?? global.ordersCount ?? 0} 
  sub={`${activeEntryOrders} entry / ${exitOrders} exit / ${optionsSignals} options signals`} 
/>
            <Kpi icon={ShieldCheck} label="Protected Bricks" value={`${global.protectedBricksCount ?? 0} / ${Object.keys(bricks || {}).length || 0}`} sub="Protected" tone="green" />
            <Kpi icon={ShieldCheck} label="Trailing Hits" value={global.trailingHitsCount ?? 0} sub="Today" />
          </Box>


          <div className="mb-2 grid grid-cols-[1.14fr_1fr_1.52fr] items-start gap-2">
            <Box className="min-h-[318px] overflow-hidden p-3">
              <div className="mb-1 flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold uppercase tracking-wide text-white whitespace-nowrap">Equity Curve</div>
                  
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={chartRange}
                    onChange={(e) => setChartRange(e.target.value)}
                    className="rounded-md border border-[#1f2a37] bg-[#111827] px-2 py-0.5 text-[9px] font-semibold text-slate-300 outline-none"
                  >
                    <option>1D</option>
                    <option>7D</option>
                    <option>30D</option>
                    <option>90D</option>
                    <option>YTD</option>
                    <option>ALL</option>
                  </select>
                  <span className="text-[10px] text-slate-400">{equityCurve?.length || 0} pts</span>
                  <span className="text-xs font-semibold text-white">{eur(totalPatrimonialPnl)}</span>
                </div>
              </div>

              <div className="mb-1 flex items-center justify-between text-[9px] text-slate-500">
                <span>{chartPointsCount} pts · updated {latestCurveLabel}</span>
                <span className="text-blue-300">source: equity_curve_engine</span>
              </div>

              <div className="mb-1 flex items-center gap-2 text-[9px] text-slate-400">
                <span className="h-1.5 w-4 rounded-full bg-blue-500"></span>
                <span>Total patrimonial PnL incl. LT + Options US (EUR)</span>
                <span className="text-slate-500">Trading {eur(tradingPnl)} · LT {eur(longTermPnl)} · Options US {eur(optionsPnl)}</span>
              </div>

              <div className="h-[252px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityCurve} margin={{ top: 6, right: 4, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.58}/>
                        <stop offset="60%" stopColor="#1d4ed8" stopOpacity={0.22}/>
                        <stop offset="100%" stopColor="#020617" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1f2a37" strokeOpacity={0.4} vertical={true} />
                    <XAxis dataKey="d" tick={{ fill: "#94a3b8", fontSize: 9 }} />
                    <YAxis
                      tick={{ fill: "#94a3b8", fontSize: 9 }}
                      tickFormatter={(v) => `${Math.round(v)} €`}
                    />
                    <Tooltip cursor={{ stroke: "#94a3b8", strokeWidth: 1, strokeDasharray: "3 3" }}
                      contentStyle={{ background: "#020617", border: "0", borderRadius: "6px" }}
                      formatter={(v) => [`${Math.round(v)} €`, "PnL"]}
                    />
                    <Area type="monotone" dataKey="v" stroke="#3b82f6" fill="url(#eq)" strokeWidth={2.6} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Box>

            <Box className="min-h-[318px] overflow-hidden p-3">
              <div className="mb-1 flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold uppercase tracking-wide text-white whitespace-nowrap">Drawdown</div>
                  
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={chartRange}
                    onChange={(e) => setChartRange(e.target.value)}
                    className="rounded-md border border-[#1f2a37] bg-[#111827] px-2 py-0.5 text-[9px] font-semibold text-slate-300 outline-none"
                  >
                    <option>1D</option>
                    <option>7D</option>
                    <option>30D</option>
                    <option>90D</option>
                    <option>YTD</option>
                    <option>ALL</option>
                  </select>
                  <span className="text-[10px] text-slate-400">{ddCurve?.length || 0} pts</span>
                  <span className="text-xs font-semibold text-red-400">
                    {ddCurve?.length
                      ? `${ddCurve[ddCurve.length - 1].v}%`
                      : "0%"}
                  </span>
                </div>
              </div>

              <div className="mb-1 flex items-center justify-between text-[9px] text-slate-500">
                <span>current DD {currentDrawdown.toFixed(2)}%</span>
                <span className="text-red-300">max DD {maxDrawdown.toFixed(2)}%</span>
              </div>

              <div className="mb-1 flex items-center gap-2 text-[9px] text-slate-400">
                <span className="h-1.5 w-4 rounded-full bg-red-500"></span>
                <span>Drawdown %</span>
              </div>

              <div className="h-[252px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={ddCurve} margin={{ top: 6, right: 4, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="dd" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.52}/>
                        <stop offset="70%" stopColor="#991b1b" stopOpacity={0.22}/>
                        <stop offset="100%" stopColor="#020617" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1f2a37" strokeOpacity={0.4} vertical={true} />
                    <XAxis
                      dataKey="d"
                      tick={{ fill: "#94a3b8", fontSize: 9 }}
                      tickFormatter={(value) => {
                        const date = new Date(value);

                        if (Number.isNaN(date.getTime())) {
                          return value;
                        }

                        return chartRange === "1D"
                          ? date.toLocaleTimeString("fr-FR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : date.toLocaleDateString("fr-FR", {
                              day: "2-digit",
                              month: "short",
                            });
                      }}
                    />
                    <YAxis
                      tick={{ fill: "#94a3b8", fontSize: 9 }}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip cursor={{ stroke: "#94a3b8", strokeWidth: 1, strokeDasharray: "3 3" }}
                      contentStyle={{ background: "#020617", border: "0", borderRadius: "6px" }}
                      formatter={(v) => [`${v}%`, "Drawdown"]}
                    />
                    <Area type="monotone" dataKey="v" stroke="#ef4444" fill="url(#dd)" strokeWidth={2.6} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Box>

            <Box className="grid min-h-[318px] grid-cols-[0.9fr_1.5fr] overflow-visible p-3">
              <div className="border-r border-[#1f2a37] pr-4">
                <div className="mb-2 flex items-start justify-between">
                  
<div className="flex items-center justify-between">
  <Title>Risk Console</Title>

  <div className="flex items-center gap-2">
    <div className={`h-2 w-2 rounded-full ${
      telemetryFreshnessLabel === "LIVE"
        ? "bg-emerald-400 animate-pulse"
        : telemetryFreshnessLabel === "FRESH"
        ? "bg-amber-300"
        : "bg-red-500"
    }`} />

    <span className={`text-[9px] font-semibold uppercase tracking-[0.18em] ${telemetryFreshnessClass}`}>
      {telemetryFreshnessLabel}
    </span>
  </div>
</div>

                  <span className={
                    Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock)
                      ? "rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[8px] font-bold uppercase text-red-300"
                      : Number(global?.riskFlags || 0) > 0
                        ? "rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[8px] font-bold uppercase text-amber-300"
                        : "rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[8px] font-bold uppercase text-emerald-300"
                  }>
                    {Boolean(global?.globalAuditBlocking || global?.masterAuditHardBlock) ? "Blocking" : Number(global?.riskFlags || 0) > 0 ? "Watch" : "Stable"}
                  </span>
                </div>

                <div className="text-[9px] uppercase text-slate-400">Risk Level</div>
                <div className="mt-1 flex items-end gap-2">
                  <span className={
                    riskLevel === "LOW"
                      ? "text-lg font-semibold text-emerald-400"
                      : riskLevel === "WATCH"
                      ? "text-lg font-semibold text-amber-300"
                      : "text-lg font-semibold text-red-400"
                  }>
                    
{riskLevel}

<div className="mt-0.5 text-[8px] text-slate-500">
  sync {telemetryFreshnessSec ?? "?"}s ago
</div>

                  </span>
                  <span className="pb-0.5 text-[9px] text-slate-500">
                    {riskFlagsCount || 0} active flag{Number(riskFlagsCount || 0) > 1 ? "s" : ""}
                  </span>
                </div>

                <div className="my-2 flex flex-col items-center justify-center gap-3">
                  <div className="relative h-16 w-32 shrink-0">
                    <div className={`absolute bottom-0 left-0 h-16 w-32 rounded-t-full border-[10px] border-b-0 opacity-95 ${riskGaugeArcClass}`} />
                    <div className={`absolute bottom-0 left-1/2 h-11 w-[2px] origin-bottom bg-white shadow signals-[0_0_12px_rgba(255,255,255,0.75)] transition-transform duration-700 ${riskNeedleClass}`} />
                    <div className="absolute bottom-0 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-white" />
                  </div>

                  <div className="min-w-[92px] text-center leading-tight">
                    <div className="text-[8px] uppercase tracking-[0.18em] text-slate-500">
                      Severity Score
                    </div>

                    <div className={`mt-1 text-sm font-semibold ${
                      riskSeverityScore >= 70
                        ? "text-red-400"
                        : riskSeverityScore >= 35
                        ? "text-amber-300"
                        : "text-emerald-400"
                    }`}>
                      {riskSeverityScore}/100
                    </div>
                  </div>
                </div>


                {[
                  ["Protection", global.protectionLevel || "—"],
                  ["Kill Switch", global.masterAuditHardBlock ? "ON" : "OFF"],
                  ["Governance", global.masterAuditGovernancePolicy === "SIMULATED_ONLY" ? "SIM ONLY" : (global.governanceMode || "—")],
                  ["Supervision", global.supervisionGateOpen ? (global.supervisionGateMode || "OPEN") : "CLOSED"],
                  ["Systemic Stress", effectivePortfolioRegime === "BLOCKING" || effectivePortfolioRegime === "HARD_BLOCK" ? "BLOCKING" : effectivePortfolioRegime === "SAFE_MODE" ? "SAFE_MODE" : Number(global?.riskFlags || 0) > 0 ? `WATCH (${global.riskFlagsDetails?.[0]?.softVetos?.[0] || "flag"})` : "NONE"],
                ].map(([a,b]) => {
                  const bad = String(b).includes("BLOCKING") || String(b).includes("ON") || String(b).includes("CLOSED");
                  const watch = String(b).includes("WATCH") || String(b).includes("SIM");
                  return (
                    <div key={a} className="flex justify-between border-t border-[#1f2a37] py-1 text-[9px]">
                      <span className="text-slate-400">{a}</span>
                      <span className={bad ? "font-semibold text-red-300" : watch ? "font-semibold text-amber-300" : "font-semibold text-emerald-400"}>
                        {b}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="pl-4">
                <div className="mb-2 flex items-start justify-between">
                  <Title>Protection Summary</Title>
                  <div className="flex gap-2 text-[8px]">
                    <span className="rounded-md border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 font-semibold text-emerald-300">
                      {global.protectedBricksCount ?? 0} protected
                    </span>
                    <span className="rounded-md border border-slate-500/20 bg-slate-500/10 px-2 py-0.5 font-semibold text-slate-300">
                      {global.trailingHitsCount ?? 0} trailing
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-[1.35fr_1fr_0.75fr_0.75fr] gap-2 border-b border-[#1f2a37] pb-1.5 text-[9px] uppercase text-slate-400">
                  <div>Brick</div><div>Status</div><div>Protected</div><div>Trailing</div>
                </div>

                {portfolioKeys.map((brick) => {
                  const p = protectionSummary.find((x) => normalizeBrickKey(x.brick) === normalizeBrickKey(brick)) || {};
                  const rawStatus = Array.isArray(p.status) ? p.status.join(",") : String(p.status || "NONE");
                  const protectedCount = Number(p.protectedPositionsCount ?? 0);
                  const trailingCount = Number(p.trailingHitCount ?? 0);
                  const status = rawStatus.toUpperCase().includes("PROTECTED") || protectedCount > 0 ? "PROTECTED" : "NONE";
                  const protectedActive = status !== "NONE";
                  return (
                    <div key={brick} className="grid grid-cols-[1.35fr_1fr_0.75fr_0.75fr] items-center gap-2 border-b border-[#172231] py-1.5 text-[9px]">
                      <div className="truncate text-white">{humanBrickName(brick)}</div>
                      <div>
                        <span className={`rounded-md border px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide ${
                          protectedActive
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                            : "border-slate-500/20 bg-slate-500/10 text-slate-400"
                        }`}>
                          {status}
                        </span>
                      </div>
                      <div className={protectedCount > 0 ? "font-semibold text-emerald-300" : "text-slate-400"}>{protectedCount}</div>
                      <div className={trailingCount > 0 ? "font-semibold text-amber-300" : "text-slate-400"}>{trailingCount}</div>
                    </div>
                  );
                })}
              </div>
            </Box>
          </div>

          <div className="mb-2 grid grid-cols-[0.82fr_0.82fr_1.53fr] gap-2">
            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Allocation: Target vs Current</Title>
              <div className="space-y-3">
                <div className="grid grid-cols-[1.45fr_48px_48px_65px_48px_58px] gap-2 text-[9px] uppercase text-slate-400">
                  <div>Brick</div><div>Target %</div><div>Current %</div><div></div><div>Gap %</div><div>Urgency</div>
                </div>
                {allocationRows.map((r) => {
                  const gap = Math.round((Number(r.current || 0) - Number(r.target || 0)) * 1000) / 10;
                  const absGap = Math.abs(gap);
                  const urgency = absGap >= 20 ? "HIGH" : absGap >= 8 ? "WATCH" : "LOW";
                  return (
                    <div key={r.key} className="grid grid-cols-[1.45fr_48px_48px_65px_48px_58px] gap-2 items-center text-[10px]">
                      <div className="truncate text-white">{humanBrickName(r.key)}</div>
                      <div>{pct(r.target)}</div>
                      <div>{pct(r.current)}</div>
                      <div className="h-1.5 rounded bg-slate-800">
                        <div
                          className={`h-1.5 rounded ${
                            gap < -8 ? "bg-red-400" : gap > 8 ? "bg-emerald-400" : "bg-blue-400"
                          }`}
                          style={{ width: `${Math.min(100, Math.abs(gap) * 2.8)}%` }}
                        />
                      </div>
                      <div className={gap < 0 ? "text-red-400" : "text-emerald-400"}>
                        {gap > 0 ? "+" : ""}{gap.toFixed(1)}%
                      </div>
                      <div>
                        <span className={`rounded-md border px-1.5 py-0.5 text-[8px] font-semibold ${
                          urgency === "HIGH"
                            ? "border-red-500/30 bg-red-500/10 text-red-300"
                            : urgency === "WATCH"
                            ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        }`}>
                          {urgency}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Box>

            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Funding Pools</Title>

              {(() => {
                const backendFundingPools =
                  portfolioState?.funding_pools ||
                  portfolioState?.data?.funding_pools ||
                  {};

                const capitalObserved = Number(global.capitalObserved || 0);

                const cryptoWeight = Number(finalWeights?.crypto ?? 0);

                const longTermWeight = Number(
                  finalWeights?.long_term ?? 0
                );

                const nonCryptoTradableWeight = Object.entries(
                  finalWeights || {}
                ).reduce((total, [key, rawWeight]) => {
                  if (
                    key === "crypto" ||
                    key === "long_term" ||
                    key === "cash" ||
                    key === "cash_buffer" ||
                    String(key).endsWith("_shadow")
                  ) {
                    return total;
                  }

                  return total + Number(rawWeight || 0);
                }, 0);

                const cashBufferWeight = Number(
                  portfolioTarget?.cash_buffer ??
                  portfolioTarget?.data?.cash_buffer ??
                  0
                );

                const pools = Object.entries(backendFundingPools).length
                  ? Object.entries(backendFundingPools)
                  : [
                      ["IBKR Pool", {
                        target_amount_eur:
                          capitalObserved * nonCryptoTradableWeight,
                        available_eur:
                          capitalObserved * nonCryptoTradableWeight,
                        utilization_pct: 0
                      }],
                      ["Crypto Exchange Pool", {
                        target_amount_eur:
                          capitalObserved * cryptoWeight,
                        available_eur:
                          capitalObserved * cryptoWeight,
                        utilization_pct: 0
                      }],
                      ["Long-Term Pool", {
                        target_amount_eur:
                          capitalObserved * longTermWeight,
                        available_eur:
                          capitalObserved * longTermWeight,
                        utilization_pct: 0
                      }],
                      ["Cash Buffer", {
                        target_amount_eur:
                          capitalObserved * cashBufferWeight,
                        available_eur:
                          capitalObserved * cashBufferWeight,
                        utilization_pct: 0
                      }],
                    ];

                const totalTarget = pools.reduce((acc, [, v]) => acc + Number(v.target_amount_eur ?? v.target_amount ?? 0), 0);
                const totalAvailable = pools.reduce((acc, [, v]) => acc + Number(v.available_eur ?? v.available_amount_eur ?? v.target_amount_eur ?? v.target_amount ?? 0), 0);
                const utilization = totalTarget > 0 ? Math.round(((totalTarget - totalAvailable) / totalTarget) * 100) : 0;
  return (
                  <>
                    <div className="grid grid-cols-[1.15fr_0.9fr_0.9fr_0.65fr] gap-2 border-b border-[#1f2a37] pb-1.5 text-[9px] uppercase text-slate-400">
                      <div>Pool</div><div>Target</div><div>Available</div><div>Util.</div>
                    </div>

                    {pools.map(([k,v]) => (
                      <div key={k} className="grid grid-cols-[1.15fr_0.9fr_0.9fr_0.65fr] gap-2 border-b border-[#172231] py-1 text-[9px]">
                        <div className="truncate text-white">{k}</div>
                        <div>{eur(v.target_amount_eur ?? v.target_amount ?? 0)}</div>
                        <div className="text-emerald-400">{eur(v.available_eur ?? v.available_amount_eur ?? v.target_amount_eur ?? v.target_amount ?? 0)}</div>
                        <div className="flex items-center gap-1">
                          <div className="h-1.5 w-8 rounded bg-slate-800">
                            <div className="h-1.5 rounded bg-emerald-400" style={{ width: `${Math.max(0, Math.min(100, Number(v.utilization_pct ?? 0)))}%` }} />
                          </div>
                          <span>{Math.round(Number(v.utilization_pct ?? 0))}%</span>
                        </div>
                      </div>
                    ))}

                    <div className="grid grid-cols-[1.15fr_0.9fr_0.9fr_0.65fr] gap-2 pt-2 text-[9px] font-semibold">
                      <div className="text-white">TOTAL</div>
                      <div className="text-blue-300">{eur(totalTarget)}</div>
                      <div className="text-blue-300">{eur(totalAvailable)}</div>
                      <div className="text-blue-300">{utilization}%</div>
                    </div>
                  </>
                );
              })()}
            </Box>

            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Cross-Brick Overview</Title>
              <div className="grid grid-cols-[1.15fr_0.75fr_0.75fr_0.55fr_0.6fr_0.45fr_0.65fr_0.45fr_0.45fr] gap-2 border-b border-[#1f2a37] pb-1.5 text-[9px] uppercase text-slate-400">
                <div>Brick</div><div>Mode</div><div>Regime</div><div>Target</div><div>Current</div><div>Pos</div><div>PnL</div><div>Risk</div><div>Conf.</div>
              </div>

              {strategies.map((s) => {
                const key = normalizeBrickKey(s.key);
                const riskOk = Number(s.riskFlags ?? 0) === 0;
                const confRaw = Number(
                  s.confidence ??
                  s.conf ??
                  portfolioTarget?.brick_confidence?.[key] ??
                  portfolioTarget?.data?.brick_confidence?.[key] ??
                  0
                );
                const conf = Math.round(confRaw * 100);

                return (
                  <div key={s.key || s.name} className="grid grid-cols-[1.15fr_0.75fr_0.75fr_0.55fr_0.6fr_0.45fr_0.65fr_0.45fr_0.45fr] gap-2 border-b border-[#172231] py-1.5 text-[9.5px]">
                    <div className="truncate text-white">{humanBrickName(s.key, s.name)}</div>
                    <div className="truncate">
                      <span className={`rounded-full border px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide ${modeBadgeClass(s.mode)}`}>
                        {s.mode || "—"}
                      </span>
                    </div>
                    <div className="truncate">{s.regime || "—"}</div>
                    <div>{pct(s.targetExposure)}</div>
                    <div>{pct(s.currentExposure ?? s.targetExposure)}</div>
                    <div>{s.positions ?? s.openPositions ?? 0}</div>
                    <div className={Number(s.pnl || 0) >= 0 ? "text-emerald-400" : "text-red-400"}>{eur(s.pnl)}</div>
                    <div className={riskOk ? "text-emerald-400" : "text-amber-300"}>●</div>
                    <div className={confidenceClass(confRaw)}>{conf}%</div>
                  </div>
                );
              })}
            </Box>
          </div>

          <div className="grid grid-cols-[1.05fr_1.25fr_1fr] gap-2">
            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Execution Health</Title>

              <div className="mb-3 grid grid-cols-5 gap-0 text-center">
                {[
                  ["Candidate Orders", global.candidatesCount ?? 0],
                  ["Final Orders", global.ordersCount ?? 0],
                  ["Entry Orders", activeEntryOrders],
                  ["Exit Orders", exitOrders],
                  ["Options Signals", optionsSignals],
                  ["Fills", ordersExecuted],
                  ["Rejected", ordersRejected],
                  ["Fill Ratio", `${fillRatio}%`],
                ].map(([label, value], i) => (
                  <div key={label} className={i === 4 ? "" : "border-r border-[#1f2a37]"}>
                    <div className="text-[9px] uppercase leading-tight text-slate-500">{label}</div>
                    <div className="mt-1 text-xl font-semibold text-white">{value}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-[0.75fr_1.2fr_0.75fr_0.55fr_0.55fr_0.75fr_0.75fr] gap-2 border-b border-[#1f2a37] pb-2 text-[9px] uppercase text-slate-500">
                <div>Time</div>
                <div>Brick</div>
                <div>Symbol</div>
                <div>Side</div>
                <div>Qty</div>
                <div>Price</div>
                <div>Status</div>
              </div>
              <div className="mt-3 rounded-lg border border-cyan-500/20 bg-cyan-500/10 p-3 text-xs leading-5 text-cyan-200">
                <span className="mr-2 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-cyan-300">
                  Reserved
                </span>
                Runtime fill stream is not connected to Dashboard yet. Dedicated execution views remain the source for order-level diagnostics.
              </div>

            </Box>

            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Explainability Snapshot</Title>
              <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs leading-5 text-emerald-200">
                <span className="mr-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-300">
                  Dynamic
                </span>
                Current posture is derived from portfolio regime, brick confidence, funding constraints, governance state and protection status.
              </div>
            </Box>

            <Box className="p-2 border border-[#1c2633] bg-[#0d1520]">
              <Title>Today’s Changes</Title>

              <div className="grid grid-cols-[0.75fr_1fr_0.45fr] gap-2 border-b border-[#1f2a37] pb-1.5 text-[9px] uppercase text-slate-500">
                <div>Time</div><div>Message</div><div>Impact</div>
              </div>
              <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs leading-5 text-amber-200">
                <span className="mr-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-300">
                  Pending Feed
                </span>
                Audited change feed is not connected yet. This area is reserved for validated portfolio, execution, risk and governance events.
              </div>

            </Box>
          </div>
        </main>
      </div>
    </div>
  );
}
