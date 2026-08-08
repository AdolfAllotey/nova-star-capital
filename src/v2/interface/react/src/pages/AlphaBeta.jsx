import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson } from "../lib/apiClient";

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function fmt(v, digits = 3) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function pct(v, digits = 2) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

function signedPct(v, digits = 2) {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}${Math.abs(n * 100).toFixed(digits)}%`;
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

function Bar({ value, mode = "beta" }) {
  const v = Math.abs(num(value));
  const width = Math.max(0, Math.min(100, v * 100));
  const color =
    mode === "alpha"
      ? num(value) >= 0 ? "bg-emerald-400" : "bg-red-400"
      : v > 1 ? "bg-amber-400" : "bg-sky-400";

  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className={`h-1.5 rounded ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export default function AlphaBeta() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [payload, setPayload] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/alpha-beta/overview", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        const msg =
          r?.error?.detail?.detail ||
          r?.error?.detail ||
          r?.error?.message ||
          "";

        const msgStr = String(msg).toLowerCase();
        if (msgStr.includes("not found") || r?.error?.status === 404 || msgStr.includes("no α/β") || msgStr.includes("no α β")) {
          setPayload(null);
          setErr(null);
          setLoading(false);
          return;
        }

        setPayload(null);
        setErr("Unable to load Alpha / Beta data.");
        setLoading(false);
        return;
      }

      const data = r.data || null;
      if (data && typeof data.detail === "string") {
        const d = data.detail.toLowerCase();
        if (
          d.includes("no α/β") ||
          d.includes("no α β") ||
          d.includes("no alpha/beta")
        ) {
          setPayload(null);
          setErr(null);
          setLoading(false);
          return;
        }
      }

      setPayload(data);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 30000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const bricks = useMemo(() => {
    const arr = Array.isArray(payload?.bricks) ? payload.bricks : [];
    return arr.slice().sort((a, b) => num(b?.n_points) - num(a?.n_points));
  }, [payload]);

  const avgBeta = bricks.length ? bricks.reduce((s, b) => s + num(b.β ?? b.beta), 0) / bricks.length : 0;
  const avgAlpha = bricks.length ? bricks.reduce((s, b) => s + num(b.α ?? b.alpha), 0) / bricks.length : 0;
  const maxCorr = bricks.length ? Math.max(...bricks.map((b) => num(b.corr))) : 0;
  const totalPoints = bricks.reduce((s, b) => s + num(b.n_points), 0);
  const benchmark = payload?.benchmark?.name || payload?.benchmark?.id || "—";
  const hasData = bricks.length > 0 && totalPoints > 0;
  const alphaState = hasData
    ? avgAlpha >= 0 ? "ALPHA POSITIVE" : "ALPHA NEGATIVE"
    : "DATA PENDING";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Alpha / Beta layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-4 pt-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Alpha / Beta</h1>
            <p className="text-xs text-slate-400">
              Risk-adjusted attribution by brick: alpha, beta, correlation, R², volatility and benchmark sensitivity
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={hasData ? avgAlpha >= 0 ? "green" : "red" : "slate"}>{alphaState}</StatusPill>
            <StatusPill tone="blue">Benchmark {benchmark}</StatusPill>
            <StatusPill tone="slate">{bricks.length} Bricks</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Average Alpha" value={hasData ? signedPct(avgAlpha) : "—"} tone={hasData ? avgAlpha >= 0 ? "green" : "red" : "slate"} />
          <Metric label="Average Beta" value={hasData ? fmt(avgBeta, 2) : "—"} tone={hasData ? avgBeta > 1 ? "amber" : "blue" : "slate"} />
          <Metric label="Max Corr." value={hasData ? fmt(maxCorr, 2) : "—"} tone={hasData ? maxCorr > 0.8 ? "amber" : "green" : "slate"} />
          <Metric label="Data Points" value={totalPoints} tone="white" />
          <Metric label="Benchmark" value={benchmark} tone="blue" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-4">
            <Title right={loading ? "Loading" : "Live"}>Alpha / Beta Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Alpha State</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{alphaState}</div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Beta Load</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{fmt(avgBeta, 2)}</div>
              </div>

              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Coverage</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{totalPoints} pts</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Correlation</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{fmt(maxCorr, 2)}</div>
              </div>
            </div>
          </Box>

          <Box className="p-4">
            <Title>Risk-Adjusted Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${hasData ? avgAlpha >= 0 ? "text-emerald-400" : "text-red-400" : "text-slate-300"}`}>
                {hasData ? avgAlpha >= 0 ? "ALPHA GENERATION" : "ALPHA PRESSURE" : "DATA PENDING"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                {hasData
                  ? "This view tracks whether each sleeve creates independent return or mainly carries benchmark exposure."
                  : "The alpha_beta_engine is ready, but no statistical coverage is available yet for the current preproduction cycle."}
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-4">
          <Title right="By brick">Alpha / Beta Matrix</Title>

          <div className="grid grid-cols-[1fr_80px_80px_80px_80px_80px_90px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Brick</div>
            <div>Alpha</div>
            <div>Beta</div>
            <div>R²</div>
            <div>Corr.</div>
            <div>Vol.</div>
            <div>Points</div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-[#1c2633] bg-[#0d1520] p-3">
            {bricks.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#09111a] p-3 text-sm text-slate-400">
                No Alpha / Beta data available yet. Statistical attribution will appear once enough benchmark and brick return points are available.
              </div>
            ) : bricks.map((b) => {
              const alpha = b.α ?? b.alpha;
              const beta = b.β ?? b.beta;
              return (
                <div key={b.id || b.name} className="grid grid-cols-[1fr_80px_80px_80px_80px_80px_90px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-200">{b.name || b.id || "—"}</div>
                  <div className={num(alpha) >= 0 ? "text-emerald-400" : "text-red-400"}>{signedPct(alpha)}</div>
                  <div className="text-sky-300">{fmt(beta, 2)}</div>
                  <div className="text-slate-300">{fmt(b.r2, 2)}</div>
                  <div className="text-slate-300">{fmt(b.corr, 2)}</div>
                  <div className="text-slate-300">{pct(b.volatility)}</div>
                  <div className="text-slate-400">{b.n_points ?? "—"}</div>
                  <div className="col-span-7 grid grid-cols-[1fr_1fr] gap-3">
                    <Bar value={alpha} mode="alpha" />
                    <Bar value={beta} mode="beta" />
                  </div>
                </div>
              );
            })}
          </div>
        </Box>
      </main>
    </div>
  );
}
