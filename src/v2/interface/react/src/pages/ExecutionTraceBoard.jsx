import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import StatusBadge from "../components/ui/StatusBadge";
import { fetchJson } from "../lib/apiClient";

const FALLBACK = {
  header: { planId: null, actionPolicy: "N/A", reasons: [] },
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
  return <div className={`rounded-xl border border-[#1f2a37] bg-[#09111a]/95 transition-all duration-300 hover:border-cyan-500/20 hover:shadow-[0_0_25px_rgba(34,211,238,0.06)] ${className}`}>{children}</div>;
}

function Title({ children, right }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-slate-200">{children}</h3>
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

export default function ExecutionTraceBoard() {
  const [data, setData] = useState(FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetchJson("/api/execution-trace", { timeoutMs: 8000 });
        if (!res?.ok) throw new Error(`HTTP ${res?.status || "FETCH_FAILED"}`);
        if (!cancelled) setData(res.data || FALLBACK);
      } catch {
        if (!cancelled) {
          setError("Unable to load execution trace.");
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
  const reasons = safeArray(data.header?.reasons);
  const executableCount = rows.filter((r) => r.execution_status === "EXECUTABLE").length;
  const blockedCount = rows.filter((r) => r.execution_status === "BLOCKED").length;
  const traceState = rows.length > 0 ? "TRACE READY" : "NO TRACE";
  const actionPolicy = data.header?.actionPolicy || "N/A";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Trace layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Execution Trace</h1>
            <p className="text-xs text-slate-400">
              Signal progression from candidate stage to final execution state
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone="amber">{String(actionPolicy).toUpperCase()}</StatusPill>
            <StatusPill tone={rows.length > 0 ? "green" : "slate"}>{traceState}</StatusPill>
            <StatusPill tone="blue">Plan {short(data.header?.planId, 18)}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-4 gap-3">
          <Metric label="Signals" value={rows.length} tone="blue" />
          <Metric label="Executable" value={executableCount} tone={executableCount > 0 ? "green" : "slate"} />
          <Metric label="Blocked" value={blockedCount} tone={blockedCount > 0 ? "red" : "green"} />
          <Metric label="Plan Reasons" value={reasons.length} tone="white" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Execution Narrative</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Policy</div>
                <div className="mt-1 truncate text-sm font-semibold text-amber-200" title={String(actionPolicy)}>
                  {short(actionPolicy, 18)}
                </div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Trace Flow</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{rows.length} signals</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Executable</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{executableCount}</div>
              </div>

              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Blocked</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{blockedCount}</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Trace Integrity</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${rows.length > 0 ? "text-emerald-400" : "text-slate-300"}`}>
                {traceState}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                This board verifies traceability between signal generation, candidate filtering, governance decisions and final execution eligibility.
              </div>
            </div>
          </Box>
        </div>

        <Box className="mb-3 p-3">
          <Title right="Signal, candidate and execution states by symbol">Execution Trace</Title>

          <div className="grid grid-cols-[1fr_70px_70px_70px_120px_120px_120px_1.2fr] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Symbol</div>
            <div>Side</div>
            <div>Qty</div>
            <div>Score</div>
            <div>Signal</div>
            <div>Candidate</div>
            <div>Execution</div>
            <div>Reason</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-6 text-sm leading-5 text-slate-400">
                No execution trace available for the current execution cycle. Trace rows will appear when signal candidates enter the execution pipeline.
              </div>
            ) : rows.map((row, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_70px_70px_70px_120px_120px_120px_1.2fr] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate"><SymbolCell symbol={row.symbol} /></div>
                <div><SideCell side={row.side} /></div>
                <div className="text-slate-300">{row.qty ?? "—"}</div>
                <div className="text-slate-300">{row.score ?? "—"}</div>
                <div><StatusBadge label={row.signal_status || "N/A"} /></div>
                <div><StatusBadge label={row.candidate_status || "N/A"} /></div>
                <div><StatusBadge label={row.execution_status || "N/A"} /></div>
                <div className="truncate text-slate-400" title={row.reason || "—"}>{row.reason || "—"}</div>
              </div>
            ))}
          </div>
        </Box>

        <Box className="p-3">
          <Title>Plan Reasons</Title>
          <div className="space-y-2">
            {reasons.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-6 text-sm leading-5 text-slate-400">
                No plan reason available for the current execution cycle.
              </div>
            ) : reasons.map((reason, idx) => (
              <div key={idx} className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-2 text-sm text-slate-300">
                {reason}
              </div>
            ))}
          </div>
        </Box>
      </main>
    </div>
  );
}
