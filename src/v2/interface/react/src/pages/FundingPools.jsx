import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import { fetchJson, apiUrl } from "../lib/apiClient";

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function eur(v) {
  return `${num(v).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} €`;
}

function pct(v) {
  return `${(num(v) * 100).toFixed(1)}%`;
}

function humanPool(key) {
  const map = {
    crypto_exchange_pool: "Crypto Exchange Pool",
    ibkr_pool: "IBKR Pool",
    cash_reserve: "Cash Reserve",
    safety_pool: "Safety Pool",
  };
  return map[key] || String(key || "—").replaceAll("_", " ");
}

function Box({ children, className = "" }) {
  return (
    <div className={`rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 backdrop-blur-sm transition-all duration-300 hover:border-cyan-400/20 hover:shadow-[0_0_40px_rgba(34,211,238,0.06)] ${className}`}>
      {children}
    </div>
  );
}

function Title({ children, right }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[13px] font-semibold uppercase tracking-[0.14em] text-slate-100">{children}</h3>
      {right ? <div className="text-[10px] uppercase tracking-wide text-slate-500">{right}</div> : null}
    </div>
  );
}

function Metric({ label, value, tone = "white", helper }) {
  const tones = {
    white: "text-white",
    green: "text-emerald-400",
    amber: "text-amber-300",
    red: "text-red-400",
    blue: "text-sky-300",
    slate: "text-slate-300",
    violet: "text-violet-300",
  };

  return (
    <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] px-3 py-2 transition-all duration-300 hover:border-cyan-500/20 hover:bg-[#101927]">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 truncate text-lg font-semibold ${tones[tone] || tones.white}`}>{value}</div>
      {helper ? <div className="mt-1 truncate text-[10px] text-slate-500">{helper}</div> : null}
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
    violet: "border-violet-400/30 bg-violet-400/10 text-violet-300",
  };

  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${tones[tone] || tones.blue}`}>
      {children}
    </span>
  );
}

function LiveIndicator({ label = "LIVE", tone = "emerald" }) {
  const toneMap = {
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
    amber: "border-amber-400/20 bg-amber-400/10 text-amber-300",
    red: "border-red-400/20 bg-red-400/10 text-red-300",
  };

  const dotMap = {
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.14em] ${toneMap[tone] || toneMap.emerald}`}>
      <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${dotMap[tone] || dotMap.emerald}`} />
      {label}
    </span>
  );
}

function UtilizationBar({ value }) {
  const width = Math.max(0, Math.min(100, num(value) * 100));
  const color = width >= 85 ? "bg-amber-400" : width >= 60 ? "bg-cyan-400" : "bg-emerald-400";

  return (
    <div className="h-1.5 rounded bg-[#1a2532]">
      <div className={`h-1.5 rounded ${color}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export default function FundingPools() {
  const [fundingPlan, setFundingPlan] = useState(null);
  const [portfolioTarget, setPortfolioTarget] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [fundingRes, targetRes] = await Promise.all([
        fetchJson("/api/funding-plan", { timeoutMs: 8000 }),
        fetchJson("/api/portfolio-target", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      setErr(!fundingRes?.ok ? "Unable to load funding plan." : null);
      setFundingPlan(fundingRes?.ok ? fundingRes.data : null);
      setPortfolioTarget(targetRes?.ok ? targetRes.data : null);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const pools = fundingPlan?.pools || fundingPlan?.funding_pools || [];

  const rows = useMemo(() => {
    if (Array.isArray(pools)) {
      return pools.map((value, idx) => {
        const key = value?.pool || value?.name || `pool_${idx}`;
        const netRequired = num(value?.net_required_eur);
        const itemTarget = Array.isArray(value?.items)
          ? value.items.reduce((s, item) => s + num(item?.target_amount_eur), 0)
          : 0;
        const itemCurrent = Array.isArray(value?.items)
          ? value.items.reduce((s, item) => s + num(item?.current_amount_estimate_eur), 0)
          : 0;
        const target = num(value?.target ?? value?.target_amount_eur ?? itemTarget);
        const available = num(value?.available ?? value?.available_eur ?? value?.cash_available_eur ?? itemCurrent);
        return {
          key,
          label: humanPool(key),
          target,
          available,
          utilization: target > 0 ? available / target : 0,
          currency: value?.currency || "EUR",
          status: value?.manual_transfer_required ? "MANUAL" : (value?.status || "ACTIVE"),
          universe: Array.isArray(value?.items)
            ? value.items.map((item) => item?.brick).filter(Boolean).join(", ")
            : (value?.universe || value?.scope || key),
          netRequired,
        };
      });
    }

    return Object.entries(pools || {}).map(([key, value]) => ({
      key,
      label: humanPool(key),
      target: num(value?.target ?? value?.target_eur ?? value?.target_capital_eur ?? value?.target_amount_eur),
      available: num(value?.available ?? value?.available_eur ?? value?.cash_available_eur),
      utilization: num(value?.utilization ?? value?.utilization_ratio),
      currency: value?.currency || "EUR",
      status: value?.manual_transfer_required ? "MANUAL" : (value?.status || "ACTIVE"),
      universe: value?.universe || value?.scope || key,
      netRequired: num(value?.net_required_eur),
    }));
  }, [pools]);

  const totalTarget = rows.reduce((s, r) => s + r.target, 0);
  const totalCurrent = rows.reduce((s, r) => s + r.available, 0);
  const totalNetRequired = rows.reduce((s, r) => s + num(r.netRequired), 0);
  const avgUtil = rows.length ? rows.reduce((s, r) => s + r.utilization, 0) / rows.length : 0;
  const manualTransfers =
    fundingPlan?.requires_manual_transfer_between_pools === true ||
    fundingPlan?.manual_approval_required === true ||
    fundingPlan?.inter_universe_transfer?.automatic_transfer_allowed === false ||
    rows.some((row) => String(row.status || "").toUpperCase() === "MANUAL")
      ? "MANUAL"
      : "NONE";
  const cashBuffer = num(portfolioTarget?.cash_buffer ?? portfolioTarget?.data?.cash_buffer);
  const fundingStatus =
    manualTransfers === "MANUAL" ? "GOVERNED" :
    avgUtil >= 0.85 ? "TIGHT" :
    "READY";

  const fundingAlerts = [];
  if (manualTransfers === "MANUAL") fundingAlerts.push("Manual cross-universe funding remains enforced: Crypto venues and IBKR pool are not automatically bridged.");
  if (avgUtil >= 0.85) fundingAlerts.push("High average utilization detected. Deployment room is becoming constrained.");
  if (rows.length === 0) fundingAlerts.push("No funding pool data available yet.");
  if (!fundingAlerts.length) fundingAlerts.push("Funding layer is coherent. No critical liquidity blocker detected.");

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Funding layer online" />

      <main className="ml-[235px] w-[calc(100%-235px)] p-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h1 className="text-lg font-semibold uppercase tracking-wide">Funding Pools</h1>
              <LiveIndicator label={loading ? "SYNCING" : "LIVE"} tone={loading ? "amber" : "cyan"} />
            </div>
            <p className="text-xs text-slate-400">
              Capital pools, available liquidity, utilization, cash buffer and manual transfer governance
            </p>
          </div>

          <div className="flex gap-2">
            <StatusPill tone={fundingStatus === "READY" ? "green" : fundingStatus === "TIGHT" ? "amber" : "blue"}>{fundingStatus}</StatusPill>
            <StatusPill tone={manualTransfers === "MANUAL" ? "amber" : "green"}>Transfers {manualTransfers}</StatusPill>
            <StatusPill tone="blue">Cash Buffer {pct(cashBuffer)}</StatusPill>
          </div>
        </div>

        {err ? (
          <Box className="mb-3 border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {err}
          </Box>
        ) : null}

        <div className="mb-3 grid grid-cols-6 gap-3">
          <Metric label="Funding Status" value={fundingStatus} tone={fundingStatus === "READY" ? "green" : fundingStatus === "TIGHT" ? "amber" : "blue"} />
          <Metric label="Pools" value={rows.length} tone="slate" />
          <Metric label="Target Capital" value={eur(totalTarget)} tone="blue" />
          <Metric label="Current" value={eur(totalCurrent)} tone="green" />
          <Metric label="Net Required" value={eur(totalNetRequired)} tone={totalNetRequired > 0 ? "amber" : "green"} />
          <Metric label="Avg Utilization" value={pct(avgUtil)} tone={avgUtil > 0.8 ? "amber" : "green"} />
        </div>

        <div className="mb-3 grid grid-cols-[1.3fr_1fr] gap-3">
          <Box className="p-3">
            <Title right="Capital routing">Funding Command Center</Title>

            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-sky-400/20 bg-sky-400/5 p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-sky-300">Capital Availability</div>
                <div className="mt-2 text-2xl font-semibold text-sky-200">{eur(totalCurrent)}</div>
                <div className="mt-3 text-xs text-slate-400">Current capital currently mapped to declared pools.</div>
              </div>

              <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-amber-300">Transfer Mode</div>
                <div className="mt-2 text-2xl font-semibold text-amber-200">{manualTransfers}</div>
                <div className="mt-3 text-xs text-slate-400">Cross-universe funding requires explicit approval.</div>
              </div>

              <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-emerald-300">Cash Buffer</div>
                <div className="mt-2 text-2xl font-semibold text-emerald-200">{pct(cashBuffer)}</div>
                <div className="mt-3 text-xs text-slate-400">Portfolio engine liquidity reserve.</div>
              </div>
            </div>
          </Box>

          <Box className="p-3">
            <Title>Funding Policy</Title>
            <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] p-4">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Reading</div>
              <div className={`mt-2 text-2xl font-semibold ${manualTransfers === "MANUAL" ? "text-amber-300" : "text-emerald-400"}`}>
                {manualTransfers === "MANUAL" ? "MANUAL FUNDING" : "AUTOMATED"}
              </div>
              <div className="mt-3 text-sm leading-5 text-slate-300">
                Crypto exchange capital and IBKR capital remain separated. No automatic capital bridge is assumed in PREPROD.
              </div>
            </div>

            <div className="mt-3 space-y-2">
              {fundingAlerts.map((alert, idx) => (
                <div key={idx} className={`rounded-xl border px-3 py-2 text-xs ${
                  alert.includes("No critical") || alert.includes("coherent")
                    ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-100"
                    : "border-amber-500/20 bg-amber-500/5 text-amber-100"
                }`}>
                  {alert}
                </div>
              ))}
            </div>
          </Box>
        </div>

        <Box className="p-3">
          <Title right="Capital pools by universe">Funding Pool Intelligence</Title>

          <div className="grid grid-cols-[1.2fr_100px_100px_140px_100px_110px] gap-2 border-b border-[#172231] pb-2 text-[9px] uppercase text-slate-500">
            <div>Pool</div>
            <div>Target</div>
            <div>Current</div>
            <div>Utilization</div>
            <div>Status</div>
            <div>Universe</div>
          </div>

          <div className="space-y-2 pt-2">
            {rows.length === 0 ? (
              <div className="rounded-xl border border-[#1c2633] bg-[#0d1520] p-3 text-sm text-slate-400">
                No funding pool data available yet.
              </div>
            ) : rows.map((row) => (
              <div key={row.key} className="grid grid-cols-[1.2fr_100px_100px_100px_140px_100px_110px] items-center gap-2 border-b border-[#172231] py-2 text-xs last:border-b-0">
                <div>
                  <div className="truncate text-slate-200">{row.label}</div>
                  <div className="truncate text-[10px] text-slate-600">{row.key}</div>
                </div>
                <div className="text-slate-300">{eur(row.target)}</div>
                <div className="text-emerald-400">{eur(row.available)}</div>
                <div className={row.netRequired > 0 ? "text-amber-300" : "text-slate-500"}>{eur(row.netRequired)}</div>
                <div className="grid gap-1">
                  <UtilizationBar value={row.utilization} />
                  <div className={row.utilization > 0.8 ? "text-amber-300" : "text-slate-300"}>{pct(row.utilization)}</div>
                </div>
                <div className="text-sky-300">{row.status}</div>
                <div className="truncate text-slate-500">{row.universe}</div>
              </div>
            ))}
          </div>
        </Box>

        <div className="mt-3 text-[10px] text-slate-600">
          Sources: {apiUrl("/api/funding-plan")} · {apiUrl("/api/portfolio-target")}
        </div>
      </main>
    </div>
  );
}
