import React, { useEffect, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson, apiUrl } from "../lib/apiClient";

function Box({ children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20 hover:shadow-[0_0_40px_rgba(34,211,238,0.06)] ${className}`}>
      {children}
    </div>
  );
}

function LiveIndicator({ label = "LIVE", tone = "emerald" }) {
  const toneMap = {
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
    amber: "border-amber-400/20 bg-amber-400/10 text-amber-300",
    violet: "border-violet-400/20 bg-violet-400/10 text-violet-300",
    red: "border-red-400/20 bg-red-400/10 text-red-300",
  };
  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    violet: "bg-violet-400",
    red: "bg-red-400",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] ${toneMap[tone] || toneMap.emerald}`}>
      <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${dotMap[tone] || dotMap.emerald}`}></span>
      {label}
    </span>
  );
}

function PremiumSectionHeader({ title, subtitle, tone = "amber", badges = [] }) {
  const toneMap = {
    emerald: "border-emerald-400/10 from-[#071018] via-[#0b1a19] to-[#071018] text-emerald-100",
    cyan: "border-cyan-400/10 from-[#071018] via-[#0a1724] to-[#071018] text-cyan-100",
    amber: "border-amber-400/10 from-[#100d08] via-[#17120a] to-[#100d08] text-amber-100",
    violet: "border-violet-400/10 from-[#080d18] via-[#101426] to-[#080d18] text-violet-100",
    red: "border-red-400/10 from-[#140808] via-[#1a0b0b] to-[#140808] text-red-100",
  };
  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    violet: "bg-violet-400",
    red: "bg-red-400",
  };
  return (
    <div className={`mb-3 rounded-2xl border bg-gradient-to-r px-4 py-3 shadow-[0_0_50px_rgba(251,191,36,0.05)] ${toneMap[tone] || toneMap.amber}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full animate-pulse ${dotMap[tone] || dotMap.amber}`}></div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.22em]">
              {title}
            </div>
          </div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            {subtitle}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[9px] uppercase tracking-[0.14em]">
          {badges.map((badge, idx) => (
            <span key={idx} className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-300">
              {badge}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
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
    <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] px-3 py-2 transition-all duration-300 hover:border-cyan-500/20 hover:bg-[#101927] hover:shadow-[0_0_20px_rgba(34,211,238,0.04)]">
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
  return <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase ${tones[tone] || tones.blue}`}>{children}</span>;
}

export default function Governance() {
  const [governance, setGovernance] = useState(null);
  const [executionPlan, setExecutionPlan] = useState(null);
  const [aggregatorAudit, setAggregatorAudit] = useState(null);
  const [allocationPolicy, setAllocationPolicy] = useState(null);
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [govRes, execRes, auditRes, policyRes, dashboardRes] = await Promise.all([
        fetchJson("/governance/status", { timeoutMs: 8000 }),
        fetchJson("/api/execution-plan", { timeoutMs: 8000 }),
        fetchJson("/api/aggregator-audit", { timeoutMs: 8000 }),
        fetchJson("/api/allocation-policy", { timeoutMs: 8000 }),
        fetchJson("/dashboard/v3", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;
      setGovernance(govRes?.ok ? govRes.data : null);
      setExecutionPlan(execRes?.ok ? execRes.data : null);
      setAggregatorAudit(auditRes?.ok ? auditRes.data : null);
      setAllocationPolicy(policyRes?.ok ? policyRes.data : null);
      setDashboard(dashboardRes?.ok ? dashboardRes.data : null);
    }

    load();
    const id = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const global = dashboard?.global || {};
  const mode = global.governanceMode || governance?.mode || governance?.governance_mode || "UNKNOWN";
  const actionPolicy = global.masterAuditGovernancePolicy || governance?.action_policy || executionPlan?.action_policy || executionPlan?.execution_mode || "UNKNOWN";
  const hardBlock = Boolean(global.globalAuditBlocking || global.masterAuditHardBlock || executionPlan?.blocked === true || String(mode).toUpperCase().includes("BLOCK"));
  const supervisionGateMode = String(global.supervisionGateMode || "UNKNOWN").toUpperCase();
  const supervisionGateOpen = global.supervisionGateOpen === true;
  const realExecutionEnabled = String(actionPolicy).toUpperCase() !== "SIMULATED_ONLY" && !hardBlock;
  const auditStatus = aggregatorAudit?.status || "UNKNOWN";
  const anomalies = Number(aggregatorAudit?.summary?.anomalies_count || 0);
  const warnings = Number(aggregatorAudit?.summary?.warnings_count || 0);
  const approved = Number(aggregatorAudit?.summary?.approved_actions_count || 0);

  const policyStatus = allocationPolicy?.status || "UNKNOWN";
  const policyRole = allocationPolicy?.policy_role || "—";
  const sourceOfTruth = allocationPolicy?.source_of_truth === true;
  const manualFundingRequired = allocationPolicy?.rebalance?.manual_funding_required === true;
  const autoInterUniverse = allocationPolicy?.rebalance?.automatic_inter_universe_transfer === true;
  const minRebalanceThreshold = allocationPolicy?.rebalance?.min_rebalance_threshold_pct;
  const maxRebalanceFrequency = allocationPolicy?.rebalance?.max_rebalance_frequency || "—";
  const cashBufferMin = allocationPolicy?.cash_buffer_min_pct;
  const cashBufferCurrent = allocationPolicy?.cash_buffer_current_pct;
  const actionRules = allocationPolicy?.action_rules || {};
  const brickInertia = allocationPolicy?.brick_inertia || {};
  const fundingPools = allocationPolicy?.funding_pools || {};

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Governance layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <header className="mb-3 rounded-2xl border border-[#1f2a37] bg-[radial-gradient(circle_at_top_left,#102033_0%,#09111a_42%,#05080d_100%)] p-3 shadow-[0_0_50px_rgba(34,211,238,0.08)]">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold uppercase tracking-wide">Governance Command Center</h1>
              <p className="text-xs text-slate-400">
                Source-of-truth policy, hard blocks, supervision gate and execution authority
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatusPill tone={hardBlock ? "red" : "green"}>{hardBlock ? "Hard Block" : "No Hard Block"}</StatusPill>
              <StatusPill tone="amber">{String(actionPolicy).toUpperCase()}</StatusPill>
              <StatusPill tone={realExecutionEnabled ? "red" : "green"}>{realExecutionEnabled ? "Real Execution Enabled" : "Real Execution Disabled"}</StatusPill>
              <StatusPill tone={supervisionGateOpen ? "green" : "red"}>Gate {supervisionGateOpen ? "Open" : "Closed"}</StatusPill>
            </div>
          </div>
        </header>

        <Box className="mb-3 border-amber-500/15 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.12),rgba(23,18,10,0.96)_38%,rgba(5,8,13,0.98)_100%)] p-3">
          <div className="grid grid-cols-[1.1fr_0.9fr_0.9fr_0.9fr] gap-3">
            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-300">Governance State</div>
              <div className={`mt-2 text-3xl font-semibold ${hardBlock ? "text-red-300" : "text-emerald-300"}`}>
                {hardBlock ? "BLOCKED" : "CONTROLLED"}
              </div>
              <div className="mt-2 text-[11px] leading-4 text-slate-400">
                Governance acts as the source-of-truth safety layer before any execution or funding decision.
              </div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Policy Mode</div>
              <div className="mt-2 text-2xl font-semibold text-amber-300">{String(actionPolicy).toUpperCase()}</div>
              <div className="mt-3 text-[10px] text-slate-400">Mode {String(mode).toUpperCase()}</div>
              <div className="mt-1 text-[10px] text-slate-400">Preprod execution policy</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Supervision Gate</div>
              <div className={`mt-2 text-2xl font-semibold ${supervisionGateOpen ? "text-emerald-300" : "text-red-300"}`}>
                {supervisionGateOpen ? "OPEN" : "CLOSED"}
              </div>
              <div className="mt-3 text-[10px] text-slate-400">Gate mode {supervisionGateMode}</div>
              <div className="mt-1 text-[10px] text-slate-400">Simulated orchestration only</div>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400">Execution Authority</div>
              <div className={`mt-2 text-2xl font-semibold ${realExecutionEnabled ? "text-red-300" : "text-emerald-300"}`}>
                {realExecutionEnabled ? "ENABLED" : "DISABLED"}
              </div>
              <div className="mt-3 text-[10px] text-slate-400">Hard block {hardBlock ? "active" : "inactive"}</div>
              <div className="mt-1 text-[10px] text-slate-400">Execution {executionPlan?.blocked ? "blocked" : "simulated"}</div>
            </div>
          </div>
        </Box>

        <PremiumSectionHeader
          title="Governance Command Layer"
          subtitle="Policy authority · execution permissions · audit state · hard block supervision"
          tone={hardBlock ? "red" : "amber"}
          badges={[
            hardBlock ? "Hard block active" : "No hard block",
            String(actionPolicy).toUpperCase(),
            `Warnings ${warnings}`,
            `Anomalies ${anomalies}`
          ]}
        />

        <div className="mb-3 rounded-2xl border border-amber-400/10 bg-gradient-to-r from-[#100d08] via-[#17120a] to-[#100d08] px-4 py-3 shadow-[0_0_60px_rgba(251,191,36,0.05)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-100">
                Live Governance Telemetry
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.14em]">
              <LiveIndicator label="GOVERNANCE LIVE" tone="amber" />
              <LiveIndicator label={hardBlock ? "BLOCKED" : "CONTROLLED"} tone={hardBlock ? "red" : "emerald"} />
              <LiveIndicator label={`AUDIT ${String(auditStatus).toUpperCase()}`} tone={anomalies > 0 ? "red" : warnings > 0 ? "amber" : "emerald"} />
              <LiveIndicator label="PREPROD SAFE" tone="cyan" />
            </div>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-5 gap-3">
          <Metric label="Mode" value={mode} tone={hardBlock ? "red" : "green"} />
          <Metric label="Action Policy" value={actionPolicy} tone="amber" />
          <Metric label="Audit" value={auditStatus} tone={auditStatus === "ok" ? "green" : "amber"} />
          <Metric label="Warnings" value={warnings} tone={warnings > 0 ? "amber" : "green"} />
          <Metric label="Anomalies" value={anomalies} tone={anomalies > 0 ? "red" : "green"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3 border border-amber-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(251,191,36,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Command</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-amber-300/70">
                  Policy gate, hard block and execution authority
                </div>
              </div>
              <LiveIndicator label="COMMAND" tone="amber" />
            </div>
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
                <div className="text-[10px] uppercase text-emerald-300">Hard Block</div>
                <div className="mt-1 text-sm font-semibold text-emerald-200">{hardBlock ? "ON" : "OFF"}</div>
              </div>
              <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                <div className="text-[10px] uppercase text-amber-300">Policy</div>
                <div className="mt-1 truncate text-sm font-semibold text-amber-200">{actionPolicy}</div>
              </div>
              <div className="rounded-lg border border-sky-400/20 bg-sky-400/5 p-3">
                <div className="text-[10px] uppercase text-sky-300">Approved</div>
                <div className="mt-1 text-sm font-semibold text-sky-200">{approved}</div>
              </div>
              <div className="rounded-lg border border-violet-400/20 bg-violet-400/5 p-3">
                <div className="text-[10px] uppercase text-violet-300">Execution</div>
                <div className="mt-1 text-sm font-semibold text-violet-200">{executionPlan?.blocked ? "BLOCKED" : "SIMULATED"}</div>
              </div>
            </div>
          </Box>

          <Box className="p-3 border border-violet-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(139,92,246,0.05)]">
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Reading</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-violet-300/70">
                  Institutional interpretation of current safety posture
                </div>
              </div>
              <LiveIndicator label="READING" tone="violet" />
            </div>
            <div className="rounded-2xl border border-[#1c2633] bg-[#0d1520] p-4 shadow-[0_0_30px_rgba(139,92,246,0.04)]">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${hardBlock ? "text-red-400" : "text-emerald-400"}`}>
                {hardBlock ? "BLOCKED" : "CONTROLLED"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Governance remains the final safety layer before execution. In preproduction, actions must remain simulated unless explicitly approved later.
              </div>
            </div>
          </Box>
        </div>

        <PremiumSectionHeader
          title="Governance Detail Layer"
          subtitle="Execution block state · plan traceability · audit confirmations"
          tone={hardBlock ? "red" : "cyan"}
          badges={[
            executionPlan?.blocked ? "Execution blocked" : "Execution permitted",
            aggregatorAudit?.governance_ok ? "Governance OK" : "Governance watch",
            aggregatorAudit?.funding_ok ? "Funding OK" : "Funding watch"
          ]}
        />


        <PremiumSectionHeader
          title="Policy Layer"
          subtitle="Master allocation policy · funding constraints · brick inertia · rebalance rules"
          tone={sourceOfTruth ? "emerald" : "amber"}
          badges={[
            sourceOfTruth ? "Source of truth" : "Policy watch",
            manualFundingRequired ? "Manual funding required" : "Auto funding",
            autoInterUniverse ? "Auto bridge enabled" : "No auto bridge",
            String(policyStatus).toUpperCase()
          ]}
        />

        <div className="mb-3 grid grid-cols-[1.2fr_1fr] gap-3">
          <Box className="p-3 border border-emerald-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(16,185,129,0.05)]">
            <Title right="Master policy">Allocation Policy</Title>
            <div className="grid grid-cols-4 gap-3">
              <Metric label="Policy Status" value={policyStatus} tone={policyStatus === "ok" ? "green" : "amber"} />
              <Metric label="Policy Role" value={policyRole} tone="blue" />
              <Metric label="Source of Truth" value={sourceOfTruth ? "YES" : "NO"} tone={sourceOfTruth ? "green" : "amber"} />
              <Metric label="Manual Funding" value={manualFundingRequired ? "YES" : "NO"} tone={manualFundingRequired ? "amber" : "green"} />
              <Metric label="Auto Crypto ↔ IBKR" value={autoInterUniverse ? "YES" : "NO"} tone={autoInterUniverse ? "red" : "green"} />
              <Metric label="Min Rebalance" value={minRebalanceThreshold != null ? `${(Number(minRebalanceThreshold) * 100).toFixed(1)}%` : "—"} tone="blue" />
              <Metric label="Frequency" value={maxRebalanceFrequency} tone="slate" />
              <Metric label="Cash Buffer" value={cashBufferCurrent != null ? `${(Number(cashBufferCurrent) * 100).toFixed(1)}%` : "—"} tone="green" />
            </div>

            <div className="mt-3 rounded-xl border border-[#1c2633] bg-[#0d1520] p-3 text-sm leading-5 text-slate-300">
              {allocationPolicy?.rebalance?.reason || "Policy layer loaded. Rebalance and funding decisions remain governed."}
            </div>
          </Box>

          <Box className="p-3 border border-amber-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(251,191,36,0.05)]">
            <Title right="Guardrails">Action Rules</Title>
            <div className="grid grid-cols-2 gap-3">
              <Metric label="Hard Block" value={actionRules.hard_block || "—"} tone="red" />
              <Metric label="Soft Veto PREPROD" value={actionRules.soft_veto_preprod || "—"} tone="amber" />
              <Metric label="Shadow Modules" value={actionRules.shadow_modules || "—"} tone="blue" />
              <Metric label="Future Exit Policy" value={actionRules.exit_only_future_policy || "—"} tone="slate" />
            </div>

            <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-sm leading-5 text-amber-100">
              No automatic capital bridge is authorized between crypto exchanges and IBKR. Options shadow modules remain observe-only.
            </div>
          </Box>
        </div>

        <div className="mb-3 grid grid-cols-[1fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Pools">Funding Pool Policy</Title>
            <div className="space-y-2">
              {Object.entries(fundingPools).map(([key, pool]) => (
                <div key={key} className="rounded-xl border border-[#1c2633] bg-[#0d1520] px-3 py-2 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-200">{key.replaceAll("_", " ")}</div>
                      <div className="mt-1 text-[10px] text-slate-500">
                        Venues: {(pool.venues || []).join(", ") || "—"}
                      </div>
                    </div>
                    <StatusPill tone={pool.automatic_external_funding ? "red" : "green"}>
                      {pool.automatic_external_funding ? "AUTO FUNDING" : "NO AUTO FUNDING"}
                    </StatusPill>
                  </div>
                  <div className="mt-2 text-[10px] text-slate-400">
                    Allowed bricks: {(pool.allowed_bricks || []).join(", ") || "—"}
                  </div>
                </div>
              ))}
            </div>
          </Box>

          <Box className="p-3">
            <Title right="Inertia">Brick Movement Policy</Title>
            <div className="space-y-2">
              {Object.entries(brickInertia).map(([key, cfg]) => (
                <div key={key} className="grid grid-cols-[1fr_80px_80px_80px] items-center gap-2 rounded-xl border border-[#1c2633] bg-[#0d1520] px-3 py-2 text-xs">
                  <div className="truncate text-slate-200">{key.replaceAll("_", " ")}</div>
                  <div className="text-sky-300">{cfg.frequency || "—"}</div>
                  <div className="text-slate-300">{cfg.max_weight_change_per_cycle != null ? `${(Number(cfg.max_weight_change_per_cycle) * 100).toFixed(1)}%` : "—"}</div>
                  <div className={cfg.execution_allowed === false ? "text-amber-300" : "text-emerald-400"}>
                    {cfg.execution_allowed === false ? "LOCKED" : "ACTIVE"}
                  </div>
                </div>
              ))}
            </div>
          </Box>
        </div>

        <Box className="p-3 border border-cyan-400/10 bg-gradient-to-b from-[#0b1622] to-[#09111a] shadow-[0_0_40px_rgba(34,211,238,0.05)]">
          <div className="mb-3 flex items-start justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-100">Governance Details</div>
              <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">
                Low-level execution and audit status
              </div>
            </div>
            <LiveIndicator label="DETAILS" tone="cyan" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Metric label="Execution Blocked" value={executionPlan?.blocked ? "YES" : "NO"} tone={executionPlan?.blocked ? "red" : "green"} />
            <Metric label="Plan ID" value={executionPlan?.plan_id || "—"} tone="blue" />
            <Metric label="Audit Governance OK" value={aggregatorAudit?.governance_ok ? "YES" : "NO"} tone={aggregatorAudit?.governance_ok ? "green" : "amber"} />
            <Metric label="Audit Funding OK" value={aggregatorAudit?.funding_ok ? "YES" : "NO"} tone={aggregatorAudit?.funding_ok ? "green" : "amber"} />
          </div>
        </Box>

        <div className="mt-3 text-[10px] text-slate-600">
          Sources: {apiUrl("/governance/status")} · {apiUrl("/api/execution-plan")} · {apiUrl("/api/aggregator-audit")} · {apiUrl("/api/allocation-policy")}
        </div>
      </main>
    </div>
  );
}
