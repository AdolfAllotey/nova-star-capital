import { buildApiUrl } from "../lib/apiBase";
import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import LongTermMiniCurve from "../components/longterm/LongTermMiniCurve";
import { formatEur, formatPct } from "../utils/formatters";

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function toneClass(v) {
  return Number(v || 0) >= 0 ? "text-emerald-400" : "text-red-400";
}

function prettyLabel(value) {
  const map = {
    crypto: "Crypto",
    equity: "Equities",
    equities_offensive: "Offensive Equities",
    broker_account: "Broker Account",
    cold_wallet: "Cold Wallet",
    exchange_wallet: "Exchange Wallet",
    etf: "ETF",
    bond: "Bond",
  };
  return map[value] || value || "—";
}

function sortRows(obj, field = "market_value_eur") {
  return Object.entries(obj || {}).sort(
    (a, b) => Number(b?.[1]?.[field] || 0) - Number(a?.[1]?.[field] || 0)
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

function AllocationBar({ value }) {
  const width = Math.max(0, Math.min(100, num(value)));
  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className="h-1.5 rounded bg-blue-500" style={{ width: `${width}%` }} />
    </div>
  );
}

function AssetCell({ symbol }) {
  if (!symbol) return <span className="text-slate-500">—</span>;
  return /usdt$|usdc$|btc$|eth$|eur$|btc|eth|sol|bnb|xrp|avax|matic/i.test(symbol)
    ? <CryptoBadge symbol={symbol} />
    : <span className="font-medium text-white">{symbol}</span>;
}

export default function LongTerm() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetch(buildApiUrl("/api/long-term/valuation"));
        if (!res.ok) throw new Error(`valuation ${res.status}`);
        const payload = await res.json();
        if (!cancelled) setData(payload);
      } catch {
        if (!cancelled) {
          setError("Unable to load Long Term consolidated data.");
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

  const totals = data?.totals || {};
  const byAssetClass = data?.by_asset_class || {};
  const bySourceBrick = data?.by_source_brick || {};
  const positions = Array.isArray(data?.positions) ? data.positions : [];
  const fx = data?.fx || {};

  const sourceRows = useMemo(() => sortRows(bySourceBrick), [bySourceBrick]);
  const assetRows = useMemo(() => sortRows(byAssetClass), [byAssetClass]);

  const topPosition = positions.length
    ? [...positions].sort((a, b) => Number(b?.market_value_eur || 0) - Number(a?.market_value_eur || 0))[0]
    : null;

  const totalValue = num(totals.market_value_eur);
  const invested = num(totals.invested_eur);
  const pnl = num(totals.pnl_eur);
  const pnlPct = num(totals.pnl_pct);
  const holdings = Number(totals.positions || positions.length || 0);

  const cryptoCount = positions.filter((p) => String(p.asset_class || "").toLowerCase().includes("crypto")).length;
  const equityCount = positions.filter((p) => String(p.asset_class || "").toLowerCase().includes("equity")).length;

  if (error) {
    return (
      <div className="min-h-screen bg-[#05080d] text-slate-100">
        <NscSidebar footerText="Long Term layer online" />
        <main className="ml-[235px] w-[calc(100%-235px)] p-3">
          <Box className="border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{error}</Box>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#05080d] text-slate-100">
        <NscSidebar footerText="Long Term layer online" />
        <main className="ml-[235px] w-[calc(100%-235px)] p-3 text-sm text-slate-400">
          Loading Long Term portfolio...
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Long Term layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Long Term</h1>
            <p className="text-xs text-slate-400">
              Strategic patrimonial sleeve: crypto majors, global equities, ETFs and long-duration holdings
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone="blue">Holdings {holdings}</StatusPill>
            <StatusPill tone="green">Value {formatEur(totalValue)}</StatusPill>
            <StatusPill tone={pnl >= 0 ? "green" : "red"}>PnL {formatEur(pnl, { signed: true })}</StatusPill>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Invested Capital" value={formatEur(invested)} />
          <Metric label="Market Value" value={formatEur(totalValue)} tone="blue" />
          <Metric label="Total PnL" value={formatEur(pnl, { signed: true })} tone={pnl >= 0 ? "green" : "red"} />
          <Metric label="Total Return" value={formatPct(pnlPct, { signed: true })} tone={pnlPct >= 0 ? "green" : "red"} />
          <Metric label="Top Holding" value={topPosition?.symbol || "—"} tone="amber" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Strategic">Long Term Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Market Value</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{formatEur(totalValue)}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Crypto Majors</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{cryptoCount}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Equities / ETF</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{equityCount}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Largest Holding</div>
                <div className="mt-1 truncate text-sm font-semibold text-amber-200">{topPosition?.symbol || "None"}</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Valuation Curve</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
              <LongTermMiniCurve />
            </div>
          </Box>
        </div>

        <div className="mb-3 grid grid-cols-[1fr_1fr] gap-3">
          <Box className="p-3">
            <Title>By Asset Class</Title>
            <div className="space-y-2">
              {assetRows.length === 0 ? (
                <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                  No asset class data available.
                </div>
              ) : assetRows.map(([key, row]) => {
                const share = totalValue > 0 ? (num(row.market_value_eur) / totalValue) * 100 : 0;
                return (
                  <div key={key} className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
                    <div className="grid grid-cols-[1fr_100px_90px] items-center gap-2 text-xs">
                      <div>
                        <div className="text-slate-200">{prettyLabel(row.asset_class || key)}</div>
                        <div className="text-[10px] text-slate-500">{Number(row.positions || 0)} positions</div>
                      </div>
                      <div className="text-right text-slate-300">{formatEur(row.market_value_eur)}</div>
                      <div className={`text-right ${toneClass(row.pnl_eur)}`}>{formatEur(row.pnl_eur, { signed: true })}</div>
                    </div>
                    <div className="mt-2 grid grid-cols-[1fr_45px] items-center gap-2">
                      <AllocationBar value={share} />
                      <div className="text-right text-[10px] text-slate-500">{share.toFixed(1)}%</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Box>

          <Box className="p-3">
            <Title>By Source Brick</Title>
            <div className="space-y-2">
              {sourceRows.length === 0 ? (
                <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                  No source brick data available.
                </div>
              ) : sourceRows.map(([key, row]) => {
                const share = totalValue > 0 ? (num(row.market_value_eur) / totalValue) * 100 : 0;
                return (
                  <div key={key} className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2">
                    <div className="grid grid-cols-[1fr_100px_90px] items-center gap-2 text-xs">
                      <div>
                        <div className="text-slate-200">{prettyLabel(row.source_brick || key)}</div>
                        <div className="text-[10px] text-slate-500">{Number(row.positions || 0)} positions</div>
                      </div>
                      <div className="text-right text-slate-300">{formatEur(row.market_value_eur)}</div>
                      <div className={`text-right ${toneClass(row.pnl_eur)}`}>{formatEur(row.pnl_eur, { signed: true })}</div>
                    </div>
                    <div className="mt-2 grid grid-cols-[1fr_45px] items-center gap-2">
                      <AllocationBar value={share} />
                      <div className="text-right text-[10px] text-slate-500">{share.toFixed(1)}%</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right={`${positions.length} active holdings`}>Holdings Inventory</Title>

          <div className="grid grid-cols-[1fr_110px_110px_110px_110px_90px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Asset</div>
            <div>Source</div>
            <div>Class</div>
            <div>Invested</div>
            <div>Market Value</div>
            <div>PnL</div>
            <div>Return</div>
          </div>

          <div className="space-y-2 pt-2">
            {positions.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No long-term holding available.
              </div>
            ) : positions.map((row, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_110px_110px_110px_110px_90px_90px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate"><AssetCell symbol={row.symbol} /></div>
                <div className="truncate text-slate-400">{prettyLabel(row.source_brick)}</div>
                <div className="truncate text-slate-400">{prettyLabel(row.asset_class)}</div>
                <div className="text-slate-300">{formatEur(row.invested_eur)}</div>
                <div className="text-slate-300">{formatEur(row.market_value_eur)}</div>
                <div className={toneClass(row.pnl_eur)}>{formatEur(row.pnl_eur, { signed: true })}</div>
                <div className={toneClass(row.pnl_pct)}>{formatPct(row.pnl_pct, { signed: true })}</div>
              </div>
            ))}
          </div>
        </Box>

        <div className="mt-3 text-[10px] text-slate-600">
          Last refresh: {String(data?.updated_at || "n/a").slice(0, 19).replace("T", " ")}
          {fx?.usd_to_eur_rate ? ` · USD/EUR: ${Number(fx.usd_to_eur_rate).toFixed(6)} · ${fx.source || "fx"}` : ""}
        </div>
      </main>
    </div>
  );
}
