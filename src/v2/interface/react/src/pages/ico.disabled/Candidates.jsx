// src/pages/ico/Candidates.jsx
// NSC Trading Desk – ICO Candidates (V2 Preprod, style Dashboard)

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

function normalizeCandidates(raw) {
  if (!raw) return [];

  const list = raw.data || raw.items || raw.candidates || raw;
  if (!Array.isArray(list)) return [];

  return list.map((c, index) => ({
    id: c.id || c.slug || `ico-${index}`,
    name: c.name || c.project || "Projet inconnu",
    symbol: c.symbol || c.ticker || "N/A",
    chain: c.chain || c.network || "N/A",
    launch: c.launch_date || c.date || c.when || "N/A",
    hype:
      typeof c.hype === "number"
        ? c.hype
        : typeof c.hype_score === "number"
        ? c.hype_score
        : null,
    risk:
      typeof c.risk === "string"
        ? c.risk
        : Array.isArray(c.risks)
        ? c.risks.join(", ")
        : "Aucun signal détecté",
    source: c.source || c.detected_by || "NSC Scanner",
  }));
}

export default function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [_error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const url = `${API_BASE}/ico/candidates`;
        console.debug("[ICO Candidates] fetch:", url);

        const res = await fetch(url);
        let raw = null;

        if (res.ok) {
          raw = await res.json();
        } else {
          console.warn("[ICO Candidates] HTTP non-OK:", res.status);
        }

        if (cancelled) return;

        const normalized = normalizeCandidates(raw);
        setCandidates(normalized);
        setError("");
      } catch (e) {
        console._error("[ICO Candidates] _error", e);
        if (!cancelled) {
          setCandidates([]);
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

  return (
    <div className="space-y-8">
      {/* HEADER */}
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          NSC Trading Desk – ICO Candidates
        </h1>
        <p className="text-sm text-zinc-400">
          Projets détectés automatiquement par les scrapers Telegram, Twitter, Airdrop,
          Launchpad et flux NSC.
        </p>
      </header>

      {/* (On garde _error dans le state si on veut l’utiliser plus tard, mais on ne spam pas la vue) */}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Chargement des projets ICO…
        </div>
      ) : (
        <>
          {/* STATS */}
          <Section title="Statistiques globales">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <StatCard
                label="Projets détectés"
                value={candidates.length}
                helper="Détection automatique NSC"
              />
              <StatCard
                label="Projets à analyser"
                value={candidates.length}
                helper="Étape suivante : Screening"
              />
            </div>
          </Section>

          {/* TABLE */}
          <Section title="Projets détectés">
            {candidates.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun projet ICO détecté pour le moment. Les premiers résultats apparaîtront
                lorsque les scrapers seront actifs.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-zinc-800">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 px-2 text-left">Projet</th>
                      <th className="py-2 px-2 text-left">Symbole</th>
                      <th className="py-2 px-2 text-left">Réseau</th>
                      <th className="py-2 px-2 text-left">Lancement</th>
                      <th className="py-2 px-2 text-right">Hype</th>
                      <th className="py-2 px-2 text-left">Risque</th>
                      <th className="py-2 px-2 text-left">Source</th>
                    </tr>
                  </thead>

                  <tbody>
                    {candidates.map((c) => (
                      <tr
                        key={c.id}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-2 px-2 font-medium">{c.name}</td>
                        <td className="py-2 px-2">{c.symbol}</td>
                        <td className="py-2 px-2">{c.chain}</td>
                        <td className="py-2 px-2">{c.launch}</td>
                        <td className="py-2 px-2 text-right">
                          {c.hype !== null
                            ? `${(c.hype * 100).toFixed(1)} %`
                            : "n/d"}
                        </td>
                        <td className="py-2 px-2">{c.risk}</td>
                        <td className="py-2 px-2 text-zinc-400">{c.source}</td>
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
              Les projets détectés passeront ensuite dans la pipeline : screening → scoring →
              allocation automatique selon le Market Regime et la gestion du risque NSC.
            </p>
          </Section>
        </>
      )}
    </div>
  );
}