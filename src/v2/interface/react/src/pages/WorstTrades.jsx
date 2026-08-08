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

function money(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return eur(v);
}

function formatDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return String(d);
  return dt.toLocaleString("fr-FR");
}

function getTradeDate(t) {
  return t?.timestamp || t?.opened_at || t?.entry_time || t?.ts || null;
}

function getLossValue(t) {
  const raw = t?.loss_eur ?? t?.pnl_eur ?? t?.pnl ?? t?.realized_pnl_eur ?? t?.realized_pnl ?? null;
  const n = Number(raw);
  return Number.isNaN(n) ? null : n;
}


function pillClass(tone = "slate") {
  const tones = {
    green: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    red: "border-red-500/30 bg-red-500/10 text-red-300",
    blue: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    slate: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  };
  return tones[tone] || tones.slate;
}

function strategyLabel(t) {
  return t?.strategy || t?.raw?.strategy || "unknown";
}

function riskModeLabel(t) {
  return t?.risk_mode || t?.raw?.risk_mode || "—";
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

export default function WorstTrades() {
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(20);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const [tradesRes, summaryRes] = await Promise.all([
          fetchJson("/risk/worst-trades", { timeoutMs: 8000 }),
          fetchJson("/risk/worst-trades/summary", { timeoutMs: 8000 }),
        ]);

        if (!tradesRes?.ok) throw new Error("worst-trades fetch failed");
        if (!summaryRes?.ok) throw new Error("worst-trades summary fetch failed");

        const tradesData = tradesRes.data;
        const summaryData = summaryRes.data;

        const items = Array.isArray(tradesData)
          ? tradesData
          : Array.isArray(tradesData?.trades)
            ? tradesData.trades
            : Array.isArray(tradesData?.items)
              ? tradesData.items
              : [];

        const derivedUpdatedAt =
          summaryData?.context?.generated_at ||
          summaryData?.updated_at ||
          items.map(getTradeDate).filter(Boolean).sort().slice(-1)[0] ||
          null;

        if (!cancelled) {
          setTrades(items);
          setSummary(summaryData || null);
          setUpdatedAt(derivedUpdatedAt);
        }
      } catch {
        if (!cancelled) setError("Unable to load worst trades.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    const id = setInterval(fetchData, 30000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const stats = useMemo(() => {
    if (!trades.length) {
      return { count: 0, totalLoss: 0, avgLoss: 0, worstLoss: 0 };
    }

    const numeric = trades.map(getLossValue).filter((v) => v !== null);
    const losses = numeric.filter((v) => v < 0);

    if (!losses.length) {
      return {
        count: trades.length,
        totalLoss: num(summary?.metrics?.total_pnl_eur),
        avgLoss: num(summary?.metrics?.avg_pnl_eur),
        worstLoss: 0,
      };
    }

    const totalLoss = losses.reduce((a, b) => a + b, 0);
    const avgLoss = totalLoss / losses.length;
    const worstLoss = Math.min(...losses);

    return { count: trades.length, totalLoss, avgLoss, worstLoss };
  }, [trades, summary]);

  const visibleTrades = useMemo(() => trades.slice(0, limit), [trades, limit]);
  const summaryText = summary?.summary || "No backend risk summary available.";
  const summaryCount = Number(summary?.metrics?.n_worst || 0);
  const consistencyGap = summaryCount > 0 && summaryCount !== trades.length;
  const llmStatus = summary?.llm_status || "unknown";
  const riskState = stats.totalLoss < 0 ? "LOSS REVIEW" : "CLEAN";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Post-trade risk online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Worst Trades</h1>
            <p className="text-xs text-slate-400">
              Post-mortem risk analysis, largest realized losses, fragile setups and blacklist intelligence
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={trades.length > 0 ? "amber" : "slate"}>{trades.length > 0 ? "DATA AVAILABLE" : "NO DATA"}</StatusPill>
            <StatusPill tone="blue">Trades {stats.count}</StatusPill>
            {consistencyGap ? <StatusPill tone="amber">Summary gap</StatusPill> : null}
            <StatusPill tone="slate">{updatedAt ? `Updated ${formatDate(updatedAt)}` : "NO TIMESTAMP"}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Analyzed Trades" value={stats.count} />
          <Metric label="Total Loss" value={money(stats.totalLoss)} tone={stats.totalLoss < 0 ? "red" : "slate"} />
          <Metric label="Average Loss" value={money(stats.avgLoss)} tone={stats.avgLoss < 0 ? "red" : "slate"} />
          <Metric label="Worst Loss" value={money(stats.worstLoss)} tone={stats.worstLoss < 0 ? "red" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>Loss Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Risk State</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{riskState}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Dataset</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{stats.count} trades</div>
              </div>

              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Worst</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{money(stats.worstLoss)}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Refresh</div>
                <div className="mt-1 truncate text-sm font-semibold text-sky-200">
                  {updatedAt ? formatDate(updatedAt) : "n/a"}
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Risk Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${stats.totalLoss < 0 ? "text-red-400" : "text-emerald-400"}`}>
                {stats.totalLoss < 0 ? "POST-MORTEM" : "CLEAN"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                This page isolates losing trades from market scanning. It is used for risk learning, weak-pattern detection and blacklist recommendations.
              </div>
            </div>
          </Box>
        </div>

        <Box className="mb-3 p-4">
          <Title right="Backend synthesis">Risk Summary</Title>
          <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4 text-sm leading-6 text-slate-300">
            <div>{summaryText}</div>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${pillClass(llmStatus === "skipped_uninformative" ? "amber" : "blue")}`}>
                LLM {llmStatus}
              </span>

              {consistencyGap ? (
                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${pillClass("amber")}`}>
                  Summary {summaryCount} / API {trades.length}
                </span>
              ) : (
                <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${pillClass("green")}`}>
                  Summary aligned
                </span>
              )}
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3">
            <Metric label="Worst Trades Count" value={summary?.metrics?.n_worst ?? "—"} />
            <Metric label="Total PnL" value={money(summary?.metrics?.total_pnl_eur)} tone={num(summary?.metrics?.total_pnl_eur) < 0 ? "red" : "green"} />
            <Metric label="Average PnL" value={money(summary?.metrics?.avg_pnl_eur)} tone={num(summary?.metrics?.avg_pnl_eur) < 0 ? "red" : "green"} />
          </div>
        </Box>

        <Box className="p-4">
          <Title right="Detailed loss list">Worst Trades Table</Title>

          <div className="grid grid-cols-[0.9fr_150px_90px_120px_80px_100px_110px_110px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Token</div>
            <div>Date</div>
            <div>Exchange</div>
            <div>Strategy</div>
            <div>Risk</div>
            <div>Amount</div>
            <div>Notional</div>
            <div>PnL</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {loading && !trades.length ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                Loading worst trades...
              </div>
            ) : visibleTrades.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                No worst trades available.
              </div>
            ) : visibleTrades.map((t, i) => {
              const pnl = getLossValue(t);
              return (
                <div key={`${t.token || t.symbol || "trade"}-${i}`} className="grid grid-cols-[0.9fr_150px_90px_120px_80px_100px_110px_110px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate font-semibold text-slate-200">{t.token || t.symbol || "—"}</div>
                  <div className="truncate text-slate-400">{formatDate(getTradeDate(t))}</div>
                  <div className="truncate text-slate-400">{t.exchange || "—"}</div>
                  <div className="truncate text-slate-300">{strategyLabel(t)}</div>
                  <div className="truncate text-amber-300">{riskModeLabel(t)}</div>
                  <div className="text-slate-300">{money(t.amount)}</div>
                  <div className="text-slate-300">{money(t.notional_eur)}</div>
                  <div className={pnl !== null && pnl < 0 ? "font-semibold text-red-400" : "text-slate-300"}>{pnl === null ? "—" : money(pnl)}</div>
                </div>
              );
            })}
          </div>

          {trades.length > limit ? (
            <button
              onClick={() => setLimit((v) => v + 20)}
              className="mt-4 rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2 text-sm text-slate-200 hover:bg-[#111827]"
            >
              Show more
            </button>
          ) : null}
        </Box>
      </main>
    </div>
  );
}
