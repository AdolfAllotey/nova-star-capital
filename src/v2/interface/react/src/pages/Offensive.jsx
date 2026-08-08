import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";

const FALLBACK = {
  header: {
    name: "Offensive Equities",
    status: "PREPROD",
    env: "PREPROD",
    mode: "SIMULATED_ONLY",
    regime: "UNKNOWN",
    regimeConfidence: 0,
    planId: null,
  },
  kpis: {
    candidates: 0,
    orders: 0,
    openPositions: 0,
    totalNotionalUsd: 0,
    limitsOk: true,
    softVetos: [],
  },
  pipeline: {
    candidateOrders: [],
    orders: [],
    reasons: [],
    planId: null,
    actionPolicy: null,
  },
  risk: {},
  reconciliation: {},
  exposure: {},
};

function truncate(value, max = 42) {
  if (!value) return "—";
  const s = String(value);
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

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
        <a
          href="/signals/board"
          className="inline-flex items-center rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-[11px] font-medium tracking-wide text-sky-300 hover:bg-sky-500/20 transition"
        >
          Open Signal Board
        </a>
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

export default function Offensive() {
  const [data, setData] = useState(FALLBACK);
  const [explainability, setExplainability] = useState([]);
  const [explainabilitySummary, setExplainabilitySummary] = useState(null);
  const [explainabilityBySymbol, setExplainabilityBySymbol] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetch(apiUrl("/bricks/offensive/overview"), {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();

        // Explainability fetch
        try {
          const explainRes = await fetch(apiUrl("/api/explainability"), {
            method: "GET",
            credentials: "include",
          });
          if (explainRes.ok) {
            const explainJson = await explainRes.json();
            if (!cancelled) {
              setExplainability(explainJson?.explanations || []);
              setExplainabilitySummary(explainJson?.summary || null);
              setExplainabilityBySymbol(explainJson?.by_symbol || {});
            }
          }
        } catch (e) {
          console.warn("Explainability fetch failed", e);
        }

        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) {
          console.error("offensive overview fetch failed", e);
          setError("Unable to load live offensive data.");
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

  const { header, kpis, pipeline, risk, reconciliation, exposure } = data;

  const riskReasons = safeArray(risk.reasons);
  const riskSoftVetos = safeArray(risk.soft_vetos || risk.softVetos);
  const recoAnomalies = safeArray(reconciliation.anomalies);
  const fillsSymbols = safeArray(reconciliation?.summary?.symbols_in_fills);
  const positionsSymbols = safeArray(reconciliation?.summary?.symbols_in_positions);
  const exposurePositions = safeArray(exposure.positions);

  const riskStatus = risk.ok === false ? "BREACH" : "OK";
  const recoStatus = reconciliation.ok === false ? "ANOMALY" : "OK";
  const limitsStatus = kpis.limitsOk ? "OK" : "BREACH";

  const narrative = useMemo(() => {
    return [
      `Current regime reads ${header.regime || "UNKNOWN"}.`,
      `Execution mode is ${header.mode || "N/A"}.`,
      `There are currently ${kpis.candidates ?? 0} candidate signal(s) and ${kpis.orders ?? 0} executable order(s).`,
      `Risk status is ${riskStatus} and reconciliation status is ${recoStatus}.`,
      `Current plan ID is ${truncate(header.planId)}.`,
    ];
  }, [header, kpis, riskStatus, recoStatus]);

  return (
    <div className="p-5 space-y-6">
      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <PageHeader
        title={header.name || "Offensive Equities"}
        subtitle="Trading desk view for offensive execution, signal conversion, risk controls, and exposure monitoring."
        badges={[
          { label: header.status },
          { label: header.env },
          { label: header.mode },
          { label: header.regime },
        ]}
      />

      <SectionCard title="Desk Narrative" subtitle="How the offensive sleeve should currently be read">
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

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <MicroCard label="Candidates" value={kpis.candidates} />
        <MicroCard label="Orders" value={kpis.orders} />
        <MicroCard label="Open Positions" value={kpis.openPositions} />
        <MicroCard label="Notional USD" value={kpis.totalNotionalUsd ?? 0} />
        <MicroCard label="Limits" value={limitsStatus} />
        <MicroCard label="Soft Vetos" value={safeArray(kpis.softVetos).length} />
      </div>

      <SectionCard title="Pipeline" subtitle="Signal conversion from candidate set to executable orders">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div>
            <div className="text-sm text-zinc-400 mb-2">Candidate Orders</div>
            <div className="space-y-2">
              {safeArray(pipeline.candidateOrders).length === 0 && (
                <div className="text-sm text-zinc-500">No candidate orders.</div>
              )}
              {safeArray(pipeline.candidateOrders).map((o, idx) => (
                <div key={`cand-${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm">
                  <div>{o.symbol} · {o.side} · qty {o.qty}</div>
                  <div className="text-zinc-400 mt-1">
                    score: {o.score ?? "—"} · reason: {o.reason ?? "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-sm text-zinc-400 mb-2">Orders</div>
            <div className="space-y-2">
              {safeArray(pipeline.orders).length === 0 && (
                <div className="text-sm text-zinc-500">No executable orders.</div>
              )}
              {safeArray(pipeline.orders).map((o, idx) => (
                <div key={`ord-${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm">
                  <div>{o.symbol} · {o.side} · qty {o.qty}</div>
                  <div className="text-zinc-400 mt-1">
                    type: {o.type ?? "—"} · reason: {o.reason ?? "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5">
          <div className="text-sm text-zinc-400 mb-2">Plan Reasons</div>
          <ul className="list-disc pl-5 text-sm text-zinc-300 space-y-1">
            {safeArray(pipeline.reasons).length === 0 && <li>No reasons available.</li>}
            {safeArray(pipeline.reasons).map((r, idx) => (
              <li key={`reason-${idx}`}>{r}</li>
            ))}
          </ul>
        </div>
      </SectionCard>

      <SectionCard title="Explainability" subtitle="Decision traceability grouped by symbol and event timeline">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
          <MicroCard label="Symbols" value={explainabilitySummary?.total_symbols ?? 0} />
          <MicroCard label="Events" value={explainabilitySummary?.total_events ?? 0} />
          <MicroCard label="Entries Not Executed" value={explainabilitySummary?.entries_not_executed ?? 0} />
          <MicroCard label="Exits Executed" value={explainabilitySummary?.exits_executed ?? 0} />
          <MicroCard label="Entries Executed" value={explainabilitySummary?.entries_executed ?? 0} />
        </div>

        <div className="space-y-4">
          {Object.keys(explainabilityBySymbol || {}).length === 0 && (
            <div className="text-sm text-zinc-500">No explainability data.</div>
          )}

          {Object.values(explainabilityBySymbol || {}).map((group) => (
            <div key={group.symbol} className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-lg font-medium text-white">{group.symbol}</div>
                <div className="text-xs text-zinc-400">
                  {group.timeline?.length || 0} event(s)
                </div>
              </div>

              <div className="space-y-3">
                {(group.timeline || []).map((event, idx) => (
                  <div key={`${group.symbol}-${idx}`} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm font-medium text-white capitalize">{event.family || "event"}</div>
                      <div className="flex items-center gap-2">
                        <StatusBadge label={event.decision || "UNKNOWN"} />
                        <StatusBadge label={event.decision_class || "UNKNOWN_CLASS"} />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 text-sm text-zinc-300">
                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Score:</span>{" "}
                        {event.narrative?.signal?.score ?? "—"}
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Setup:</span>{" "}
                        {event.narrative?.signal?.setup ?? "—"}
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Signal Side:</span>{" "}
                        {event.narrative?.signal?.side ?? "—"}
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Regime:</span>{" "}
                        {event.narrative?.context?.regime ?? "—"}
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Policy:</span>{" "}
                        {event.narrative?.context?.policy ?? "—"}
                      </div>

                      <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-zinc-400">Decision Class:</span>{" "}
                        {event.decision_class ?? "—"}
                      </div>
                    </div>

                    <div className="mt-3 rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-sm text-zinc-300">
                      <span className="text-zinc-400">Decision reason:</span>{" "}
                      {event.narrative?.decision?.reason ?? "—"}
                      {event.narrative?.decision?.qty ? (
                        <>
                          {" "}· <span className="text-zinc-400">Qty:</span>{" "}
                          {event.narrative.decision.qty}
                        </>
                      ) : null}
                      {event.narrative?.decision?.side ? (
                        <>
                          {" "}· <span className="text-zinc-400">Order side:</span>{" "}
                          {event.narrative.decision.side}
                        </>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <SectionCard title="Risk & Limits" subtitle="Risk status and guardrail layer">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-zinc-400">Risk Status</div>
            <StatusBadge label={riskStatus} />
          </div>

          <div className="space-y-2 text-sm">
            <div>
              <span className="text-zinc-400">Soft vetos:</span>{" "}
              <span>{riskSoftVetos.length ? riskSoftVetos.join(", ") : "None"}</span>
            </div>
            <div>
              <span className="text-zinc-400">Open positions:</span>{" "}
              <span>{risk?.summary?.open_positions ?? "—"}</span>
            </div>
            <div>
              <span className="text-zinc-400">Total notional:</span>{" "}
              <span>{risk?.summary?.total_notional_usd ?? "—"}</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm text-zinc-400 mb-2">Reasons</div>
            <ul className="list-disc pl-5 text-sm text-zinc-300 space-y-1">
              {riskReasons.length === 0 && <li>No risk reason reported.</li>}
              {riskReasons.map((r, idx) => (
                <li key={`risk-${idx}`}>{r}</li>
              ))}
            </ul>
          </div>
        </SectionCard>

        <SectionCard title="Reconciliation" subtitle="Order versus fills versus positions consistency">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-zinc-400">Reconciliation Status</div>
            <StatusBadge label={recoStatus} />
          </div>

          <div className="space-y-2 text-sm">
            <div>
              <span className="text-zinc-400">Anomalies:</span>{" "}
              <span>{recoAnomalies.length}</span>
            </div>
            <div>
              <span className="text-zinc-400">Filled symbols:</span>{" "}
              <span>{fillsSymbols.length ? fillsSymbols.join(", ") : "None"}</span>
            </div>
            <div>
              <span className="text-zinc-400">Position symbols:</span>{" "}
              <span>{positionsSymbols.length ? positionsSymbols.join(", ") : "None"}</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm text-zinc-400 mb-2">Details</div>
            <ul className="list-disc pl-5 text-sm text-zinc-300 space-y-1">
              {recoAnomalies.length === 0 && <li>No anomaly detected.</li>}
              {recoAnomalies.map((a, idx) => (
                <li key={`reco-${idx}`}>{a}</li>
              ))}
            </ul>
          </div>
        </SectionCard>

        <SectionCard title="Exposure" subtitle="Current gross, net, and position-level exposure">
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-zinc-400">Gross exposure:</span>{" "}
              <span>{exposure.gross_exposure_usd ?? "—"}</span>
            </div>
            <div>
              <span className="text-zinc-400">Net exposure:</span>{" "}
              <span>{exposure.net_exposure_usd ?? "—"}</span>
            </div>
            <div>
              <span className="text-zinc-400">Open positions:</span>{" "}
              <span>{exposurePositions.length}</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm text-zinc-400 mb-2">Positions</div>
            <div className="space-y-2">
              {exposurePositions.length === 0 && (
                <div className="text-sm text-zinc-500">No exposure positions.</div>
              )}
              {exposurePositions.map((p, idx) => (
                <div key={`pos-${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm">
                  <div>{p.symbol || "—"} · qty {p.qty ?? "—"}</div>
                  <div className="text-zinc-400 mt-1">
                    notional: {p.notional_usd ?? "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
