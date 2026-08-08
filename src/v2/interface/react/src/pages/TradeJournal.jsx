import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson } from "../lib/apiClient";

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function eur(v) {
  return `${num(v).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} €`;
}

function shortTs(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("fr-FR");
  } catch {
    return value;
  }
}


function cleanSymbol(v) {
  const s = String(v || "").trim();
  if (!s || s.toUpperCase() === "UNKNOWN") return "Unknown asset";
  return s.toUpperCase();
}

function cleanSide(row) {
  const raw = String(row?.side || row?.action || "").toUpperCase();
  if (raw === "BUY" || raw === "LONG") return "BUY";
  if (raw === "SELL" || raw === "SHORT") return "SELL";
  return "—";
}

function sideClass(v) {
  if (v === "BUY") return "text-emerald-400";
  if (v === "SELL") return "text-red-400";
  return "text-slate-400";
}

function qualityBadge(row) {
  const symbol = String(row?.symbol || "").toUpperCase();
  const hasGap = !symbol || symbol === "UNKNOWN" || Number(row?.entry_price || 0) === 0;

  if (hasGap) {
    return (
      <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-300">
        DATA GAP
      </span>
    );
  }

  return (
    <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-300">
      OK
    </span>
  );
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

export default function TradeJournal() {
  const [data, setData] = useState({ summary: {}, rows: [] });
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const r = await fetchJson("/api/trade-journal-state", { timeoutMs: 8000 });

      if (cancelled) return;

      if (!r.ok) {
        setErr("Unable to load trade journal.");
        setData({ summary: {}, rows: [] });
        return;
      }

      setErr("");
      setData(r.data || { summary: {}, rows: [] });
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const summary = data?.summary || {};
  const rows = Array.isArray(data?.rows) ? data.rows : [];

  const pnl = num(summary.total_realized_pnl_eur);
  const openPositions = num(summary.open_positions_count);
  const simulations = num(summary.trade_simulation_count);
  const rowCount = num(summary.rows_count || rows.length);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Trade journal online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Trade Journal</h1>
            <p className="text-xs text-slate-400">
              Execution footprint, simulated trades, realized PnL and recent trading history
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={pnl >= 0 ? "green" : "red"}>PnL {eur(pnl)}</StatusPill>
            <StatusPill tone="blue">{rowCount} Rows</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Rows" value={rowCount} />
          <Metric label="Open Positions" value={openPositions} tone={openPositions > 0 ? "green" : "slate"} />
          <Metric label="Trade Simulations" value={simulations} tone="blue" />
          <Metric label="Realized PnL" value={eur(pnl)} tone={pnl >= 0 ? "green" : "red"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right="Live">Journal Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Rows</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{rowCount}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Open Positions</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{openPositions}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Simulations</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{simulations}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Realized</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{eur(pnl)}</div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Journal Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {pnl >= 0 ? "POSITIVE" : "NEGATIVE"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                The journal consolidates simulated trade activity and execution footprint for monitoring and auditability.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-4">
          <Title right="Recent rows">Recent Trades</Title>

          <div className="grid grid-cols-[130px_1.1fr_110px_70px_100px_90px_90px_110px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Timestamp</div>
            <div>Symbol</div>
            <div>Strategy</div>
            <div>Side</div>
            <div>Notional</div>
            <div>PnL</div>
            <div>Source</div>
            <div>Execution</div>
            <div>Quality</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                No trade journal data available.
              </div>
            ) : rows.slice(0, 30).map((row, idx) => {
              const realized = num(row.realized_pnl);
              return (
                <div key={idx} className="grid grid-cols-[130px_1.1fr_110px_70px_100px_90px_90px_110px_90px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-400">{shortTs(row.ts)}</div>
                  <div className="truncate text-slate-200">{cleanSymbol(row.symbol)}</div>
                  <div className="truncate text-slate-400">{row.strategy || "—"}</div>
                  <div className={sideClass(cleanSide(row))}>{cleanSide(row)}</div>
                  <div className="text-slate-300">{eur(row.notional_eur || 0)}</div>
                  <div className={realized >= 0 ? "text-emerald-400" : "text-red-400"}>{eur(realized)}</div>
                  <div className="truncate text-slate-500">{row.source || "—"}</div>
                  <div className="truncate text-slate-500">{row.execution_mode || row.action || "—"}</div>
                  <div>{qualityBadge(row)}</div>
                </div>
              );
            })}
          </div>
        </Box>
      </main>
    </div>
  );
}
