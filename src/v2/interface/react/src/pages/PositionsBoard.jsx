import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import StatusBadge from "../components/ui/StatusBadge";
import { fetchJson } from "../lib/apiClient";

const FALLBACK = {
  summary: {
    openPositions: 0,
    grossExposureEur: 0,
    netExposureEur: 0,
  },
  rows: [],
};

function safeArray(v) {
  return Array.isArray(v) ? v : [];
}

function eur(v) {
  const n = Number(v || 0);
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
}

function short(v, max = 24) {
  const s = String(v || "—");
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


function humanSymbol(symbol) {
  const s = String(symbol || "").toUpperCase();

  const map = {
    BTCUSDT: ["Bitcoin", "BTC/USDT"],
    ETHUSDT: ["Ethereum", "ETH/USDT"],
    MATICUSDT: ["Polygon", "MATIC/USDT"],
    SHIBUSDT: ["SHIB", "SHIB/USDT"],
    DOGEUSDT: ["Dogecoin", "DOGE/USDT"],
    XRPUSDT: ["XRP", "XRP/USDT"],
    SOLUSDT: ["Solana", "SOL/USDT"],
  };

  return map[s] || [s, ""];
}

function HumanSymbolCell({ symbol }) {
  const [name, pair] = humanSymbol(symbol);

  return (
    <div className="flex min-w-0 items-center gap-2">
      <div className="shrink-0">
        <CryptoBadge symbol={symbol} />
      </div>
      <div className="min-w-0">
        <div className="truncate font-semibold text-slate-100">{name}</div>
        {pair ? <div className="truncate text-[10px] text-slate-500">{pair}</div> : null}
      </div>
    </div>
  );
}

function SymbolCell({ symbol }) {
  if (!symbol) {
    return <span className="text-slate-500">—</span>;
  }

  const raw = String(symbol).toUpperCase();

  const MAP = {
    BTCUSDT: ["Bitcoin", "BTC/USDT"],
    ETHUSDT: ["Ethereum", "ETH/USDT"],
    MATICUSDT: ["Polygon", "MATIC/USDT"],
    SHIBUSDT: ["SHIB", "SHIB/USDT"],
    XRPUSDT: ["XRP", "XRP/USDT"],
    DOGEUSDT: ["Dogecoin", "DOGE/USDT"],
  };

  const [name, pair] = MAP[raw] || [raw.replace("USDT", ""), raw];

  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="shrink-0">
        <CryptoBadge symbol={symbol} />
      </div>

      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-slate-100">
          {name}
        </div>

        <div className="truncate text-[10px] text-slate-500">
          {pair}
        </div>
      </div>
    </div>
  );
}


function normalizeOpenPortfolioPosition(p) {
  const symbol = p?.symbol || p?.token || p?.asset || "—";
  const qty = Number(p?.remaining_size ?? p?.size ?? p?.qty ?? 0);
  const entry = Number(p?.entry_price ?? p?.avg_price ?? 0);
  const notional = Number(p?.notional_eur ?? p?.notional_usd ?? p?.value_eur ?? p?.value_usd ?? 0);
  const status = p?.closed ? "CLOSED" : (p?.status || "OPEN");

  return {
    symbol,
    side: p?.side || "long",
    qty,
    entry_price: entry,
    notional_eur: notional,
    status,
    execution_mode: p?.execution_mode || p?.action || "UNAVAILABLE",
    pnl: Number(p?.realized_pnl ?? p?.pnl ?? p?.pnl_eur ?? 0),
    strategy: p?.strategy || "—",
  };
}

function buildPositionsBoardFromOpenPortfolio(payload) {
  const sourceRows = safeArray(payload?.positions || payload?.data?.positions);
  const rows = sourceRows
    .filter((p) => !p?.closed && Number(p?.remaining_size ?? p?.size ?? 0) > 0)
    .map(normalizeOpenPortfolioPosition);

  const grossExposureEur = rows.reduce((s, r) => s + Number(r.notional_eur || 0), 0);
  const longCount = rows.filter((r) => ["BUY", "LONG"].includes(String(r.side || "").toUpperCase())).length;
  const shortCount = rows.filter((r) => ["SELL", "SHORT"].includes(String(r.side || "").toUpperCase())).length;

  return {
    summary: {
      openPositions: rows.length,
      grossExposureEur,
      netExposureEur: grossExposureEur,
      longCount,
      shortCount,
    },
    rows,
  };
}


function fmtQty(v) {
  const n = Number(v || 0);

  if (n >= 1000000) return `${(n / 1000000).toFixed(2)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(2)}K`;
  if (n >= 1) return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });

  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 8,
  });
}

function fmtPrice(v) {
  const n = Number(v || 0);

  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  if (n >= 1) return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  if (n >= 0.0001) return n.toLocaleString("fr-FR", { maximumFractionDigits: 4 });

  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 8,
    maximumFractionDigits: 8,
  });
}

function SideCell({ side }) {
  const normalized = String(side || "").toUpperCase();
  if (normalized === "BUY" || normalized === "LONG") {
    return <span className="font-semibold text-emerald-400">LONG</span>;
  }
  if (normalized === "SELL" || normalized === "SHORT") {
    return <span className="font-semibold text-red-400">SHORT</span>;
  }
  return <span className="text-slate-300">{side || "—"}</span>;
}

export default function PositionsBoard() {
  const [data, setData] = useState(FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetchJson("/api/positions-board", { timeoutMs: 8000 });

        if (res?.ok && Array.isArray(res.data?.rows) && res.data.rows.length > 0) {
          if (!cancelled) setData(res.data || FALLBACK);
          return;
        }

        const openRes = await fetchJson("/portfolio/open", { timeoutMs: 8000 });
        if (!openRes?.ok) throw new Error(`HTTP ${openRes?.status || "FETCH_FAILED"}`);

        if (!cancelled) {
          setData(buildPositionsBoardFromOpenPortfolio(openRes.data));
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load positions board.");
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
  const gross = Number(data.summary?.grossExposureEur ?? data.summary?.grossExposureUsd ?? 0);
  const net = Number(data.summary?.netExposureEur ?? data.summary?.netExposureUsd ?? 0);
  const open = Number(data.summary?.openPositions ?? rows.length ?? 0);

  const exposureState = rows.length > 0 ? "DEPLOYED" : "FLAT";
  const longCount = rows.filter((r) => ["BUY", "LONG"].includes(String(r.side || "").toUpperCase())).length;
  const shortCount = rows.filter((r) => ["SELL", "SHORT"].includes(String(r.side || "").toUpperCase())).length;

  const largestPosition = useMemo(() => {
    return [...rows].sort((a, b) => Number(b.notional_eur || 0) - Number(a.notional_eur || 0))[0] || null;
  }, [rows]);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Positions layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Positions Board</h1>
            <p className="text-xs text-slate-400">
              Live book monitoring, active exposure, side balance and current position state
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={rows.length > 0 ? "green" : "slate"}>{exposureState}</StatusPill>
            <StatusPill tone="blue">Gross {eur(gross)}</StatusPill>
            <StatusPill tone="blue">Net {eur(net)}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Open Positions" value={open} tone={open > 0 ? "green" : "slate"} />
          <Metric label="Gross Exposure" value={eur(gross)} tone="blue" />
          <Metric label="Net Exposure" value={eur(net)} tone="blue" />
          <Metric label="Long / Short" value={`${longCount} / ${shortCount}`} tone="white" />
          <Metric label="Largest Position" value={largestPosition ? humanSymbol(largestPosition.symbol)[0] : "—"} tone="amber" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Position Narrative</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Book State</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{exposureState}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Exposure</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{eur(gross)}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Side Balance</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{longCount} long · {shortCount} short</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Concentration</div>
                <div className="mt-1 truncate text-sm font-semibold text-amber-200">
                  {largestPosition ? humanSymbol(largestPosition.symbol)[0] : "No position"}
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Risk Overlay</Title>
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Positions" value={rows.length} />
              <Metric label="Long" value={longCount} tone="green" />
              <Metric label="Short" value={shortCount} tone={shortCount > 0 ? "red" : "slate"} />
            </div>

            <div className="mt-3 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-300">
              {rows.length > 0
                ? "Live exposure is active and should be monitored against governance and risk limits."
                : "The live book is currently flat with no active exposure."}
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right="Current live book by symbol and side">Open Positions</Title>

          <div className="grid grid-cols-[2.2fr_90px_110px_110px_120px_130px_130px_100px] gap-3 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Symbol</div>
            <div>Side</div>
            <div>Qty</div>
            <div>Entry</div>
            <div>Notional EUR</div>
            <div>Strategy</div>
            <div>Mode</div>
            <div>Status</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No open positions.
              </div>
            ) : rows.map((row, idx) => (
              <div key={idx} className="grid grid-cols-[2.2fr_90px_110px_110px_120px_130px_130px_100px] items-center gap-3 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate">
                  <SymbolCell symbol={row.symbol} />
                </div>
                <div><SideCell side={row.side} /></div>
                <div className="font-mono tabular-nums text-slate-300">{fmtQty(row.qty)}</div>
                <div className="font-mono tabular-nums text-slate-300">{fmtPrice(row.entry_price)}</div>
                <div className="text-slate-300">{eur(row.notional_eur)}</div>
                <div className="truncate text-slate-300">{row.strategy || "—"}</div>
                <div>
                  <span className={`rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                    !row.execution_mode
                      ? "border-slate-500/30 bg-slate-500/10 text-slate-400"
                      : String(row.execution_mode).includes("SIMULATED")
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                        : String(row.execution_mode).includes("LIVE")
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                          : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                  }`}>
                    {row.execution_mode || "UNAVAILABLE"}
                  </span>
                </div>
                <div><StatusBadge label={row.status || "OPEN"} /></div>
              </div>
            ))}
          </div>
        </Box>
      </main>
    </div>
  );
}
