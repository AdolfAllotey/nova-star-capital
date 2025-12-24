// src/pages/ico/Screened.jsx
// NSC Trading Desk – ICO Screening (V2 Preprod, style Dashboard)

import React, { useEffect, useState } from "react";
import { API_BASE } from "../../lib/apiBase";

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
      <span className="text-xs uppercase tracking-wide text-zinc-400">{label}</span>
      <span className="text-xl font-semibold text-zinc-50">{value}</span>
      {helper && <span className="text-xs text-zinc-500">{helper}</span>}
    </div>
  );
}

function normalizeScreened(raw) {
  if (!raw) return [];

  const list = raw.data || raw.items || raw.screened || raw;
  if (!Array.isArray(list)) return [];

  return list.map((p, index) => ({
    id: p.id || p.slug || `screen-${index}`,
    name: p.name || p.project || "Projet inconnu",
    symbol: p.symbol || "N/A",
    chain: p.chain || p.network || "N/A",
    passed: Boolean(p.passed || p.ok),
    risks:
      Array.isArray(p.risks)
        ? p.risks
        : typeof p.risks === "string"
        ? [p.risks]
        : [],
    reputation: p.reputation || p.rep_score || null,
    flagged:
      Array.isArray(p.flags)
        ? p.flags
        : typeof p.flags === "string"
        ? [p.flags]
        : [],
    summary: p.summary || p.notes || "Aucun résumé disponible.",
    source: p.source || p.detected_by || "NSC Screening Engine",
  }));
}

export default function Screened() {
  const [screened, setScreened] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const url = `${API_BASE}/ico/screened`;
        console.debug("[ICO Screened] Fetch:", url);

        const res = await fetch(url);
        let raw = null;

        if (res.ok) {
          raw = await res.json();
        } else {
          console.warn("[ICO Screened] HTTP non-OK:", res.status);
        }

        if (cancelled) return;

        const normalized = normalizeScreened(raw);
        setScreened(normalized);
        setError("");
      } catch (e) {
        console.error("[ICO Screened] Error:", e);
        if (!cancelled) {
          setScreened([]);
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

  const passedCount = screened.filter((p) => p.passed).length;

  return (
    <div className="space-y-8">
      {/* HEADER */}
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          NSC Trading Desk – ICO Screening
        </h1>
        <p className="text-sm text-zinc-400">
          Analyse des projets détectés : risques, réputation, flags, conformité avant
          passage au scoring complet.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Analyse des projets en cours…
        </div>
      ) : (
        <>
          {/* STATS */}
          <Section title="Statistiques du screening">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <StatCard
                label="Projets analysés"
                value={screened.length}
                helper="Après détection"
              />
              <StatCard
                label="Validés"
                value={passedCount}
                helper="Passent à l'étape scoring"
              />
              <StatCard
                label="Recalés"
                value={screened.length - passedCount}
                helper="Bloqués par flags / risques"
              />
            </div>
          </Section>

          {/* TABLE */}
          <Section title="Résultats du screening">
            {screened.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun projet n’a encore passé la phase de screening.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-zinc-800">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 px-2 text-left">Projet</th>
                      <th className="py-2 px-2 text-left">Symbole</th>
                      <th className="py-2 px-2 text-left">Réseau</th>
                      <th className="py-2 px-2 text-left">Status</th>
                      <th className="py-2 px-2 text-left">Risques</th>
                      <th className="py-2 px-2 text-left">Flags</th>
                      <th className="py-2 px-2 text-left">Résumé</th>
                      <th className="py-2 px-2 text-left">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {screened.map((p) => (
                      <tr
                        key={p.id}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-2 px-2 font-medium">{p.name}</td>
                        <td className="py-2 px-2">{p.symbol}</td>
                        <td className="py-2 px-2">{p.chain}</td>
                        <td className="py-2 px-2">
                          {p.passed ? (
                            <span className="text-emerald-400 font-medium">
                              ✔ Validé
                            </span>
                          ) : (
                            <span className="text-red-400 font-medium">
                              ✖ Rejeté
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2">
                          {p.risks.length > 0 ? p.risks.join(", ") : "—"}
                        </td>
                        <td className="py-2 px-2 text-red-400">
                          {p.flagged.length > 0 ? p.flagged.join(", ") : "—"}
                        </td>
                        <td className="py-2 px-2 text-zinc-300 max-w-lg">
                          {p.summary}
                        </td>
                        <td className="py-2 px-2 text-zinc-500">{p.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* NEXT */}
          <Section title="Prochaines étapes">
            <p className="text-sm text-zinc-500">
              Les projets validés passent à la phase suivante :{" "}
              <strong>ICO Scoring</strong> (fondamentaux, tokenomics, hype, liquidité,
              sentiment, risque).
            </p>
          </Section>
        </>
      )}
    </div>
  );
}
