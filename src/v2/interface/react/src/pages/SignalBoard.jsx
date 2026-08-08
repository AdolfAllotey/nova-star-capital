import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import StatusBadge from "../components/ui/StatusBadge";

const FALLBACK = {
  count: 0,
  rows: [],
  plan_id: null,
  action_policy: "N/A",
};

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function short(value, max = 26) {
  const s = String(value || "—");
  return s.length > max ? `${s.slice(0, max)}…` : s;
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

function SideCell({ side }) {
  const s = String(side || "—").toUpperCase();
  if (s === "BUY") return <span className="font-semibold text-emerald-400">BUY</span>;
  if (s === "SELL") return <span className="font-semibold text-red-400">SELL</span>;
  return <span className="text-slate-300">{s}</span>;
}

function SymbolCell({ symbol }) {
  if (!symbol) return <span className="text-slate-500">—</span>;
  return /usdt$|usdc$|btc$|eth$|eur$/i.test(symbol)
    ? <CryptoBadge symbol={symbol} />
    : <span className="font-medium text-white">{symbol}</span>;
}

export default function SignalBoard() {
  const [data, setData] = useState(FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetch(apiUrl("/api/signals/board"), {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json || FALLBACK);
      } catch {
        if (!cancelled) {
          setError("Unable to load signal board.");
          setData(FALLBACK);
        }
      }
    }

    load();
    const interval = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const rows = Array.isArray(data.rows) ? data.rows : [];
  const buyCount = rows.filter((r) => String(r.side || "").toUpperCase() === "BUY").length;
  const sellCount = rows.filter((r) => String(r.side || "").toUpperCase() === "SELL").length;
  const avgScore = rows.length ? rows.reduce((s, r) => s + num(r.score), 0) / rows.length : 0;
  const activeCount = rows.filter((r) => !["REJECTED", "BLOCKED", "N/A"].includes(String(r.status || "").toUpperCase())).length;

  const topSignal = useMemo(() => {
    if (!rows.length) return null;
    return [...rows].sort((a, b) => num(b.score) - num(a.score))[0];
  }, [rows]);

  const boardState = rows.length > 0 ? "SIGNALS READY" : "NO SIGNALS";
  const votedCount = rows.filter((r) => String(r.status || "").toUpperCase() === "VOTED").length;
  const softVetoCount = rows.filter((r) => String(r.status || "").toUpperCase() === "SOFT_VETO").length;

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Signal layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Signal Board</h1>
            <p className="text-xs text-slate-400">
              Signal generation board: candidate symbols, side, score, source and pre-execution status
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={rows.length > 0 ? "green" : "slate"}>{boardState}</StatusPill>
            <StatusPill tone="amber">{String(data.action_policy || "N/A").toUpperCase()}</StatusPill>
            <StatusPill tone="blue">Plan {short(data.plan_id, 18)}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Signals" value={rows.length} tone="blue" />
          <Metric label="Voted" value={votedCount} tone={votedCount > 0 ? "green" : "slate"} />
          <Metric label="Soft Veto" value={softVetoCount} tone={softVetoCount > 0 ? "amber" : "slate"} />
          <Metric label="BUY" value={buyCount} tone="green" />
          <Metric label="Avg Score" value={avgScore.toFixed(1)} tone={avgScore >= 70 ? "green" : avgScore >= 50 ? "amber" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right="Live">Signal Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Board State</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{boardState}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Buy Flow</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{buyCount}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Soft Vetos</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{softVetoCount}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Top Signal</div>
                <div className="mt-1 truncate text-sm font-semibold text-amber-200">{topSignal?.symbol || "None"}</div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Signal Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${rows.length > 0 ? "text-emerald-400" : "text-slate-300"}`}>
                {rows.length > 0 ? "SIGNAL FLOW" : "FLAT"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Signal Board is upstream from Order Board. It shows what the engines produce before conversion into executable candidates.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-4">
          <Title right="Generated candidates">Signals</Title>

          <div className="grid grid-cols-[1fr_80px_90px_80px_110px_130px_130px_1.3fr] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Symbol</div>
            <div>Side</div>
            <div>Qty / €</div>
            <div>Score</div>
            <div>Status</div>
            <div>Strategy</div>
            <div>Source</div>
            <div>Reason</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                No signals available.
              </div>
            ) : rows.map((row, idx) => (
              <div key={row.id || idx} className="grid grid-cols-[1fr_80px_90px_80px_110px_130px_130px_1.3fr] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate"><SymbolCell symbol={row.symbol} /></div>
                <div><SideCell side={row.side} /></div>
                <div className="text-slate-300">{row.qty ?? "—"}</div>
                <div className={num(row.score) >= 70 ? "font-semibold text-emerald-400" : num(row.score) >= 50 ? "font-semibold text-amber-300" : "font-semibold text-sky-300"}>
                  {row.score ?? "—"}
                </div>
                <div><StatusBadge label={row.status || "N/A"} /></div>
                <div className="truncate text-slate-300">{row.strategy || "—"}</div>
                <div className="truncate text-slate-500">{row.source || "—"}</div>
                <div className="truncate text-slate-400" title={row.reason || "—"}>{row.reason || "—"}</div>
              </div>
            ))}
          </div>
        </Box>
      </main>
    </div>
  );
}
