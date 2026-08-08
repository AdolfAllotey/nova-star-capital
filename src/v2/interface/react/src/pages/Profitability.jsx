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

function pct(v) {
  return `${num(v).toFixed(2)}%`;
}

function monthLabel(m) {
  if (!m) return "—";
  if (m.label) return m.label;
  if (m.year && m.month) return `${m.year}-${String(m.month).padStart(2, "0")}`;
  return m.date || "—";
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

export default function Profitability() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [summary, setSummary] = useState({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const [monthlyRes, summaryRes] = await Promise.all([
        fetchJson("/profitability/monthly", { timeoutMs: 8000 }),
        fetchJson("/profitability/summary", { timeoutMs: 8000 }),
      ]);
      if (cancelled) return;

      const r = monthlyRes;

      if (!r.ok) {
        const msg =
          r?.error?.detail?.detail ??
          r?.error?.detail ??
          r?.error?.message ??
          (typeof r?.error === "string" ? r.error : null);

        if (msg && String(msg).toLowerCase().includes("no profitability")) {
          setMonthly([]);
          setErr(null);
          setLoading(false);
          return;
        }

        setErr("Unable to load profitability data.");
        setMonthly([]);
        setLoading(false);
        return;
      }

      const data = r.data;

      if (data && typeof data === "object" && data.detail) {
        if (String(data.detail).toLowerCase().includes("no profitability")) {
          setMonthly([]);
          setErr(null);
          setLoading(false);
          return;
        }
      }

      setMonthly(Array.isArray(data?.monthly) ? data.monthly : []);
      setSummary(summaryRes?.ok ? (summaryRes.data || {}) : {});
      setLoading(false);
    }

    load();
    const id = setInterval(load, 30000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const aggregates = useMemo(() => {
    let pnlGross = 0;
    let pnlNet = 0;
    let costs = 0;

    for (const m of monthly) {
      pnlGross += num(m?.pnl_gross_eur);
      pnlNet += num(m?.pnl_net_eur);
      costs += num(m?.costs_eur);
    }

    const margin = pnlGross !== 0 ? (pnlNet / Math.abs(pnlGross)) * 100 : 0;
    const costRatio = pnlGross !== 0 ? (costs / Math.abs(pnlGross)) * 100 : 0;

    if (!monthly.length) {
      const pnlGrossFromSummary = num(summary?.total_pnl);
      const costsFromSummary = num(summary?.total_costs);
      const netFromSummary = num(summary?.net);
      const marginFromSummary = pnlGrossFromSummary !== 0 ? (netFromSummary / Math.abs(pnlGrossFromSummary)) * 100 : 0;
      const costRatioFromSummary = pnlGrossFromSummary !== 0 ? (costsFromSummary / Math.abs(pnlGrossFromSummary)) * 100 : 0;

      return {
        pnlGross: pnlGrossFromSummary,
        pnlNet: netFromSummary,
        costs: costsFromSummary,
        months: 0,
        margin: marginFromSummary,
        costRatio: costRatioFromSummary,
      };
    }

    return { pnlGross, pnlNet, costs, months: monthly.length, margin, costRatio };
  }, [monthly, summary]);

  const hasData =
    monthly.length > 0 ||
    summary?.total_pnl !== undefined ||
    summary?.total_costs !== undefined ||
    summary?.net !== undefined;
  const state = hasData
    ? aggregates.pnlNet >= 0 ? "PROFITABLE" : "UNPROFITABLE"
    : "DATA PENDING";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Profitability layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Profitability</h1>
            <p className="text-xs text-slate-400">
              Net profitability monitoring: gross PnL, operating costs, net PnL and monthly margin
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={hasData ? state === "PROFITABLE" ? "green" : "red" : "slate"}>{state}</StatusPill>
            <StatusPill tone="blue">{aggregates.months} Months</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Gross PnL" value={hasData ? eur(aggregates.pnlGross) : "—"} tone={hasData ? aggregates.pnlGross >= 0 ? "green" : "red" : "slate"} />
          <Metric label="Costs" value={hasData ? eur(aggregates.costs) : "—"} tone={hasData ? aggregates.costs > 0 ? "amber" : "slate" : "slate"} />
          <Metric label="Net PnL" value={hasData ? eur(aggregates.pnlNet) : "—"} tone={hasData ? aggregates.pnlNet >= 0 ? "green" : "red" : "slate"} />
          <Metric label="Net Margin" value={hasData ? pct(aggregates.margin) : "—"} tone={hasData ? aggregates.margin >= 0 ? "green" : "red" : "slate"} />
          <Metric label="Cost Ratio" value={hasData ? pct(aggregates.costRatio) : "—"} tone={hasData ? aggregates.costRatio > 30 ? "amber" : "blue" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>Profitability Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Profitability State</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{state}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Gross</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{eur(aggregates.pnlGross)}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Costs</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{eur(aggregates.costs)}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Net</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{eur(aggregates.pnlNet)}</div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Business Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${hasData ? aggregates.pnlNet >= 0 ? "text-emerald-400" : "text-red-400" : "text-slate-300"}`}>
                {hasData ? aggregates.pnlNet >= 0 ? "NET POSITIVE" : "NET NEGATIVE" : "DATA PENDING"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                {hasData
                  ? "Profitability tracking is ready, but monthly_pnl.json and monthly_costs.json are not yet populated for the current preproduction cycle."
                  : "Profitability tracking is ready, but monthly_pnl.json and monthly_costs.json are not yet populated for the current preproduction cycle."}
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-4">
          <Title right="Monthly view">Monthly Profitability</Title>

          <div className="grid grid-cols-[1fr_120px_120px_120px_90px_90px_120px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Month</div>
            <div>Gross PnL</div>
            <div>Costs</div>
            <div>Net PnL</div>
            <div>Gross %</div>
            <div>Net %</div>
            <div>Equity</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {monthly.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                No profitability data available yet. Monthly profitability will appear once monthly_pnl.json and monthly_costs.json are populated.
              </div>
            ) : monthly.map((m, idx) => {
              const gross = num(m?.pnl_gross_eur);
              const costs = num(m?.costs_eur);
              const net = num(m?.pnl_net_eur);
              return (
                <div key={idx} className="grid grid-cols-[1fr_120px_120px_120px_90px_90px_120px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-200">{monthLabel(m)}</div>
                  <div className={gross >= 0 ? "text-emerald-400" : "text-red-400"}>{eur(gross)}</div>
                  <div className="text-amber-300">{eur(costs)}</div>
                  <div className={net >= 0 ? "text-emerald-400" : "text-red-400"}>{eur(net)}</div>
                  <div className="text-slate-300">{pct(num(m?.pnl_gross_pct))}</div>
                  <div className="text-slate-300">{pct(num(m?.pnl_net_pct))}</div>
                  <div className="text-slate-300">{eur(m?.equity_eur)}</div>
                </div>
              );
            })}
          </div>
        </Box>
      </main>
    </div>
  );
}
