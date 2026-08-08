import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const EMPTY_DATA = {
  global: {},
  pnlState: { summary: {} },
  equityCurveState: { history: [] },
  portfolioState: { bricks: {} },
  tradeJournalState: { summary: {}, rows: [] },
};

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function eur(v) {
  return `${num(v).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
}

function pct(v) {
  return `${(num(v) * 100).toFixed(1)}%`;
}

function Box({ children, className = "" }) {
  return <div className={`rounded-xl border border-[#1f2a37] bg-[#09111a]/95 ${className}`}>{children}</div>;
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
      <div className={`mt-1 truncate text-lg font-semibold ${tones[tone] || tones.white}`}>
        {value}
      </div>
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

function shortTs(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("fr-FR");
  } catch {
    return value;
  }
}

export default function Executive() {
  const [data, setData] = useState(EMPTY_DATA);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [aggregatorAudit, setAggregatorAudit] = useState(null);
  const [sourceAvailable, setSourceAvailable] = useState(false);
  const [sourceError, setSourceError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [
          dashboardRes,
          pnlRes,
          equityCurveRes,
          portfolioStateRes,
          aggregatorAuditRes,
          portfolioTargetRes,
          tradeJournalRes,
        ] = await Promise.all([
          fetch(apiUrl("/dashboard/v3"), { credentials: "include" }),
          fetch(apiUrl("/api/pnl-state"), { credentials: "include" }),
          fetch(apiUrl("/api/equity-curve-state"), { credentials: "include" }),
          fetch(apiUrl("/api/portfolio-state"), { credentials: "include" }),
          fetch(apiUrl("/api/aggregator-audit"), { credentials: "include" }),
          fetch(apiUrl("/api/portfolio-target"), { credentials: "include" }),
          fetch(apiUrl("/api/trade-journal-state"), { credentials: "include" }),
        ]);

        const [
          dashboard,
          pnlState,
          equityCurveState,
          portfolioState,
          aggregatorAudit,
          portfolioTargetJson,
          tradeJournalState,
        ] = await Promise.all([
          dashboardRes.ok ? dashboardRes.json() : Promise.resolve(null),
          pnlRes.ok ? pnlRes.json() : Promise.resolve(null),
          equityCurveRes.ok ? equityCurveRes.json() : Promise.resolve(null),
          portfolioStateRes.ok ? portfolioStateRes.json() : Promise.resolve(null),
          aggregatorAuditRes.ok ? aggregatorAuditRes.json() : Promise.resolve(null),
          portfolioTargetRes.ok ? portfolioTargetRes.json() : Promise.resolve(null),
          tradeJournalRes.ok ? tradeJournalRes.json() : Promise.resolve(null),
        ]);

        if (!cancelled) {
          setSourceAvailable(Boolean(dashboardRes.ok));
          setSourceError(
            dashboardRes.ok
              ? null
              : `Dashboard HTTP ${dashboardRes.status}`
          );
          setData({
            global: dashboard?.global || {},
            pnlState: pnlState || EMPTY_DATA.pnlState,
            equityCurveState: equityCurveState || EMPTY_DATA.equityCurveState,
            portfolioState: portfolioState || EMPTY_DATA.portfolioState,
            tradeJournalState: tradeJournalState || EMPTY_DATA.tradeJournalState,
          });
          setAggregatorAudit(aggregatorAudit);
          setPortfolioTarget(portfolioTargetJson);
        }
      } catch (error) {
        if (!cancelled) {
          setSourceAvailable(false);
          setSourceError(
            String(
              error?.message
              || error
              || "Executive source unavailable"
            )
          );
          setData(EMPTY_DATA);
        }
      }
    }

    load();
    const id = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const global = data.global || {};
  const pnl = data.pnlState?.summary || {};
  const pt = portfolioTarget?.data || portfolioTarget || {};
  const ps = data.portfolioState?.data || data.portfolioState || {};
  const bricks = ps?.bricks || {};

  const totalPnl = num(global.pnlGlobal ?? pnl.total_pnl_eur);
  const openPositions = num(global.openPositionsTotal ?? global.openPositions ?? pnl.open_positions_count);
  const orders = num(global.ordersToday ?? global.ordersCount);
  const regime = pt?.portfolio_regime || ps?.portfolio_regime || global.regime || "UNKNOWN";
  const governance = global.governanceMode || "UNKNOWN";
  const cashBuffer = num(pt?.cash_buffer);
  const auditStatus = String(aggregatorAudit?.status || "UNKNOWN").toUpperCase();
  const anomalies = num(aggregatorAudit?.summary?.anomalies_count);
  const warnings = num(aggregatorAudit?.summary?.warnings_count);
  const approved = num(aggregatorAudit?.summary?.approved_actions_count);

  const severity =
    String(governance).toUpperCase().includes("BLOCK") ? "CRITICAL" :
    anomalies > 0 ? "HIGH" :
    warnings > 0 || approved > 0 ? "MEDIUM" :
    "LOW";

  const chartData = useMemo(() => {
    const rows = Array.isArray(data.equityCurveState?.history) ? data.equityCurveState.history : [];
    return rows.slice(-30).map((row, idx) => ({
      idx: idx + 1,
      total_pnl_eur: num(row.total_pnl_eur),
      realized_pnl_eur: num(row.realized_pnl_eur),
      capital_engaged_eur: num(row.capital_engaged_eur),
    }));
  }, [data.equityCurveState]);

  const brickRows = Object.entries(bricks).map(([key, b]) => ({
    key,
    target: num(b.target_weight_snapshot),
    current: num(b.current_weight_estimate ?? b.target_weight_snapshot),
    confidence: num(b.confidence),
    origin: b.state_origin || "—",
  }));

  const journalRows = Array.isArray(data.tradeJournalState?.rows) ? data.tradeJournalState.rows.slice(0, 8) : [];

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Executive layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Executive</h1>
            <p className="text-xs text-slate-400">
              CIO-level overview: regime, governance, capital posture, PnL, allocation and execution footprint
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={sourceAvailable ? "blue" : "amber"}>{sourceAvailable ? (global.env || "UNAVAILABLE") : "OFFLINE"}</StatusPill>
            <StatusPill tone={severity === "LOW" ? "green" : severity === "MEDIUM" ? "amber" : "red"}>{severity}</StatusPill>
            <StatusPill tone="green">{String(regime).toUpperCase()}</StatusPill>
            <StatusPill tone="amber">{String(governance).toUpperCase()}</StatusPill>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-6 gap-3">
          <Metric label="Total PnL" value={eur(totalPnl)} tone={totalPnl >= 0 ? "green" : "red"} />
          <Metric label="Open Positions" value={openPositions} />
          <Metric label="Orders Today" value={orders} />
          <Metric label="Cash Buffer" value={pct(cashBuffer)} tone="blue" />
          <Metric label="Audit" value={auditStatus} tone={auditStatus === "OK" ? "green" : "amber"} />
          <Metric label="Approved Actions" value={approved} tone={approved > 0 ? "amber" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Executive Command</Title>
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Market Regime</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{String(regime).toUpperCase()}</div>
              </div>
              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Governance</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{String(governance).toUpperCase()}</div>
              </div>
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Protection</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">PROTECTED</div>
              </div>
              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Posture</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">PREPROD</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Decision Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${severity === "LOW" ? "text-emerald-400" : severity === "MEDIUM" ? "text-amber-300" : "text-red-400"}`}>
                {severity === "LOW" ? "CONTROLLED" : severity === "MEDIUM" ? "WATCH" : "REVIEW"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                The system remains in preproduction. Governance, allocation and execution are monitored without real execution.
              </div>
            </div>
          </Box>
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right={`${chartData.length} points`}>Performance Timeline</Title>
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="idx" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(9,17,26,0.96)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: "12px",
                      color: "#f8fafc",
                    }}
                  />
                  <Line type="monotone" dataKey="total_pnl_eur" name="Total PnL" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="realized_pnl_eur" name="Realized PnL" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="capital_engaged_eur" name="Capital Engaged" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Aggregator Audit</Title>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Status" value={auditStatus} tone={auditStatus === "OK" ? "green" : "amber"} />
              <Metric label="Anomalies" value={anomalies} tone={anomalies > 0 ? "red" : "green"} />
              <Metric label="Warnings" value={warnings} tone={warnings > 0 ? "amber" : "green"} />
              <Metric label="Approved" value={approved} tone={approved > 0 ? "amber" : "slate"} />
            </div>
            <div className="mt-3 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-300">
              Portfolio target, portfolio state, funding and rebalance consistency remain monitored through the aggregator audit.
            </div>
          </Box>
        </div>

        <Box className="mb-3 p-3">
          <Title right="Portfolio sleeves">Cross-Brick Executive View</Title>
          <div className="grid grid-cols-[1fr_80px_80px_80px_110px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Brick</div>
            <div>Target</div>
            <div>Current</div>
            <div>Conf.</div>
            <div>Origin</div>
          </div>
          <div className="space-y-2 pt-2">
            {brickRows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No brick data available.
              </div>
            ) : brickRows.map((row) => (
              <div key={row.key} className="grid grid-cols-[1fr_80px_80px_80px_110px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate text-slate-200">{row.key}</div>
                <div className="text-slate-300">{pct(row.target)}</div>
                <div className="text-slate-300">{pct(row.current)}</div>
                <div className="text-sky-300">{pct(row.confidence)}</div>
                <div className="truncate text-slate-500">{row.origin}</div>
              </div>
            ))}
          </div>
        </Box>

        <Box className="p-3">
          <Title right="Recent footprint">Trade Journal Snapshot</Title>
          <div className="grid grid-cols-[130px_1fr_100px_70px_100px_90px_100px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Timestamp</div>
            <div>Symbol</div>
            <div>Strategy</div>
            <div>Side</div>
            <div>Notional</div>
            <div>PnL</div>
            <div>Execution</div>
          </div>
          <div className="space-y-2 pt-2">
            {journalRows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No recent trade journal data.
              </div>
            ) : journalRows.map((row, idx) => (
              <div key={idx} className="grid grid-cols-[130px_1fr_100px_70px_100px_90px_100px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate text-slate-400">{shortTs(row.ts)}</div>
                <div className="truncate text-slate-200">{row.symbol || "—"}</div>
                <div className="truncate text-slate-400">{row.strategy || "—"}</div>
                <div className="text-slate-300">{row.side || "—"}</div>
                <div className="text-slate-300">{eur(row.notional_eur || 0)}</div>
                <div className={num(row.realized_pnl) >= 0 ? "text-emerald-400" : "text-red-400"}>{eur(row.realized_pnl || 0)}</div>
                <div className="truncate text-slate-500">{row.execution_mode || "—"}</div>
              </div>
            ))}
          </div>
        </Box>
      </main>
    </div>
  );
}
