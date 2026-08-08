import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson } from "../lib/apiClient";

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function eur(v) {
  return `${num(v).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} €`;
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

export default function PnLOverview() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [series, setSeries] = useState([]);
  const [summaryState, setSummaryState] = useState({});
  const [unit, setUnit] = useState("€");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const [pnlRes, curveRes] = await Promise.all([
        fetchJson("/api/pnl-state", { timeoutMs: 8000 }),
        fetchJson("/api/equity-curve-state", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      if (!pnlRes?.ok && !curveRes?.ok) {
        setErr("Unable to load PnL data.");
        setSeries([]);
        setSummaryState({});
        setUnit("€");
        setLoading(false);
        return;
      }

      const pnlSummary = pnlRes?.ok ? (pnlRes.data?.summary || {}) : {};
      const history = curveRes?.ok && Array.isArray(curveRes.data?.history)
        ? curveRes.data.history
        : [];

      setSummaryState(pnlSummary);
      setSeries(history.map((row) => ({
        label: row.phase || row.regime || "PREPROD",
        date: row.ts,
        value: row.total_pnl_eur,
        realized_pnl_eur: row.realized_pnl_eur,
        unrealized_pnl_eur: row.unrealized_pnl_eur,
        shadow_pnl_eur: row.shadow_pnl_eur,
        capital_engaged_eur: row.capital_engaged_eur,
        exposure: row.live_exposure_ratio,
      })));
      setUnit("€");
      setErr(null);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const summary = useMemo(() => {
    const values = series
      .map((it) => Number(it?.value ?? it?.y ?? NaN))
      .filter((v) => Number.isFinite(v));

    const latest = values.length ? values[values.length - 1] : Number(summaryState?.total_pnl_eur || 0);

    return {
      last: latest,
      total: Number(summaryState?.total_pnl_eur ?? latest ?? 0),
      realized: Number(summaryState?.realized_pnl_eur || 0),
      unrealized: Number(summaryState?.unrealized_pnl_eur || 0),
      openNotional: Number(summaryState?.open_positions_notional_eur || 0),
      openCount: Number(summaryState?.open_positions_count || 0),
      trades: Number(summaryState?.simulated_trades_count || 0),
      winRate: Number(summaryState?.win_rate || 0),
      best: values.length ? Math.max(...values) : 0,
      worst: values.length ? Math.min(...values) : 0,
      positive: values.filter((v) => v >= 0).length,
      negative: values.filter((v) => v < 0).length,
    };
  }, [series, summaryState]);

  const state = summary.total >= 0 ? "PROFITABLE" : "NEGATIVE";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Performance layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">PnL</h1>
            <p className="text-xs text-slate-400">
              Performance monitoring, recent PnL series and realized/unrealized contribution snapshot
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={state === "PROFITABLE" ? "green" : "red"}>{state}</StatusPill>
            <StatusPill tone="blue">Unit {unit}</StatusPill>
            <StatusPill tone="slate">{series.length} Points</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-6 gap-3">
          <Metric label="Total PnL" value={eur(summary.total)} tone={summary.total >= 0 ? "green" : "red"} />
          <Metric label="Realized" value={eur(summary.realized)} tone={summary.realized >= 0 ? "green" : "red"} />
          <Metric label="Unrealized" value={eur(summary.unrealized)} tone={summary.unrealized >= 0 ? "green" : "red"} />
          <Metric label="Open Notional" value={eur(summary.openNotional)} tone="blue" />
          <Metric label="Open Positions" value={summary.openCount} tone={summary.openCount > 0 ? "amber" : "slate"} />
          <Metric label="Trades" value={summary.trades} tone="slate" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>PnL Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Performance State</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{state}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Realized</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{eur(summary.realized)}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Unrealized</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{eur(summary.unrealized)}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Open Positions</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{summary.openCount}</div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Performance Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${summary.total >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {summary.total >= 0 ? "POSITIVE" : "NEGATIVE"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
This view tracks live PnL state, realized/unrealized contribution and the equity curve history for the current preproduction cycle.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-4">
          <Title right="Recent series">PnL Series</Title>

          <div className="grid grid-cols-[1fr_160px_120px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Label</div>
            <div>Date</div>
            <div>Value</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {series.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No PnL series available.
              </div>
            ) : series.map((it, idx) => {
              const v = Number(it?.value ?? it?.y ?? NaN);
              const ok = Number.isFinite(v);
              return (
                <div key={idx} className="grid grid-cols-[1fr_160px_120px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-200">{it?.label ?? it?.x ?? "—"}</div>
                  <div className="text-slate-400">{it?.date ?? "—"}</div>
                  <div className={`text-right ${ok && v >= 0 ? "text-emerald-400" : ok ? "text-red-400" : "text-slate-500"}`}>
                    {ok ? eur(v) : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        </Box>
      </main>
    </div>
  );
}
