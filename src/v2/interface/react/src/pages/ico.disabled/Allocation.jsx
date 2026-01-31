// src/pages/ico/Allocation.jsx
// NSC Trading Desk – ICO Allocation (V2 Preprod, style Dashboard)

import React, { useEffect, useState } from "react";
import { API_BASE } from "../../lib/apiBase";

function StatCard({ label, value, helper }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-400">
        {label}
      </span>
      <span className="text-xl font-semibold text-zinc-50">
        {value ?? "–"}
      </span>
      {helper && <span className="text-xs text-zinc-500">{helper}</span>}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-zinc-100 mb-3 border-b border-zinc-800 pb-1">
        {title}
      </h2>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function StatCard({ label, value, helper }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-400">
        {label}
      </span>
      <span className="text-xl font-semibold text-zinc-50">{value}</span>
      {helper && <span className="text-xs text-zinc-500">{helper}</span>}
    </div>
  );
}

function formatCurrency(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/d";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(value);
}

function formatPercent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/d";
  return `${(value * 100).toFixed(1)} %`;
}

function normalizeAllocation(raw) {
  if (!raw) return [];

  const list = raw.data || raw.items || raw.allocation || raw;
  if (!Array.isArray(list)) return [];

  return list.map((p, index) => ({
    id: p.id || p.slug || `alloc-${index}`,
    name: p.name || "Projet inconnu",
    symbol: p.symbol || "N/A",
    chain: p.chain || p.network || "N/A",
    decision: p.decision || p.status || "watch", // invest / watch / reject
    allocationEur:
      typeof p.allocation_eur === "number"
        ? p.allocation_eur
        : typeof p.budget_eur === "number"
        ? p.budget_eur
        : null,
    allocationPct:
      typeof p.allocation_pct === "number"
        ? p.allocation_pct
        : typeof p.weight === "number"
        ? p.weight
        : null,
    regime: p.regime || p.market_regime || null,
    riskBucket: p.risk_bucket || p.risk_level || null,
    expectedRoi: p.expected_roi ?? p.expected_return ?? null,
    notes: p.notes || p.rationale || "Aucune note spécifique.",
  }));
}

export default function Allocation() {
  const [allocations, setAllocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [_error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const url = `${API_BASE}/ico/allocation`;
        console.debug("[ICO Allocation] Fetch:", url);

        const res = await fetch(url);
        let raw = null;

        if (res.ok) {
          raw = await res.json();
        } else {
          console.warn("[ICO Allocation] HTTP non-OK:", res.status);
        }

        if (cancelled) return;

        const normalized = normalizeAllocation(raw);
        setAllocations(normalized);
        setError("");
      } catch (e) {
        console._error("[ICO Allocation] Error:", e);
        if (!cancelled) {
          setAllocations([]);
          setError("");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const totalBudget = allocations.reduce(
    (sum, a) => sum + (a.allocationEur || 0),
    0
  );
  const investCount = allocations.filter((a) => a.decision === "invest").length;

  const topAlloc =
    allocations.length > 0
      ? allocations.reduce(
          (acc, p) =>
            (p.allocationEur || 0) > (acc?.allocationEur || 0) ? p : acc,
          null
        )
      : null;

  return (
    <div className="space-y-8">
      {/* HEADER */}
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          NSC Trading Desk – ICO Allocation
        </h1>
        <p className="text-sm text-zinc-400">
          Répartition finale du budget sur les projets ICO validés, en fonction du scoring,
          du régime de marché et des contraintes de risque NSC.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Calcul du plan d’allocation…
        </div>
      ) : (
        <>
          {/* STATS */}
          <Section title="Vue globale">
            {allocations.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun plan d’allocation n’est disponible pour le moment.
              </p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <StatCard
                  label="Projets alloués"
                  value={allocations.length}
                  helper="Inclut invest / watch / reject"
                />
                <StatCard
                  label="Projets en investissement"
                  value={investCount}
                  helper="Décision = invest"
                />
                <StatCard
                  label="Budget total"
                  value={formatCurrency(totalBudget)}
                  helper="Somme des montants alloués"
                />
              </div>
            )}
          </Section>

          {/* TOP ALLOCATION */}
          <Section title="Plus grosse allocation">
            {!topAlloc ? (
              <p className="text-sm text-zinc-500">
                Aucune allocation à afficher pour le moment.
              </p>
            ) : (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-zinc-100">
                  {topAlloc.name} ({topAlloc.symbol})
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <StatCard
                    label="Montant alloué"
                    value={formatCurrency(topAlloc.allocationEur || 0)}
                  />
                  <StatCard
                    label="Poids"
                    value={formatPercent(topAlloc.allocationPct || 0)}
                  />
                  <StatCard
                    label="Décision"
                    value={
                      topAlloc.decision === "invest"
                        ? "Invest"
                        : topAlloc.decision === "reject"
                        ? "Reject"
                        : "Watch"
                    }
                  />
                  <StatCard
                    label="Regime"
                    value={topAlloc.regime || "n/d"}
                  />
                  <StatCard
                    label="Risque"
                    value={topAlloc.riskBucket || "n/d"}
                  />
                  <StatCard
                    label="ROI attendu"
                    value={
                      typeof topAlloc.expectedRoi === "number"
                        ? formatPercent(topAlloc.expectedRoi)
                        : "n/d"
                    }
                  />
                </div>

                <p className="text-sm text-zinc-400 mt-2">{topAlloc.notes}</p>
              </div>
            )}
          </Section>

          {/* TABLE DETAILLEE */}
          <Section title="Plan d’allocation détaillé">
            {allocations.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun projet n’est actuellement alloué.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-zinc-800">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 px-2 text-left">Projet</th>
                      <th className="py-2 px-2 text-left">Réseau</th>
                      <th className="py-2 px-2 text-left">Décision</th>
                      <th className="py-2 px-2 text-right">Montant (€)</th>
                      <th className="py-2 px-2 text-right">Poids</th>
                      <th className="py-2 px-2 text-left">Régime</th>
                      <th className="py-2 px-2 text-left">Risque</th>
                      <th className="py-2 px-2 text-right">ROI attendu</th>
                      <th className="py-2 px-2 text-left">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allocations.map((p) => (
                      <tr
                        key={p.id}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-2 px-2 font-medium">
                          {p.name} ({p.symbol})
                        </td>
                        <td className="py-2 px-2">{p.chain}</td>
                        <td className="py-2 px-2">
                          {p.decision === "invest" && (
                            <span className="text-emerald-400 font-medium">
                              Invest
                            </span>
                          )}
                          {p.decision === "reject" && (
                            <span className="text-red-400 font-medium">
                              Reject
                            </span>
                          )}
                          {p.decision === "watch" && (
                            <span className="text-yellow-400 font-medium">
                              Watch
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {p.allocationEur !== null
                            ? formatCurrency(p.allocationEur)
                            : "n/d"}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {p.allocationPct !== null
                            ? formatPercent(p.allocationPct)
                            : "n/d"}
                        </td>
                        <td className="py-2 px-2 text-left">
                          {p.regime || "n/d"}
                        </td>
                        <td className="py-2 px-2 text-left">
                          {p.riskBucket || "n/d"}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {typeof p.expectedRoi === "number"
                            ? formatPercent(p.expectedRoi)
                            : "n/d"}
                        </td>
                        <td className="py-2 px-2 text-left text-zinc-400">
                          {p.notes}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* NOTES FUTURES */}
          <Section title="Notes & prochaines actions">
            <p className="text-sm text-zinc-500">
              À terme, cette page pourra se connecter à un module d’exécution
              semi-automatique (NSC V3+), avec validation manuelle, limites de risque et
              intégration comptable NSC.
            </p>
          </Section>
        </>
      )}
    </div>
  );
}