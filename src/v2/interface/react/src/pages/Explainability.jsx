import React, { useEffect, useState } from "react";
import { fetchJson } from "../lib/apiClient";
import NscSidebar from "../components/layout/NscSidebar";


function Box({ children, className = "" }) {
  return (
    <div className={`rounded-xl border border-[#1f2a37] bg-[#0b111a] ${className}`}>
      {children}
    </div>
  );
}

function Metric({ label, value, tone = "white" }) {
  const tones = {
    white: "text-slate-100",
    green: "text-emerald-400",
    amber: "text-amber-300",
    red: "text-red-400",
    blue: "text-sky-300",
    slate: "text-slate-300",
  };

  return (
    <Box className="p-4">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-2 truncate text-xl font-semibold ${tones[tone] || tones.white}`}>
        {value ?? "n/a"}
      </div>
    </Box>
  );
}

function fmt(v) {
  if (v === null || v === undefined) return "n/a";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

function eur(v) {
  const n = Number(v || 0);
  return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} €`;
}

function pct(v) {
  const n = Number(v || 0);
  return `${(n * 100).toFixed(0)}%`;
}

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function prettyEngine(v) {
  return String(v || "pending").replaceAll("_", " ").toUpperCase();
}

function prettyRegime(v) {
  return String(v || "n/a").replaceAll("_", " ").toUpperCase();
}

export default function Explainability() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    try {
      const r = await fetchJson("/api/explainability", { timeoutMs: 8000 });

      if (!r.ok) {
        setError("Unable to load explainability layer.");
        return;
      }

      setData(r.data || {});
      setError(null);

    } catch (e) {
      setError("Unable to load explainability layer.");
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const market = typeof data?.market_regime === "object"
    ? data.market_regime
    : { regime: data?.market_regime, score: data?.market_score };
  const risk = data?.risk_limits || {
    risk_console_flag: data?.risk_flag,
    size_factor: data?.size_factor,
    max_positions: data?.max_positions,
    strategy_intensity_context: data?.strategy_reasoning || {},
  };
  const factors = risk.strategy_intensity_factors || data?.strategy_reasoning?.factors || {};
  const vetos = risk.strategy_vetos || {};
  const boosts = risk.strategy_boosts || {};
  const perf = data?.strategy_performance || {};
  const selector = data?.strategy_selector || { weights: data?.selector_weights || {}, diagnostics: {} };
  const diagnostics = selector.diagnostics || {};

  const strategies = ["momentum", "breakout", "whale", "sniper"];

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Explainability layer ready" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3">
          <h1 className="text-lg font-semibold uppercase tracking-wide">Explainability</h1>
          <p className="text-xs text-slate-400">
            Decision reasoning, veto logic, risk explanations and portfolio narrative layer
          </p>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Status" value={String(data?.status || "Loading").toUpperCase()} tone={data?.status === "ok" ? "green" : "slate"} />
          <Metric label="Backend" value={prettyEngine(data?.engine)} tone="blue" />
          <Metric label="Market Regime" value={prettyRegime(market.regime)} tone={String(market.regime).toLowerCase().includes("risk_on") ? "green" : "amber"} />
          <Metric label="Risk Flag" value={prettyRegime(risk.risk_console_flag)} tone={risk.risk_console_flag ? "amber" : "slate"} />
        </div>

        <Box className="mb-3 p-4">
          <div className="mb-3 text-sm font-semibold uppercase tracking-wide">Decision Narrative</div>
          <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
            {Array.isArray(data?.narrative) ? (
              data.narrative.map((line, i) => (
                <p key={i} className="mb-2 text-sm leading-5 text-slate-300">
                  {line}
                </p>
              ))
            ) : (
              <p className="text-sm leading-5 text-slate-300">
                {data?.narrative || "No narrative available."}
              </p>
            )}
          </div>
        </Box>

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Market Score" value={fmt(market.score || market.confidence)} tone="slate" />
          <Metric label="Size Factor" value={fmt(risk.size_factor)} tone="blue" />
          <Metric label="Max Positions" value={fmt(risk.max_positions)} tone="white" />
          <Metric label="Selector Weights" value={Object.keys(selector.weights || {}).length} tone="blue" />
        </div>

        <Box className="mb-3 p-4">
          <div className="mb-3 text-sm font-semibold uppercase tracking-wide">Strategy Reasoning</div>
          <div className="grid grid-cols-4 gap-3">
            {strategies.map((s) => {
              const veto = vetos[s];
              const boost = boosts[s];
              const tone = veto
                ? "border-red-400/30 bg-red-500/10 text-red-300"
                : boost
                  ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-300"
                  : "border-sky-500/20 bg-sky-500/5 text-sky-300";

              return (
                <div key={s} className={`rounded-lg border p-3 ${tone}`}>
                  <div className="text-[10px] uppercase tracking-wider opacity-80">{s}</div>
                  <div className="mt-2 text-2xl font-semibold">{factors[s] !== undefined ? fmt(factors[s]) : "READY"}</div>
                  <div className="mt-2 text-[11px] leading-4">
                    {veto ? `VETO — ${veto}` : boost ? `BOOST — ${boost}` : "Neutral"}
                  </div>
                </div>
              );
            })}
          </div>
        </Box>

        <Box className="p-4">
          <div className="mb-3 text-sm font-semibold uppercase tracking-wide">Strategy Performance & Selector</div>
          <div className="overflow-hidden rounded-lg border border-[#1c2633]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#0d1520] text-[10px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="p-3">Strategy</th>
                  <th className="p-3">Trades</th>
                  <th className="p-3">PnL</th>
                  <th className="p-3">Winrate</th>
                  <th className="p-3">Profit Factor</th>
                  <th className="p-3">Selector</th>
                  <th className="p-3">Label</th>
                </tr>
              </thead>
              <tbody>
                {strategies.map((s) => {
                  const p = perf[s] || {};
                  const d = diagnostics[s] || {};
                  return (
                    <tr key={s} className="border-t border-[#1c2633]">
                      <td className="p-3 font-semibold text-slate-100">{s}</td>
                      <td className="p-3 text-slate-300">{p.trades ?? d.trades ?? 0}</td>
                      <td className={num(p.pnl_total) >= 0 ? "p-3 text-emerald-400" : "p-3 text-red-400"}>{p.pnl_total !== undefined ? eur(p.pnl_total) : "n/a"}</td>
                      <td className="p-3 text-slate-300">{p.winrate !== undefined ? pct(p.winrate) : "n/a"}</td>
                      <td className="p-3 text-slate-300">{fmt(p.profit_factor)}</td>
                      <td className="p-3 text-slate-300">{fmt((selector.weights || {})[s])}</td>
                      <td className="p-3 text-slate-400">{d.label || "n/a"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Box>
      </main>
    </div>
  );
}
