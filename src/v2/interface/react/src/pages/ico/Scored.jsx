// src/pages/ico/Scored.jsx
// NSC Trading Desk – ICO Scoring (V2 Preprod, style Dashboard)

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

function formatPercent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/d";
  return `${(value * 100).toFixed(1)} %`;
}

function normalizeScored(raw) {
  if (!raw) return [];

  const data = raw.data || raw.items || raw.scored || raw;
  if (!Array.isArray(data)) return [];

  return data.map((p, index) => ({
    id: p.id || p.slug || `score-${index}`,
    name: p.name || "Projet inconnu",
    symbol: p.symbol || "N/A",
    chain: p.chain || "N/A",
    fundamentals: p.fundamentals ?? p.fundamental_score ?? null,
    tokenomics: p.tokenomics ?? p.tokenomics_score ?? null,
    community: p.community ?? p.community_score ?? null,
    hype: p.hype ?? p.hype_score ?? null,
    risk: p.risk ?? p.risk_score ?? null,
    roadmap: p.roadmap ?? p.roadmap_score ?? null,
    score:
      typeof p.score === "number"
        ? p.score
        : p.total_score ?? null,
    summary: p.summary || p.notes || "Aucun résumé disponible.",
  }));
}

export default function Scored() {
  const [scored, setScored] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const url = `${API_BASE}/ico/scored`;
        console.debug("[ICO Scored] Fetch:", url);

        const res = await fetch(url);
        let raw = null;

        if (res.ok) {
          raw = await res.json();
        } else {
          console.warn("[ICO Scored] HTTP non-OK:", res.status);
        }

        if (cancelled) return;

        const normalized = normalizeScored(raw);
        setScored(normalized);
        setError("");
      } catch (e) {
        console.error("[ICO Scored] Error:", e);
        if (!cancelled) {
          setScored([]);
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

  const best =
    scored.length > 0
      ? scored.reduce(
          (acc, p) => (p.score > (acc?.score ?? -Infinity) ? p : acc),
          null
        )
      : null;

  return (
    <div className="space-y-8">
      {/* HEADER */}
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          NSC Trading Desk – ICO Scoring
        </h1>
        <p className="text-sm text-zinc-400">
          Scoring complet des projets : fondamentaux, tokenomics, communauté, hype, risque
          et score global NSC.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Scoring des projets en cours…
        </div>
      ) : (
        <>
          {/* SUMMARY CARDS */}
          <Section title="Statistiques du scoring">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <StatCard
                label="Projets scorés"
                value={scored.length}
                helper="Après screening"
              />
              <StatCard
                label="Score moyen"
                value={
                  scored.length > 0
                    ? `${(
                        scored.reduce((a, b) => a + (b.score ?? 0), 0) /
                        scored.length
                      ).toFixed(2)}`
                    : "n/d"
                }
                helper="Score global moyen"
              />
              <StatCard
                label="Top score"
                value={best ? best.score.toFixed(2) : "n/d"}
                helper={best ? best.name : ""}
              />
            </div>
          </Section>

          {/* BEST PROJECT */}
          <Section title="Meilleur potentiel (Top 1)">
            {!best ? (
              <p className="text-sm text-zinc-500">
                Aucun projet n’a encore été scoré.
              </p>
            ) : (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-zinc-100">
                  {best.name} ({best.symbol})
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <StatCard label="Score global" value={best.score.toFixed(2)} />
                  <StatCard
                    label="Fondamentaux"
                    value={formatPercent(best.fundamentals)}
                  />
                  <StatCard
                    label="Tokenomics"
                    value={formatPercent(best.tokenomics)}
                  />
                  <StatCard
                    label="Communauté"
                    value={formatPercent(best.community)}
                  />
                  <StatCard label="Hype" value={formatPercent(best.hype)} />
                  <StatCard label="Risque" value={formatPercent(best.risk)} />
                </div>

                <p className="text-sm text-zinc-400 mt-2">{best.summary}</p>
              </div>
            )}
          </Section>

          {/* FULL TABLE */}
          <Section title="Détails du scoring">
            {scored.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun projet scoré pour le moment.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-zinc-800">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 px-2 text-left">Projet</th>
                      <th className="py-2 px-2 text-right">Global</th>
                      <th className="py-2 px-2 text-right">Fundamentaux</th>
                      <th className="py-2 px-2 text-right">Tokenomics</th>
                      <th className="py-2 px-2 text-right">Communauté</th>
                      <th className="py-2 px-2 text-right">Hype</th>
                      <th className="py-2 px-2 text-right">Risque</th>
                      <th className="py-2 px-2 text-left">Résumé</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scored.map((p) => (
                      <tr
                        key={p.id}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-2 px-2 font-medium">
                          {p.name} ({p.symbol})
                        </td>
                        <td className="py-2 px-2 text-right">
                          {p.score?.toFixed(2) ?? "n/d"}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(p.fundamentals)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(p.tokenomics)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(p.community)}
                        </td>
                        <td className="py-2 px-2 text-right">
                          {formatPercent(p.hype)}
                        </td>
                        <td className="py-2 px-2 text-right text-red-400">
                          {formatPercent(p.risk)}
                        </td>
                        <td className="py-2 px-2 text-left text-zinc-400">
                          {p.summary}
                        </td>
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
              Les projets scorés passent ensuite à l’étape finale :{" "}
              <strong>ICO Allocation</strong> (budget, sizing, contraintes de risque,
              regime de marché).
            </p>
          </Section>
        </>
      )}
    </div>
  );
}
