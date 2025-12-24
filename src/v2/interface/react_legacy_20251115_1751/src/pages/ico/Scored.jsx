// src/pages/ico/Scored.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import Sparkline from "../../components/Sparkline.jsx";

function formatScore(x) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return Number(x).toFixed(1);
}

export default function IcoScored() {
  const [data, setData] = useState(null);
  const [minScore, setMinScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getJSON("/ico/scored");
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[ICO/Scored] Erreur:", err);
        setError(
          err?.message ||
            "Erreur lors du chargement des scores ICO (NSC score, risk/reward…)."
        );
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, []);

  const items = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.scored)) return data.scored;
    return [];
  }, [data]);

  const filtered = useMemo(() => {
    return items.filter((ico) => {
      const score =
        ico.nsc_score ??
        ico.score ??
        ico.overall_score ??
        ico.global_score ??
        0;
      return Number(score) >= Number(minScore || 0);
    });
  }, [items, minScore]);

  const updatedAt =
    data?.updated_at || data?.generated_at || data?.refreshed_at || null;

  return (
    <div className="p-6 space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            ICO — NSC Scoring
          </h1>
          <p className="text-sm text-zinc-400">
            Score consolidé NSC (fondamental, réputation, tokenomics,
            momentum…) pour prioriser les investissements.
          </p>
        </div>
        <div className="text-xs text-right text-zinc-500 space-y-1">
          <div>
            Dernière mise à jour :{" "}
            <span className="text-zinc-300">{updatedAt || "—"}</span>
          </div>
          <div>
            Endpoint :{" "}
            <code className="bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-300">
              /ico/scored
            </code>
          </div>
        </div>
      </header>

      {/* Filtre min score */}
      <section className="flex flex-wrap items-center gap-2 text-xs">
        <label className="text-zinc-400">
          Score NSC minimum :
          <input
            type="number"
            min={0}
            max={100}
            step={5}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="ml-2 w-16 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
          />
        </label>
        <span className="text-zinc-500">
          Projets visibles :{" "}
          <span className="text-zinc-200">{filtered.length}</span>
        </span>
      </section>

      {loading && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-sm text-amber-300">
          Chargement des scores ICO…
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-200">
          Erreur : {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
            {filtered.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aucun projet ne respecte le score minimum sélectionné.
                Diminue le seuil ou attends la prochaine mise à jour ICO.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-2 pr-4">Nom</th>
                      <th className="py-2 pr-4">Token</th>
                      <th className="py-2 pr-4">NSC score</th>
                      <th className="py-2 pr-4">Risk</th>
                      <th className="py-2 pr-4">Reward</th>
                      <th className="py-2 pr-4">Momentum</th>
                      <th className="py-2 pr-4">Profil</th>
                      <th className="py-2 pr-4">Évolution score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((ico, idx) => {
                      const name = ico.name || ico.project || "—";
                      const symbol = ico.symbol || ico.token || "—";

                      const nscScore =
                        ico.nsc_score ??
                        ico.score ??
                        ico.overall_score ??
                        ico.global_score ??
                        null;

                      const risk =
                        ico.risk_score ??
                        ico.risk ??
                        ico.riskLevel ??
                        null;

                      const reward =
                        ico.reward_score ??
                        ico.potential ??
                        ico.alpha_score ??
                        null;

                      const momentum =
                        ico.momentum_score ??
                        ico.momentum ??
                        ico.hype_score ??
                        null;

                      const profile =
                        ico.profile ||
                        ico.bucket ||
                        ico.segment ||
                        "—";

                      const history =
                        ico.score_history ||
                        ico.history ||
                        ico.momentum_history ||
                        [];

                      return (
                        <tr
                          key={idx}
                          className="border-b border-zinc-900 last:border-none"
                        >
                          <td className="py-1.5 pr-4 text-zinc-200">
                            {name}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-300">
                            {symbol}
                          </td>
                          <td className="py-1.5 pr-4 text-emerald-300 font-semibold">
                            {formatScore(nscScore)}
                          </td>
                          <td className="py-1.5 pr-4 text-red-300">
                            {formatScore(risk)}
                          </td>
                          <td className="py-1.5 pr-4 text-amber-300">
                            {formatScore(reward)}
                          </td>
                          <td className="py-1.5 pr-4 text-sky-300">
                            {formatScore(momentum)}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {profile}
                          </td>
                          <td className="py-1.5 pr-4">
                            {Array.isArray(history) && history.length > 1 ? (
                              <Sparkline
                                data={history}
                                className="h-8 w-24"
                              />
                            ) : (
                              <span className="text-zinc-500">n/a</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-4 text-xs text-zinc-400 font-mono max-h-[260px] overflow-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-300 font-semibold">Debug JSON</span>
              <span className="text-[10px] uppercase tracking-wide bg-zinc-900 px-2 py-0.5 rounded-full">
                ico.scored
              </span>
            </div>
            <pre className="whitespace-pre-wrap break-words">
              {data ? JSON.stringify(data, null, 2) : "Aucune donnée."}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
