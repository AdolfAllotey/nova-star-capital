import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import CryptoBadge from "../components/ui/CryptoBadge";
import { fetchJson } from "../lib/apiClient";

const FALLBACK = {
  header: { planId: null, actionPolicy: "N/A", reasons: [] },
  candidateOrders: [],
  executableOrders: [],
};

function safeArray(v) {
  return Array.isArray(v) ? v : [];
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

function OrderTable({ title, subtitle, rows, variant }) {
  return (
    <Box className="p-3">
      <Title right={subtitle}>{title}</Title>

      <div className="grid grid-cols-[1fr_70px_70px_70px_1.4fr] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
        <div>Symbol</div>
        <div>Side</div>
        <div>Qty</div>
        <div>{variant === "candidate" ? "Score" : "Type"}</div>
        <div>Reason</div>
      </div>

      <div className="space-y-2 pt-2">
        {rows.length === 0 ? (
          <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-5 text-sm text-slate-400">
            No {variant === "candidate" ? "candidate" : "executable"} orders.
          </div>
        ) : rows.map((row, idx) => (
          <div key={idx} className="grid grid-cols-[1fr_70px_70px_70px_1.4fr] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
            <div className="truncate"><SymbolCell symbol={row.symbol} /></div>
            <div><SideCell side={row.side} /></div>
            <div className="text-slate-300">{row.qty ?? "—"}</div>
            <div className="text-slate-300">{variant === "candidate" ? (row.score ?? "—") : (row.type || "—")}</div>
            <div className="truncate text-slate-400" title={row.reason || "—"}>{row.reason || "—"}</div>
          </div>
        ))}
      </div>
    </Box>
  );
}

export default function OrderBoard() {
  const [data, setData] = useState(FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetchJson("/api/order-board", { timeoutMs: 8000 });
        if (!res?.ok) throw new Error(`HTTP ${res?.status || "FETCH_FAILED"}`);
        if (!cancelled) setData(res.data || FALLBACK);
      } catch {
        if (!cancelled) {
          setError("Unable to load order board.");
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

  const candidateOrders = safeArray(data.candidateOrders);
  const executableOrders = safeArray(data.executableOrders);
  const reasons = safeArray(data.header?.reasons);
  const blockedOrders = Math.max(candidateOrders.length - executableOrders.length, 0);
  const actionPolicy = data.header?.actionPolicy || "N/A";
  const hasExecution = executableOrders.length > 0;

  const narrative = useMemo(() => {
    return [
      `Policy: ${short(actionPolicy, 18)}`,
      `Candidates: ${candidateOrders.length}`,
      `Executable: ${executableOrders.length}`,
      `Filtered: ${blockedOrders}`,
      `Plan: ${short(data.header?.planId, 18)}`,
    ];
  }, [actionPolicy, candidateOrders.length, executableOrders.length, blockedOrders, data.header?.planId]);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Execution layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Order Board</h1>
            <p className="text-xs text-slate-400">
              Pre-trade conversion, execution filtering and plan-level order governance
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone="amber">{String(actionPolicy).toUpperCase()}</StatusPill>
            <StatusPill tone={hasExecution ? "green" : "slate"}>{hasExecution ? "EXECUTABLE" : "NO EXECUTION"}</StatusPill>
            <StatusPill tone="blue">Plan {short(data.header?.planId, 18)}</StatusPill>
          </div>
        </div>

        {error ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {error}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-[1.15fr_1fr_1fr_1.15fr] gap-3">
          <Metric label="Candidate Orders" value={candidateOrders.length} tone="blue" />
          <Metric label="Executable Orders" value={executableOrders.length} tone={hasExecution ? "green" : "slate"} />
          <Metric label="Blocked / Filtered" value={blockedOrders} tone={blockedOrders > 0 ? "amber" : "green"} />
          <Metric label="Plan Reasons" value={reasons.length} tone="white" />
        </div>

        <div className="mb-3 grid grid-cols-[1.3fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Order Narrative</Title>

            <div className="grid grid-cols-[1.15fr_1fr_1fr_1.15fr] gap-3">

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Policy</div>
                <div className="mt-1 truncate whitespace-nowrap text-sm font-semibold text-amber-200" title={String(actionPolicy)}>
                  {short(actionPolicy, 18)}
                </div>
              </div>

              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Flow</div>
                <div className="mt-1 text-sm text-sky-200">
                  {candidateOrders.length} → {executableOrders.length}
                </div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Execution</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">
                  {hasExecution ? "ACTIVE" : "IDLE"}
                </div>
              </div>

              <div className="rounded-lg border border-slate-400/20 bg-slate-400/5 p-3">
                <div className="text-[10px] uppercase text-slate-300">Plan</div>
                <div className="mt-1 truncate text-sm text-slate-200" title={String(data.header?.planId || "—")}>
                  {short(data.header?.planId, 18)}
                </div>
              </div>

            </div>
          </Box>

          <Box className="p-3">
            <Title>Execution Policy</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Policy</div>
              <div className="mt-2 text-2xl font-semibold text-amber-300">{String(actionPolicy).toUpperCase()}</div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Orders remain governed by the current execution policy and preprod safety constraints.
              </div>
            </div>
          </Box>
        </div>

        <div className="mb-3 grid grid-cols-1 gap-3">
          <OrderTable title="Candidate Orders" subtitle="Signals eligible before final execution filtering" rows={candidateOrders} variant="candidate" />
          <OrderTable title="Executable Orders" subtitle="Orders retained by final execution plan" rows={executableOrders} variant="executable" />
        </div>

        <Box className="p-3">
          <Title>Plan Reasons</Title>
          <div className="space-y-2">
            {reasons.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] px-3 py-5 text-sm text-slate-400">
                No reasons available.
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
