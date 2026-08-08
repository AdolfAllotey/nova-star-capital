import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";

import { fetchJson } from "../lib/apiClient";
function PageHeader({ title, subtitle, badges = [] }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <h1 className="text-[30px] font-semibold tracking-tight text-white">{title}</h1>
        <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
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

export default function Defensive() {
  const [signal, setSignal] = useState(null);
  const [allocationData, setAllocationData] = useState(null);
  const [allocations, setAllocations] = useState([]);
  const [loading, setLoading] = useState(true);
const [error, setError] = useState("");
const [sourceState, setSourceState] = useState({
  signal: "loading",
  allocations: "loading",
});

  useEffect(() => {
  let cancelled = false;

  async function load() {
    setLoading(true);
    setError("");

    const [signalRes, allocationsRes] = await Promise.all([
      fetchJson("/api/defensive_signal", {
        timeoutMs: 8000,
      }),
      fetchJson("/api/defensive_allocations", {
        timeoutMs: 8000,
      }),
    ]);

    if (cancelled) return;

    setSourceState({
      signal: signalRes?.ok
        ? "online"
        : "unavailable",
      allocations: allocationsRes?.ok
        ? "online"
        : "unavailable",
    });

    const signalPayload = signalRes?.ok
      ? signalRes.data
      : null;

    const allocationPayload = allocationsRes?.ok
      ? allocationsRes.data
      : null;

    setSignal(signalPayload);
    setAllocationData(allocationPayload);

    setAllocations(
      Array.isArray(allocationPayload?.proposed_assets)
        ? allocationPayload.proposed_assets
        : []
    );

    const unavailable = [];

    if (!signalRes?.ok) {
      unavailable.push("defensive signal");
    }

    if (!allocationsRes?.ok) {
      unavailable.push("defensive allocations");
    }

    if (unavailable.length > 0) {
      setError(
        `Unavailable source: ${unavailable.join(", ")}.`
      );
    }

    setLoading(false);
  }

  load();

  const interval = setInterval(load, 15000);

  return () => {
    cancelled = true;
    clearInterval(interval);
  };
}, []);

  const summary = useMemo(() => {
    const signalSummary = signal?.score_summary || {};
    const allocationSummary = allocationData?.summary || {};
    const constraints = allocationSummary?.constraints_respected || {};

    const constraintsOk =
      Object.keys(constraints).length > 0
        ? Object.values(constraints).every(Boolean)
        : false;

    return {
      selectedAssets: signalSummary?.selected_assets_count ?? allocations.length ?? 0,
      targetExposure: signal?.target_exposure ?? allocationData?.target_exposure ?? 0,
      confidence: signal?.confidence ?? 0,
      beta: signalSummary?.portfolio_beta_estimate ?? "-",
      avgScore: signalSummary?.average_defensive_score ?? "-",
      constraintsOk,
      sectorWeights: allocationSummary?.sector_weights || {},
      etfWeight: allocationSummary?.etf_weight,
      etfCount: allocationSummary?.etf_count,
      stockCount: allocationSummary?.stock_count,
      maxSectorWeight: allocationSummary?.max_sector_weight,
    };
  }, [signal, allocationData, allocations]);

  const narrative = useMemo(() => {
    return [
      `Defensive sleeve targets ${(Number(summary.targetExposure || 0) * 100).toFixed(1)}% portfolio exposure.`,
      `Confidence currently reads ${(Number(summary.confidence || 0) * 100).toFixed(2)}%.`,
      `Portfolio beta estimate stands at ${summary.beta}.`,
      `Average defensive score currently reads ${summary.avgScore}.`,
      `Constraint status is ${summary.constraintsOk ? "OK" : "CHECK"}.`,
    ];
  }, [summary]);

  return (
    <div className="space-y-6 p-5 text-zinc-100">
      <PageHeader
        title="Defensive Equities"
        subtitle="Long-duration defensive sleeve focused on stability, dividends, and lower volatility exposure."
        badges={[
          
          {
  label:
    signal?.env ||
    allocationData?.env ||
    "UNAVAILABLE",
},
{
  label:
    sourceState.signal === "online" &&
    sourceState.allocations === "online"
      ? "SOURCES_ONLINE"
      : "SOURCE_UNAVAILABLE",
},
          {
  label:
    signal?.mode ||
    "UNAVAILABLE",
},
          { label: summary.constraintsOk ? "LIMITS_OK" : "CHECK_LIMITS" },
        ]}
      />
{error ? (
  <div className="mb-4 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
    {error}
  </div>
) : null}



      <SectionCard title="Defensive Narrative" subtitle="How the defensive sleeve should currently be read">
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

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-6">
        <MicroCard
          label="Selected Assets"
          value={loading ? "..." : summary.selectedAssets}
        />
        <MicroCard
          label="Target Exposure"
          value={loading ? "..." : `${((summary.targetExposure || 0) * 100).toFixed(1)}%`}
        />
        <MicroCard
          label="Confidence"
          value={loading ? "..." : `${((summary.confidence || 0) * 100).toFixed(2)}%`}
        />
        <MicroCard
          label="Portfolio Beta"
          value={loading ? "..." : summary.beta}
        />
        <MicroCard
          label="Average Score"
          value={loading ? "..." : summary.avgScore}
        />
        <MicroCard
          label="Limits"
          value={loading ? "..." : (summary.constraintsOk ? "OK" : "CHECK")}
        />
      </div>

      <SectionCard
        title="Defensive Allocation"
        subtitle="Detailed breakdown of current proposed defensive holdings"
      >
        <div className="mb-4 text-sm text-zinc-400">
          {allocations.length} assets
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] border-separate border-spacing-y-2">
            <thead>
              <tr className="text-left text-sm text-zinc-400">
                <th className="pb-2">Symbol</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Sector</th>
                <th className="pb-2">Region</th>
                <th className="pb-2">Weight</th>
                <th className="pb-2">Score</th>
                <th className="pb-2">Quality</th>
                <th className="pb-2">Low Vol</th>
                <th className="pb-2">Dividend</th>
              </tr>
            </thead>
            <tbody>
              {allocations.map((a, i) => (
                <tr key={`${a.ticker}-${i}`} className="rounded-2xl border border-zinc-800 bg-zinc-900/50">
                  <td className="rounded-l-2xl px-4 py-3 font-medium text-white">{a.ticker}</td>
                  <td className="px-4 py-3 text-zinc-300">{a.type}</td>
                  <td className="px-4 py-3 text-zinc-300">{a.sector}</td>
                  <td className="px-4 py-3 text-zinc-300">{a.region}</td>
                  <td className="px-4 py-3 text-zinc-300">{((a.weight || 0) * 100).toFixed(2)}%</td>
                  <td className="px-4 py-3 text-zinc-300">{a.defensive_score?.toFixed?.(2) ?? "-"}</td>
                  <td className="px-4 py-3 text-zinc-300">{a.quality_score?.toFixed?.(2) ?? "-"}</td>
                  <td className="px-4 py-3 text-zinc-300">{a.low_vol_score?.toFixed?.(2) ?? "-"}</td>
                  <td className="rounded-r-2xl px-4 py-3 text-zinc-300">{a.dividend_score?.toFixed?.(2) ?? "-"}</td>
                </tr>
              ))}

              {!loading && allocations.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-zinc-500">
                    No defensive allocations available.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SectionCard title="Sector Weights" subtitle="Current sector diversification profile">
          <div className="space-y-3">
            {Object.keys(summary.sectorWeights || {}).length > 0 ? (
              Object.entries(summary.sectorWeights).map(([sector, weight]) => (
                <div
                  key={sector}
                  className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3"
                >
                  <span className="text-zinc-300">{sector}</span>
                  <span className="font-medium text-white">{(Number(weight || 0) * 100).toFixed(2)}%</span>
                </div>
              ))
            ) : (
              <div className="text-zinc-500">No sector summary available.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Constraints Summary" subtitle="Allocator and risk constraints overview">
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">Target Exposure</span>
              <span className="text-white">{((summary.targetExposure || 0) * 100).toFixed(2)}%</span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">Selected Assets</span>
              <span className="text-white">{summary.selectedAssets}</span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">ETF Count / Stock Count</span>
              <span className="text-white">
                {(summary.etfCount ?? 0)} / {(summary.stockCount ?? 0)}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">ETF Weight</span>
              <span className="text-white">
                {typeof summary.etfWeight === "number" ? `${(summary.etfWeight * 100).toFixed(2)}%` : "—"}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">Max Sector Weight</span>
              <span className="text-white">
                {typeof summary.maxSectorWeight === "number" ? `${(summary.maxSectorWeight * 100).toFixed(2)}%` : "—"}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">Portfolio Beta</span>
              <span className="text-white">{summary.beta}</span>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-900/40 px-4 py-3">
              <span className="text-zinc-300">Constraints Status</span>
              <span className={summary.constraintsOk ? "text-emerald-300" : "text-amber-300"}>
                {summary.constraintsOk ? "OK" : "CHECK"}
              </span>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
