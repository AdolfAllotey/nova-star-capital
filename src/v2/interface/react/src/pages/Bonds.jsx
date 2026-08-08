import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useMemo, useState } from "react";
function normalizeMode(value) {
  if (!value) return "PREPROD";
  const v = String(value).toLowerCase();
  if (v.includes("signal")) return "PREPROD";
  return value;
}

import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";

function PageHeader({ title, subtitle, badges = [] }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <h1 className="text-[30px] font-semibold tracking-tight text-white">{title}</h1>
        <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {badges.map((badge, idx) => (
          <StatusBadge
            key={`${badge.label || badge.status || "badge"}-${idx}`}
            status={badge.status}
            label={badge.label}
          />
        ))}
      </div>
    </div>
  );
}

function MicroCard({ label, value, subvalue }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      {subvalue ? <div className="mt-1 text-sm text-zinc-400">{subvalue}</div> : null}
    </div>
  );
}

function toneClass(value) {
  const v = String(value || "unknown");
  if (/(bullish|supportive|active|defensive|low|approved|aligned)/i.test(v)) {
    return "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";
  }
  if (/(moderate|neutral|intermediate|medium|watch)/i.test(v)) {
    return "bg-amber-500/10 text-amber-300 border-amber-500/30";
  }
  if (/(headwind|high|blocked|risk_off|critical)/i.test(v)) {
    return "bg-rose-500/10 text-rose-300 border-rose-500/30";
  }
  return "bg-zinc-500/10 text-zinc-300 border-zinc-500/30";
}

function ProgressRow({ label, value }) {
  const pct = Math.max(0, Math.min(100, Number(value || 0) * 100));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-300">{label}</span>
        <span className="text-white">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div className="h-2 rounded-full bg-white/70" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function KeyValueGrid({ items = [] }) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl border border-white/10 bg-black/10 p-3">
          <div className="mb-2 text-xs uppercase tracking-wide text-zinc-400">{item.label}</div>
          <div>
            {item.badge ? (
              <StatusBadge
  label={
    item?.key === "execution_mode" || item?.key === "mode"
      ? "PREPROD"
      : normalizeMode(item.value)
  }
/>
            ) : (
              <div className="text-white">{String(normalizeMode(item.value) ?? "-")}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Bonds() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setError("");
        const res = await fetch(apiUrl("/api/bonds/signal"));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (mounted) setData(json);
      } catch (e) {
        if (mounted) setError(`Unable to load bonds data: ${e.message}`);
      }
    }

    load();
    const id = setInterval(load, 30000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const signal = data?.signal || {};
  const portfolioState = data?.portfolio_state || {};
  const allocation = signal?.allocation || {};
  const drivers = signal?.drivers || {};
  const riskFlags = signal?.risk_flags || {};
  const inertia = portfolioState?.inertia_profile || {};

  const allocationEntries = useMemo(() => Object.entries(allocation), [allocation]);
  const driverEntries = useMemo(() => Object.entries(drivers), [drivers]);
  const riskEntries = useMemo(() => Object.entries(riskFlags), [riskFlags]);

  const narrative = [
    `Bond macro score currently reads ${signal?.bond_macro_score ?? "-"}.`,
    `Target exposure stands at ${((signal?.target_exposure || 0) * 100).toFixed(1)}%.`,
    `Confidence stands at ${((signal?.confidence || 0) * 100).toFixed(1)}%.`,
    `Duration target is ${signal?.duration_target || "intermediate"}.`,
    `Funding pool currently routes through ${portfolioState?.funding_pool || "ibkr_pool"}.`,
  ];

  return (
    <div className="p-5 text-white space-y-6">
      <PageHeader
        title="Bonds"
        subtitle="Macro stabilizer sleeve for defensive allocation, duration control, and portfolio ballast."
        badges={[
          { label: signal?.regime || portfolioState?.regime || "unknown" },
          { label: signal?.duration_target || "intermediate" },
          { label: "PREPROD" },
        ]}
      />

      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">
          {error}
        </div>
      ) : null}

      <SectionCard title="Macro Narrative" subtitle="How the bonds sleeve should currently be read">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          {narrative.map((line, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-cyan-100"
            >
              {line}
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MicroCard label="Bond Macro Score" value={signal?.bond_macro_score ?? "-"} />
        <MicroCard label="Target Exposure" value={`${((signal?.target_exposure || 0) * 100).toFixed(1)}%`} />
        <MicroCard label="Confidence" value={`${((signal?.confidence || 0) * 100).toFixed(1)}%`} />
        <MicroCard label="Duration Target" value={signal?.duration_target || "-"} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SectionCard title="Internal Allocation" subtitle="Sub-allocation inside the bonds sleeve">
          <div className="space-y-4">
            {allocationEntries.length ? (
              allocationEntries.map(([k, v]) => (
                <ProgressRow key={k} label={k} value={v} />
              ))
            ) : (
              <div className="text-sm text-zinc-400">No allocation available.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Portfolio Integration" subtitle="How the sleeve plugs into the allocator">
          <KeyValueGrid
            items={[
              {
                label: "Target Weight Snapshot",
                value: `${((portfolioState?.target_weight_snapshot || 0) * 100).toFixed(1)}%`,
              },
              {
                label: "Portfolio Role",
                value: portfolioState?.portfolio_role || "-",
              },
              {
                label: "Funding Pool",
                value: portfolioState?.funding_pool || "-",
              },
              {
                label: "Rebalance Frequency",
                value: inertia?.rebalance_frequency || "-",
              },
              {
                label: "Max Weight Change / Cycle",
                value: inertia?.max_weight_change_per_cycle ?? "-",
              },
              {
                label: "Min Threshold To Rebalance",
                value: inertia?.min_threshold_to_rebalance ?? "-",
              },
            ]}
          />
        </SectionCard>
      </div>

      <SectionCard title="Macro Drivers" subtitle="Current macro signals feeding the bonds sleeve">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {driverEntries.length ? (
            driverEntries.map(([k, v]) => (
              <div key={k} className="rounded-xl border border-white/10 bg-black/10 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-zinc-400">
                  {k.replaceAll("_", " ")}
                </div>
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${toneClass(v)}`}>
                  {String(v)}
                </span>
              </div>
            ))
          ) : (
            <div className="text-sm text-zinc-400">No drivers available.</div>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Risk Flags" subtitle="Active risk warnings inside the bonds sleeve">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {riskEntries.length ? (
            riskEntries.map(([k, v]) => (
              <div key={k} className="rounded-xl border border-white/10 bg-black/10 p-3">
                <div className="mb-2 text-xs uppercase tracking-wide text-zinc-400">
                  {k.replaceAll("_", " ")}
                </div>
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${toneClass(v)}`}>
                  {String(v)}
                </span>
              </div>
            ))
          ) : (
            <div className="text-sm text-zinc-400">No risk flags available.</div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
