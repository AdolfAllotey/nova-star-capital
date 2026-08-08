import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson, apiUrl } from "../lib/apiClient";

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

function stringify(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export default function Anomalies() {
  const [aggregatorAudit, setAggregatorAudit] = useState(null);
  const [alignmentAudit, setAlignmentAudit] = useState(null);
  const [bridgeAudit, setBridgeAudit] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [auditRes, alignmentRes, bridgeRes] = await Promise.all([
        fetchJson("/api/aggregator-audit", { timeoutMs: 8000 }),
        fetchJson("/api/execution-plan", { timeoutMs: 8000 }),
        fetchJson("/api/rebalance-plan", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      setAggregatorAudit(auditRes?.ok ? auditRes.data : null);
      setAlignmentAudit(alignmentRes?.ok ? {
        status: alignmentRes.data?.blocked ? "blocked" : "ok",
        blockers: Array.isArray(alignmentRes.data?.block_reasons) ? alignmentRes.data.block_reasons : []
      } : null);
      setBridgeAudit(bridgeRes?.ok ? {
        status: "derived",
        warnings: Array.isArray(bridgeRes.data?.warnings) ? bridgeRes.data.warnings : []
      } : null);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const anomalies = Array.isArray(aggregatorAudit?.anomalies) ? aggregatorAudit.anomalies : [];
  const warnings = Array.isArray(aggregatorAudit?.warnings) ? aggregatorAudit.warnings : [];
  const blockers = Array.isArray(alignmentAudit?.blockers) ? alignmentAudit.blockers : [];
  const bridgeWarnings = Array.isArray(bridgeAudit?.warnings) ? bridgeAudit.warnings : [];

  const totalWarnings = warnings.length + bridgeWarnings.length;
  const totalIssues = anomalies.length + totalWarnings + blockers.length;

  const severity =
    blockers.length > 0 || anomalies.length > 0
      ? "HIGH"
      : totalWarnings > 0
        ? "MEDIUM"
        : "LOW";

  const issueRows = useMemo(() => {
    return [
      ...anomalies.map((x, idx) => ({ source: "Aggregator", type: "Anomaly", level: "HIGH", payload: x, key: `a-${idx}` })),
      ...warnings.map((x, idx) => ({ source: "Aggregator", type: "Warning", level: "MEDIUM", payload: x, key: `w-${idx}` })),
      ...blockers.map((x, idx) => ({ source: "Execution Alignment", type: "Blocker", level: "HIGH", payload: x, key: `b-${idx}` })),
      ...bridgeWarnings.map((x, idx) => ({ source: "Bridge", type: "Warning", level: "MEDIUM", payload: x, key: `bw-${idx}` })),
    ];
  }, [anomalies, warnings, blockers, bridgeWarnings]);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Anomaly layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold uppercase tracking-wide">Anomalies</h1>
            <p className="text-xs text-slate-400">
              Aggregator issues, warnings, blockers and execution-alignment anomalies
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={severity === "LOW" ? "green" : severity === "MEDIUM" ? "amber" : "red"}>{severity}</StatusPill>
            <StatusPill tone={totalIssues > 0 ? "amber" : "green"}>{totalIssues} Issues</StatusPill>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Total Issues" value={totalIssues} tone={totalIssues > 0 ? "amber" : "green"} />
          <Metric label="Anomalies" value={anomalies.length} tone={anomalies.length > 0 ? "red" : "green"} />
          <Metric label="Warnings" value={totalWarnings} tone={totalWarnings > 0 ? "amber" : "green"} />
          <Metric label="Blockers" value={blockers.length} tone={blockers.length > 0 ? "red" : "green"} />
          <Metric label="Audit Status" value={aggregatorAudit?.status || "UNKNOWN"} tone="blue" />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Live">Anomaly Command</Title>

            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Anomalies</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{anomalies.length}</div>
              </div>

              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Warnings</div>
                <div className="mt-1 text-sm font-semibold text-amber-200">{totalWarnings}</div>
              </div>

              <div className="rounded-lg border border-red-400/20 bg-red-400/5 p-3">
                <div className="text-[10px] uppercase text-red-300">Blockers</div>
                <div className="mt-1 text-sm font-semibold text-red-200">{blockers.length}</div>
              </div>

              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">System</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">
                  {totalIssues > 0 ? "WATCH" : "CLEAN"}
                </div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Anomaly Reading</Title>
            <div className="rounded-lg border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${severity === "LOW" ? "text-emerald-400" : severity === "MEDIUM" ? "text-amber-300" : "text-red-400"}`}>
                {severity === "LOW" ? "CLEAN" : severity === "MEDIUM" ? "WATCH" : "REVIEW"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                This page centralizes issues coming from portfolio aggregation, rebalance bridge and execution alignment.
              </div>
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right="Issue feed">Issue Log</Title>

          <div className="grid grid-cols-[130px_120px_80px_1fr] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Source</div>
            <div>Type</div>
            <div>Level</div>
            <div>Details</div>
          </div>

          <div className="space-y-2 pt-2">
            {issueRows.length === 0 ? (
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-emerald-100">
                No anomaly, warning or blocker detected.
              </div>
            ) : issueRows.map((row) => (
              <div key={row.key} className="grid grid-cols-[130px_120px_80px_1fr] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div className="truncate text-slate-300">{row.source}</div>
                <div className="text-slate-300">{row.type}</div>
                <div className={row.level === "HIGH" ? "text-red-400" : "text-amber-300"}>{row.level}</div>
                <div className="truncate text-slate-400" title={stringify(row.payload)}>{stringify(row.payload)}</div>
              </div>
            ))}
          </div>
        </Box>

        <div className="mt-3 text-[10px] text-slate-600">
          Sources: {apiUrl("/api/aggregator-audit")} · {apiUrl("/api/execution-plan")} · {apiUrl("/api/rebalance-plan")}
        </div>
      </main>
    </div>
  );
}
