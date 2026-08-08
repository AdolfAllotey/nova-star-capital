import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import StatusBadge from "../components/ui/StatusBadge";
import { fetchJson } from "../lib/apiClient";

const FALLBACK = {
  summary: { fillsCount: 0, buyCount: 0, sellCount: 0 },
  rows: [],
};

function safeArray(v) {
  return Array.isArray(v) ? v : [];
}

function short(value, max = 24) {
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
      <div className={`mt-1 truncate text-lg font-semibold ${tones[tone] || tones.white}`} title={String(value)}>
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


function fmtQty(v) {
  const n = Number(v || 0);
  if (n >= 1000000) return `${(n / 1000000).toFixed(2)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(2)}K`;
  if (n >= 1) return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 4, maximumFractionDigits: 8 });
}

function eur(v) {
  const n = Number(v || 0);
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} €`;
}

function shortDate(v) {
  if (!v) return "—";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v).slice(0, 16);
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
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

export default function FillsBoard() {
  const [data, setData] = useState(FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetchJson("/api/fills-board", { timeoutMs: 8000 });
        if (!res?.ok) throw new Error(`HTTP ${res?.status || "FETCH_FAILED"}`);
        if (!cancelled) setData(res.data || FALLBACK);
      } catch {
        if (!cancelled) {
          setError("Unable to load fills board.");
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

  const rows = safeArray(data.rows);
  const fills = Number(data.summary?.fillsCount ?? rows.length ?? 0);
  const buys = Number(data.summary?.buyCount ?? 0);
  const sells = Number(data.summary?.sellCount ?? 0);
  const streamState = rows.length > 0 ? "ACTIVE" : "EMPTY";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Fills layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Fills Board</h1>
            <p className="text-xs text-slate-400">
              Simulated execution history, fill stream monitoring and side distribution
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={rows.length > 0 ? "green" : "slate"}>{rows.length > 0 ? "FILLS AVAILABLE" : "NO FILLS"}</StatusPill>
            <StatusPill tone="green">BUY {buys}</StatusPill>
            <StatusPill tone={sells > 0 ? "red" : "slate"}>SELL {sells}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Total Fills" value={fills} tone={fills > 0 ? "green" : "slate"} />
          <Metric label="BUY Fills" value={buys} tone="green" />
          <Metric label="SELL Fills" value={sells} tone={sells > 0 ? "red" : "slate"} />
          <Metric label="Stream State" value={streamState} tone={streamState === "ACTIVE" ? "green" : "slate"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Fills Narrative</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Fill Stream</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{streamState}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Completion</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{fills} fills</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Buy Flow</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{buys}</div>
              </div>

              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Sell Flow</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{sells}</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Execution Quality</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${rows.length > 0 ? "text-emerald-400" : "text-slate-300"}`}>
                {rows.length > 0 ? "RECORDED" : "NO FILLS"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                This board tracks simulated broker execution history and recent fill events.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right="Most recent simulated executions">Recent Fills</Title>

          <div className="grid grid-cols-[105px_1.2fr_1fr_70px_80px_100px_140px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Time</div>
            <div>Plan</div>
            <div>Symbol</div>
            <div>Side</div>
            <div>Qty</div>
            <div>Fill Price</div>
            <div>Policy</div>
            <div>Status</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No fills available.
              </div>
            ) : rows.map((row, idx) => (
              <div key={idx} className="grid grid-cols-[105px_1.2fr_1fr_70px_80px_100px_140px_90px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate text-slate-300">{shortDate(row.ts)}</div>
                <div className="truncate text-slate-400" title={row.plan_id || ""}>{short(row.plan_id, 24)}</div>
                <div className="truncate"><SymbolCell symbol={row.symbol} /></div>
                <div><SideCell side={row.side} /></div>
                <div className="font-mono tabular-nums text-slate-300">{fmtQty(row.qty)}</div>
                <div className="font-mono tabular-nums text-slate-300">{eur(row.fill_price)}</div>
                <div>
                  <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                    !row.policy
                      ? "border-slate-500/30 bg-slate-500/10 text-slate-400"
                      : String(row.policy).includes("SIMULATED")
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                        : String(row.policy).includes("LIVE")
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                          : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                  }`}>
                    {row.policy || "UNAVAILABLE"}
                  </span>
                </div>
                <div><StatusBadge label={row.status || "N/A"} /></div>
              </div>
            ))}
          </div>
        </Box>
      </main>
    </div>
  );
}
