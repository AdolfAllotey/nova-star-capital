import { API_BASE, buildApiUrl as apiUrl } from "../lib/apiBase";
import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";


function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
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

function mapModeToLabel(mode) {
  switch ((mode || "").toLowerCase()) {
    case "risk_on":
    case "bull":
      return "RISK ON";
    case "risk_off":
    case "bear":
      return "RISK OFF";
    case "neutral":
      return "NEUTRAL";
    default:
      return "UNKNOWN";
  }
}

function mapModeToDescription(mode) {
  switch ((mode || "").toLowerCase()) {
    case "risk_on":
    case "bull":
      return "Constructive risk-on regime with broader risk appetite and stronger momentum tolerance.";
    case "risk_off":
    case "bear":
      return "Defensive risk-off regime with tighter risk, lower aggression and stronger capital protection.";
    case "neutral":
      return "Balanced regime with selective risk-taking and moderated conviction.";
    default:
      return "The market regime engine requires valid market inputs before its reading can be trusted.";
  }
}

function regimeTone(mode) {
  switch ((mode || "").toLowerCase()) {
    case "risk_on":
    case "bull":
      return "green";
    case "risk_off":
    case "bear":
      return "red";
    case "neutral":
      return "amber";
    default:
      return "slate";
  }
}

export default function MarketRegime() {
  const [regime, setRegime] = useState(null);
  const [riskLimits, setRiskLimits] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(buildUrl("/dashboard/market_regime"), { credentials: "include" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) setRegime(data);
      } catch {
        if (!cancelled) setError("Unable to load market regime.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const mode = regime?.regime || regime?.mode || "unknown";
  const modeLabel = mapModeToLabel(mode || "unknown");
  const description = mapModeToDescription(mode);
  const rawScore = typeof regime?.confidence === "number" ? regime.confidence : (typeof regime?.score === "number" ? regime.score : null);
  const score = String(regime?.status || "").toLowerCase() === "insufficient_data" ? 0 : rawScore;
  const source = regime?.source || regime?.status || "market_regime_detector";
  const updatedAt = regime?.updated_at || null;
  const tone = regimeTone(mode);
  const intensity = mode && String(mode).toLowerCase() !== "unknown" && score !== null ? Math.max(0, Math.min(100, num(score) * 100)) : 0;

  const components = regime?.components || {};
  const componentRows = [
    { label: "Trend", value: components.trend, hint: "QQQ / SPY trend" },
    { label: "Volatility", value: components.volatility, hint: "VIX regime" },
    { label: "Breadth", value: components.breadth, hint: regime?.inputs?.breadth_status || "market width" },
    { label: "Macro", value: components.macro, hint: regime?.inputs?.macro_status || "macro layer" },
    { label: "Data Quality", value: regime?.data_quality, hint: "input reliability" },
    { label: "Raw Score", value: regime?.raw_score, hint: "pre-confidence regime score" },
  ];

  const fmtComponent = (v) => {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "n/a";
    return Number(v).toFixed(2);
  };

  const safeRiskLimits = riskLimits || {};
  const strategyFactors = safeRiskLimits.strategy_intensity_factors || {};
  const strategyVetos = safeRiskLimits.strategy_vetos || {};
  const strategyBoosts = safeRiskLimits.strategy_boosts || {};
  const strategyContext = safeRiskLimits.strategy_intensity_context || {};

  const strategyRows = ["momentum", "breakout", "whale", "sniper"].map((key) => ({
    key,
    factor: strategyFactors[key],
    veto: strategyVetos[key],
    boost: strategyBoosts[key],
  }));

  const breadthValue = Number(components.breadth ?? 0);
  const macroValue = Number(components.macro ?? 0);

  let effectiveNscIntensity = intensity;

  if (breadthValue <= 0) effectiveNscIntensity *= 0.90;
  if (macroValue < 0) effectiveNscIntensity *= 0.90;
  if (String(mode).toLowerCase() === "risk_off") effectiveNscIntensity *= 0.50;
  if (String(mode).toLowerCase() === "unknown") effectiveNscIntensity = 0;

  effectiveNscIntensity = Math.max(0, Math.min(100, effectiveNscIntensity));

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Market regime online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Market Regime</h1>
            <p className="text-xs text-slate-400">
              Global market reading used to drive system intensity, capital posture and risk governance
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={tone}>{modeLabel}</StatusPill>
            <StatusPill tone="blue">{source}</StatusPill>
            <StatusPill tone="slate">{updatedAt ? new Date(updatedAt).toLocaleString("fr-FR") : "NO TIMESTAMP"}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Detected State" value={loading ? "LOADING" : modeLabel} tone={tone} />
          <Metric label="Internal Score" value={score !== null ? score.toFixed(2) : "n/a"} tone={tone} />
          <Metric label="Engine Source" value={source} tone="blue" />
          <Metric label="Intensity" value={`${intensity.toFixed(0)}%`} tone={tone} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>Regime Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Regime</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{modeLabel}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Risk Appetite</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">
                  {["bull", "risk_on"].includes(String(mode).toLowerCase()) ? "HIGH" : ["bear", "risk_off"].includes(String(mode).toLowerCase()) ? "LOW" : "MODERATE"}
                </div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Conviction</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{score !== null ? score.toFixed(2) : "n/a"}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Source</div>
                <div className="mt-1 truncate text-sm font-semibold text-violet-200">{source}</div>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase text-slate-500">
                <span>Regime intensity</span>
                <span>{intensity.toFixed(0)}%</span>
              </div>
              <div className="h-2 rounded bg-[#1a2532]">
                <div className="h-2 rounded bg-blue-500" style={{ width: `${intensity}%` }} />
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Regime Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${
                tone === "green" ? "text-emerald-400" : tone === "red" ? "text-red-400" : tone === "amber" ? "text-amber-300" : "text-slate-300"
              }`}>
                {modeLabel}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">{description}</div>
            </div>
          </Box>
        </div>

        <Box className="mb-3 p-4">
          <Title>Effective NSC Intensity</Title>
          <div className="grid grid-cols-[1fr_2fr] gap-3">
            <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-4">
              <div className="text-[10px] uppercase tracking-wider text-emerald-300">Recommended Intensity</div>
              <div className="mt-2 text-3xl font-semibold text-emerald-300">{effectiveNscIntensity.toFixed(0)}%</div>
              <div className="mt-1 text-xs text-slate-400">Market confidence adjusted by breadth and macro pressure.</div>
            </div>

            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase text-slate-500">
                <span>Effective deployment bar</span>
                <span>{effectiveNscIntensity.toFixed(0)}%</span>
              </div>
              <div className="h-2 rounded bg-[#1a2532]">
                <div className="h-2 rounded bg-emerald-400" style={{ width: `${effectiveNscIntensity}%` }} />
              </div>
              <div className="mt-3 text-sm text-slate-300">
                Current reading: risk-on is allowed, but breadth is neutral and macro is slightly negative, so NSC should remain offensive but not fully aggressive.
              </div>
            </div>
          </div>
        </Box>

        <Box className="mb-3 p-4">
          <Title>Market Regime Components</Title>
          <div className="grid grid-cols-6 gap-3">
            {componentRows.map((row) => {
              const value = Number(row.value ?? 0);
              const localTone = value > 0.25 ? "text-emerald-300" : value < -0.25 ? "text-red-300" : "text-amber-300";
              return (
                <div key={row.label} className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">{row.label}</div>
                  <div className={`mt-2 text-xl font-semibold ${localTone}`}>{fmtComponent(row.value)}</div>
                  <div className="mt-1 text-[10px] text-slate-500">{row.hint}</div>
                </div>
              );
            })}
          </div>
        </Box>

        <Box className="mb-3 p-4">
          <Title>Strategy V3 — Boosts & Vetos</Title>

          <div className="grid grid-cols-4 gap-3">
            {strategyRows.map((row) => {
              const blocked = Boolean(row.veto);
              const boosted = Boolean(row.boost);
              const toneClass = blocked
                ? "border-red-400/30 bg-red-500/10 text-red-300"
                : boosted
                  ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-300"
                  : "border-slate-500/20 bg-[#0d1520] text-slate-300";

              return (
                <div key={row.key} className={`rounded-lg border p-3 ${toneClass}`}>
                  <div className="text-[10px] uppercase tracking-wider opacity-80">{row.key}</div>
                  <div className="mt-2 text-2xl font-semibold">
                    {row.factor !== undefined && row.factor !== null ? Number(row.factor).toFixed(2) : "n/a"}
                  </div>
                  <div className="mt-2 text-[11px] leading-4">
                    {row.veto ? `VETO — ${row.veto}` : row.boost ? `BOOST — ${row.boost}` : "Neutral"}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-3 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Strategy Context</div>
            <div className="mt-2 text-xs text-slate-300">
              Engine: {strategyContext.engine || "n/a"} · Trend: {strategyContext.trend ?? "n/a"} · Volatility: {strategyContext.volatility ?? "n/a"} · Breadth: {strategyContext.breadth ?? "n/a"} · Macro: {strategyContext.macro ?? "n/a"}
            </div>
            {Array.isArray(strategyContext.rules) && strategyContext.rules.length ? (
              <ul className="mt-2 list-disc pl-5 text-xs text-slate-400">
                {strategyContext.rules.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            ) : null}
          </div>
        </Box>

        <Box className="p-4">
          <Title>Impact on NSC</Title>

          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Sizing</div>
              <div className="mt-2 text-sm text-slate-300">
                Position sizing and system aggressiveness adapt to the detected regime.
              </div>
            </div>

            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Portfolio Posture</div>
              <div className="mt-2 text-sm text-slate-300">
                Portfolio posture shifts between offensive deployment and capital protection.
              </div>
            </div>

            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Strategy Gating</div>
              <div className="mt-2 text-sm text-slate-300">
                Regime state gates or amplifies specific strategy families in future versions.
              </div>
            </div>
          </div>
        </Box>
      </main>
    </div>
  );
}
