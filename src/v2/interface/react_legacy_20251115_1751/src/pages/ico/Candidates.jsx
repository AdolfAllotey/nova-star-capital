// src/pages/ico/Candidates.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";

function formatDate(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString("fr-FR", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return String(value);
  }
}

export default function IcoCandidates() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getJSON("/ico/candidates");
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[ICO/Candidates] Erreur:", err);
        setError(err?.message || "Erreur lors du chargement des ICO candidates.");
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
    if (Array.isArray(data.candidates)) return data.candidates;
    return [];
  }, [data]);

  const updatedAt =
    data?.updated_at || data?.generated_at || data?.refreshed_at || null;

  return (
    <div className="p-6 space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            ICO — Candidates
          </h1>
          <p className="text-sm text-zinc-400">
            Flux brut des nouvelles opportunités ICO / IDO / IEO détectées par le scanner NSC.
          </p>
        </div>
        <div className="text-xs text-right text-zinc-500 space-y-1">
          <div>
            Dernière mise à jour :{" "}
            <span className="text-zinc-300">{formatDate(updatedAt)}</span>
          </div>
          <div>
            Endpoint :{" "}
            <code className="bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-300">
              /ico/candidates
            </code>
          </div>
        </div>
      </header>

      {loading && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-sm text-amber-300">
          Chargement des candidates ICO…
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
                Liste des projets détectés
              </h2>
              <span className="text-xs text-zinc-500">
                {items.length} projet(s)
              </span>
            </div>

            {items.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aucun projet en attente pour le moment. Dès que le scanner
                ICO sera exécuté, les nouvelles opportunités apparaîtront ici.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-2 pr-4">Nom</th>
                      <th className="py-2 pr-4">Token</th>
                      <th className="py-2 pr-4">Réseau</th>
                      <th className="py-2 pr-4">Date vente</th>
                      <th className="py-2 pr-4">Hard cap</th>
                      <th className="py-2 pr-4">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((ico, idx) => {
                      const name = ico.name || ico.project || ico.title || "—";
                      const symbol = ico.symbol || ico.token || "—";
                      const chain =
                        ico.chain || ico.network || ico.blockchain || "—";
                      const saleDate =
                        ico.sale_date ||
                        ico.listing_date ||
                        ico.event_date ||
                        null;
                      const hardCap =
                        ico.hard_cap || ico.hardcap || ico.raise_target || null;
                      const source =
                        ico.source || ico.origin || ico.platform || "—";

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
                            {chain}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {formatDate(saleDate)}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {hardCap ?? "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {source}
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
                ico.candidates
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
