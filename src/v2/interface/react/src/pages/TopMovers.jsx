import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson } from "../lib/apiClient";

function getChg24h(item) {
  const v = item?.chg_24h ?? item?.change_24h ?? item?.pct_24h ?? item?.percent_24h ?? null;
  const n = typeof v === "number" ? v : v !== null ? Number(v) : NaN;
  return Number.isNaN(n) ? null : n;
}

function num(v, fallback = null) {
  if (v === null || v === undefined) return fallback;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? fallback : n;
}

function price(v) {
  const n = num(v);
  if (n === null) return "—";
  return n >= 1 ? n.toFixed(2) : n.toFixed(6);
}

function pct(v) {
  const n = num(v);
  if (n === null) return "—";
  return `${n.toFixed(2)}%`;
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

function TokenRow({ rank, item, type }) {
  const chg = getChg24h(item);
  const symbol = String(item.symbol || item.id || "—").toUpperCase();
  const name = item.name || item.id || symbol;
  const tone = type === "gainer" ? "text-emerald-400" : "text-red-400";

  return (
    <div className="grid grid-cols-[40px_1fr_110px_90px_120px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
      <div className="text-slate-500">#{rank}</div>
      <div className="truncate">
        <div className="text-slate-200">{name}</div>
        <div className="flex gap-1 text-[10px] text-slate-500">
          <span>{symbol}</span>
          {item.tradable ? <span className="text-emerald-300">TRADABLE</span> : null}
        </div>
      </div>
      <div className="text-right text-slate-300">{price(item.price)}</div>
      <div className={`text-right font-semibold ${tone}`}>{pct(chg)}</div>
      <div className="text-right">
        <span className="rounded-md border border-slate-600/40 bg-slate-700/20 px-2 py-1 text-[10px] uppercase text-slate-300">
          {item.source || item.preferred_exchange || "—"}
        </span>
      </div>
    </div>
  );
}

export default function TopMovers() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [rawData, setRawData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/market/top-movers", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr("Unable to load top movers.");
        setRawData(null);
        setLoading(false);
        return;
      }

      setRawData(r.data);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const updatedAt = rawData && typeof rawData === "object" ? rawData.updated_at || null : null;

  const items = useMemo(() => {
    if (!rawData) return [];
    if (Array.isArray(rawData)) return rawData;
    if (Array.isArray(rawData.items)) return rawData.items;
    return [];
  }, [rawData]);

  const { gainers, losers } = useMemo(() => {
    const withChange = items
      .map((it) => ({ ...it, __chg: getChg24h(it) }))
      .filter((it) => typeof it.__chg === "number" && it.__chg !== null);

    return {
      gainers: [...withChange].filter((it) => it.__chg > 0).sort((a, b) => b.__chg - a.__chg).slice(0, 10),
      losers: [...withChange].filter((it) => it.__chg < 0).sort((a, b) => a.__chg - b.__chg).slice(0, 10),
    };
  }, [items]);

  const best = gainers[0]?.__chg ?? null;
  const worst = losers[0]?.__chg ?? null;
  const marketState = gainers.length > losers.length ? "MOMENTUM POSITIVE" : losers.length > gainers.length ? "PRESSURE" : "BALANCED";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Market scanner online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-4 rounded-3xl border border-cyan-400/10 bg-gradient-to-r from-[#07111c] via-[#0b1623] to-[#05080d] p-5 shadow-[0_0_60px_rgba(34,211,238,0.06)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.28em] text-cyan-300">Market Scanner</div>
              <h1 className="mt-1 text-2xl font-semibold uppercase tracking-wide">Top Movers</h1>
              <p className="mt-1 text-sm text-slate-400">
                Premium 24h scanner for upside momentum, downside pressure, tradability and source confirmation.
              </p>
            </div>

            <div className="flex gap-2">
              <StatusPill tone={marketState === "MOMENTUM POSITIVE" ? "green" : marketState === "PRESSURE" ? "red" : "blue"}>{marketState}</StatusPill>
              <StatusPill tone="slate">{items.length} Assets</StatusPill>
            </div>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Assets Scanned" value={items.length} tone="blue" />
          <Metric label="Gainers" value={gainers.length} tone="green" />
          <Metric label="Losers" value={losers.length} tone={losers.length > 0 ? "red" : "slate"} />
          <Metric label="Best 24h" value={best === null ? "—" : pct(best)} tone="green" />
          <Metric label="Worst 24h" value={worst === null ? "—" : pct(worst)} tone="red" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>Market Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Scanner State</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{loading ? "LOADING" : "ACTIVE"}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Upside</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{gainers.length}</div>
              </div>

              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Downside</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{losers.length}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Updated</div>
                <div className="mt-1 truncate text-sm font-semibold text-violet-200">
                  {updatedAt ? new Date(updatedAt).toLocaleString("fr-FR") : "n/a"}
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Market Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${marketState === "MOMENTUM POSITIVE" ? "text-emerald-400" : marketState === "PRESSURE" ? "text-red-400" : "text-sky-300"}`}>
                {marketState}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Top Movers is a market-scanning page. It should stay separate from Worst Trades, which is post-trade risk analysis.
              </div>
            </div>
          </Box>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Box className="p-4">
            <Title right="24h upside">Top Gainers</Title>
            <div className="grid grid-cols-[40px_1fr_110px_90px_120px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
              <div>#</div><div>Token</div><div className="text-right">Price</div><div className="text-right">24h</div><div className="text-right">Source</div>
            </div>
            <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
              {gainers.length === 0 ? (
                <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                  No gainer detected.
                </div>
              ) : gainers.map((it, idx) => <TokenRow key={it.id || it.symbol || idx} rank={idx + 1} item={it} type="gainer" />)}
            </div>
          </Box>

          <Box className="p-4">
            <Title right="24h downside">Top Losers</Title>
            <div className="grid grid-cols-[40px_1fr_110px_90px_120px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
              <div>#</div><div>Token</div><div className="text-right">Price</div><div className="text-right">24h</div><div className="text-right">Source</div>
            </div>
            <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
              {losers.length === 0 ? (
                <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                  No loser detected.
                </div>
              ) : losers.map((it, idx) => <TokenRow key={it.id || it.symbol || idx} rank={idx + 1} item={it} type="loser" />)}
            </div>
          </Box>
        </div>
      </main>
    </div>
  );
}
