// src/pages/ico/Screened.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";

function badgeColor(decision) {
  const d = (decision || "").toLowerCase();
  if (d.includes("whitelist") || d.includes("go") || d.includes("green")) {
    return "bg-emerald-900/60 text-emerald-200 border-emerald-700/70";
  }
  if (d.includes("black") || d.includes("red") || d.includes("avoid")) {
    return "bg-red-950/60 text-red-200 border-red-800/70";
  }
  if (d.includes("watch") || d.includes("hold") || d.includes("neutral")) {
    return "bg-amber-950/60 text-amber-200 border-amber-800/70";
  }
  return "bg-zinc-900/60 text-zinc-200 border-zinc-700/70";
}

export default function IcoScreened() {
  const [data, setData] = useState(null);
  const [decisionFilter, setDecisionFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getJSON("/ico/screened");
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[ICO/Screened] Erreur:", err);
        setError(
          err?.message ||
            "Erreur lors du chargement des ICO après screening."
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
    if (Array.isArray(data.screened)) return data.screened;
    return [];
  }, [data]);

  const filtered = useMemo(() => {
    if (decisionFilter === "all") return items;
    return items.filter((ico) => {
      const d =
        ico.decision || ico.recommendation || ico.label || ico.bucket || "";
      return d.toLowerCase().includes(decisionFilter);
    });
  }, [items, decisionFilter]);

  const updatedAt =
    data?.updated_at || data?.generated_at || data?.refreshed_at || null;

  return (
    <div className="p-6 space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            ICO — Screening
          </h1>
          <p className="text-sm text-zinc-400">
            Résultat du screening fondamental / réputation / risque pour chaque
            projet identifié.
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
              /ico/screened
            </code>
          </div>
        </div>
      </header>

      {/* Filtres */}
      <section className="flex flex-wrap gap-2 text-xs">
        <button
          onClick={() => setDecisionFilter("all")}
          className={`px-3 py-1 rounded-full border ${
            decisionFilter === "all"
              ? "bg-zinc-100 text-zinc-900 border-zinc-100"
              : "bg-zinc-900 text-zinc-200 border-zinc-700"
          }`}
        >
          Tous
        </button>
        <button
          onClick={() => setDecisionFilter("whitelist")}
          className={`px-3 py-1 rounded-full border ${
            decisionFilter === "whitelist"
              ? "bg-emerald-500 text-zinc-900 border-emerald-400"
              : "bg-zinc-900 text-zinc-200 border-zinc-700"
          }`}
        >
          Whitelist / Go
        </button>
        <button
          onClick={() => setDecisionFilter("watch")}
          className={`px-3 py-1 rounded-full border ${
            decisionFilter === "watch"
              ? "bg-amber-500 text-zinc-900 border-amber-400"
              : "bg-zinc-900 text-zinc-200 border-zinc-700"
          }`}
        >
          Watchlist
        </button>
        <button
          onClick={() => setDecisionFilter("black")}
          className={`px-3 py-1 rounded-full border ${
            decisionFilter === "black"
              ? "bg-red-500 text-zinc-900 border-red-400"
              : "bg-zinc-900 text-zinc-200 border-zinc-700"
          }`}
        >
          Blacklist
        </button>
      </section>

      {loading && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-sm text-amber-300">
          Chargement du screening ICO…
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
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-zinc-200">
                Projets après screening
              </h2>
              <span className="text-xs text-zinc-500">
                {filtered.length} projet(s)
              </span>
            </div>

            {filtered.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aucun projet avec ce filtre. Change le filtre ou attends la
                prochaine analyse ICO.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-2 pr-4">Nom</th>
                      <th className="py-2 pr-4">Token</th>
                      <th className="py-2 pr-4">Score risque</th>
                      <th className="py-2 pr-4">Score reward</th>
                      <th className="py-2 pr-4">Décision</th>
                      <th className="py-2 pr-4">Commentaire</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((ico, idx) => {
                      const name = ico.name || ico.project || "—";
                      const symbol = ico.symbol || ico.token || "—";
                      const riskScore =
                        ico.risk_score ??
                        ico.riskScore ??
                        ico.risk ??
                        null;
                      const rewardScore =
                        ico.reward_score ??
                        ico.rewardScore ??
                        ico.potential ??
                        null;
                      const decision =
                        ico.decision ||
                        ico.recommendation ||
                        ico.label ||
                        "—";
                      const comment =
                        ico.comment ||
                        ico.notes ||
                        ico.rationale ||
                        "—";

                      return (
                        <tr
                          key={idx}
                          className="border-b border-zinc-900 last:border-none"
                        >
                          <td className="py-1.5 pr-4 text-zinc-200">{name}</td>
                          <td className="py-1.5 pr-4 text-zinc-300">
                            {symbol}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {riskScore ?? "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {rewardScore ?? "—"}
                          </td>
                          <td className="py-1.5 pr-4">
                            <span
                              className={
                                "inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-medium " +
                                badgeColor(decision)
                              }
                            >
                              {decision}
                            </span>
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {comment}
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
                ico.screened
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
