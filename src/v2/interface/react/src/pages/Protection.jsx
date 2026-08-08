import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";

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

export default function Protection() {
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const res = await fetch(apiUrl("/dashboard/v3"), { credentials: "include", cache: "no-store" });
      const json = res?.ok ? await res.json() : null;
      if (!cancelled) setDashboard(json);
    }

    load();
    const id = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const global = dashboard?.global || {};
  const rows = Array.isArray(global.protectionSummary) ? global.protectionSummary : [];

  const protectedBricks = rows.filter((r) => String((r.protectionStatuses || []).join(",")).toUpperCase().includes("PROTECTED")).length;
  const protectedPositions = rows.reduce((s, r) => s + Number(r.protectedPositionsCount || 0), 0);
  const trailingHits = rows.reduce((s, r) => s + Number(r.trailingHitCount || 0), 0);

  const killSwitch = String(global.killSwitch || global.kill_switch || "OFF").toUpperCase();
  const governanceMode = String(global.governanceMode || "UNKNOWN").toUpperCase();
  const actionPolicy = String(global.masterAuditGovernancePolicy || global.actionPolicy || "UNAVAILABLE").toUpperCase();
  const hardBlock = Boolean(global.globalAuditBlocking || global.masterAuditHardBlock || killSwitch === "ON");
  const protectionState = String(global.protectionLevel || (hardBlock ? "BLOCKED" : "PROTECTED")).toUpperCase();

  const riskFlags = Number(global.riskFlags || 0);
  const cashBufferPct = Number(global.cashAvailable || 0) / Math.max(1, Number(global.capitalObserved || 1));
  const maxDriftPct = Number(global.maxDriftPct ?? global.maxDrift ?? 0);
  const effectiveRiskState = hardBlock ? "BLOCKED" : riskFlags > 0 ? "WATCH" : "PROTECTED";

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Protection layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <header className="mb-3 rounded-2xl border border-[#1f2a37] bg-[radial-gradient(circle_at_top_left,#102033_0%,#09111a_42%,#05080d_100%)] p-3 shadow-[0_0_50px_rgba(34,211,238,0.08)]">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold uppercase tracking-wide">Protection Command Center</h1>
              <p className="text-xs text-slate-400">
                Kill-switch, protected positions, trailing protection and governance safety posture
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatusPill tone={protectionState === "PROTECTED" ? "green" : protectionState === "BLOCKED" ? "red" : "blue"}>{protectionState}</StatusPill>
              <StatusPill tone={killSwitch === "ON" ? "red" : "green"}>Kill Switch {killSwitch}</StatusPill>
              <StatusPill tone={hardBlock ? "red" : "green"}>{hardBlock ? "Hard Block" : "No Blocking"}</StatusPill>
              <StatusPill tone="amber">{actionPolicy}</StatusPill>
            </div>
          </div>
        </header>

        <Box className="mb-3 border-cyan-500/15 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.12),rgba(7,17,29,0.96)_38%,rgba(5,8,13,0.98)_100%)] p-3">
          <div className="grid grid-cols-[1.1fr_0.9fr_0.9fr_0.9fr] gap-3">
            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">Protection State</div>
              <div className={`mt-2 text-3xl font-semibold ${protectionState === "BLOCKED" ? "text-red-300" : "text-emerald-300"}`}>
                {protectionState}
              </div>
              <div className="mt-2 text-[11px] leading-4 text-slate-400">
                Portfolio remains protected under simulated governance. Real execution remains disabled.
              </div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Governance Safety</div>
              <div className={`mt-2 text-2xl font-semibold ${hardBlock ? "text-red-300" : "text-emerald-300"}`}>
                {hardBlock ? "BLOCKED" : "OPEN"}
              </div>
              <div className="mt-3 text-[10px] text-slate-400">Mode {governanceMode}</div>
              <div className="mt-1 text-[10px] text-slate-400">Policy {actionPolicy}</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Risk Protection</div>
              <div className={`mt-2 text-2xl font-semibold ${effectiveRiskState === "WATCH" ? "text-amber-300" : effectiveRiskState === "BLOCKED" ? "text-red-300" : "text-emerald-300"}`}>
                {effectiveRiskState}
              </div>
              <div className="mt-3 text-[10px] text-slate-400">Risk flags {riskFlags}</div>
              <div className="mt-1 text-[10px] text-slate-400">Cash buffer {(cashBufferPct * 100).toFixed(1)}%</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Trailing Layer</div>
              <div className="mt-2 text-2xl font-semibold text-sky-300">{trailingHits}</div>
              <div className="mt-3 text-[10px] text-slate-400">Protected positions {protectedPositions}</div>
              <div className="mt-1 text-[10px] text-slate-400">Protected bricks {protectedBricks}</div>
            </div>
          </div>
        </Box>

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Protected Bricks" value={protectedBricks} tone={protectedBricks > 0 ? "green" : "slate"} />
          <Metric label="Protected Positions" value={protectedPositions} tone={protectedPositions > 0 ? "green" : "slate"} />
          <Metric label="Trailing Hits" value={trailingHits} tone={trailingHits > 0 ? "amber" : "slate"} />
          <Metric label="Kill Switch" value={killSwitch} tone={killSwitch === "ON" ? "red" : "green"} />
          <Metric label="Governance" value={global.governanceMode || "UNKNOWN"} tone="amber" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Protection Command</Title>
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Protection State</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{protectionState}</div>
              </div>
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Protected</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{protectedPositions} positions</div>
              </div>
              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Trailing Hits</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{trailingHits}</div>
              </div>
              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Kill Switch</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{killSwitch}</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Protection Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className="mt-2 text-2xl font-semibold text-emerald-400">{protectionState}</div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Protection remains monitored at sleeve level. Kill-switch and trailing protection are visible here before execution governance.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right="Protection by brick">Protection Summary</Title>

          <div className="grid grid-cols-[1fr_140px_120px_110px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Brick</div>
            <div>Status</div>
            <div>Protected Pos.</div>
            <div>Trailing Hits</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.length === 0 ? (
              <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No protection data available.
              </div>
            ) : rows.map((row, idx) => {
              const status = (row.protectionStatuses || []).join(", ") || "NONE";
              const isProtected = String(status).toUpperCase().includes("PROTECTED");
              return (
                <div key={idx} className="grid grid-cols-[1fr_140px_120px_110px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                  <div className="truncate text-slate-200">{row.brick || "—"}</div>
                  <div className={isProtected ? "text-emerald-400" : "text-slate-400"}>{status}</div>
                  <div className="text-slate-300">{row.protectedPositionsCount ?? 0}</div>
                  <div className="text-slate-300">{row.trailingHitCount ?? 0}</div>
                </div>
              );
            })}
          </div>
        </Box>
      </main>
    </div>
  );
}
