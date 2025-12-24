// src/pages/Metrics.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../lib/api";

function Card({ title, children, className = "" }) {
  return (
    <div
      className={
        "bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 flex flex-col gap-3 " +
        className
      }
    >
      <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
      {children}
    </div>
  );
}

export default function Metrics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      // important : on ne remet pas error à null ici pour éviter certains races en StrictMode
      try {
        const data = await fetchJSON("/metrics");
        if (!cancelled) {
          setMetrics(data || {});
          // si on a des données, on considère que l’état est sain
          setError(null);
        }
      } catch (e) {
        console.error("[Metrics] Error loading /metrics:", e);
        if (!cancelled) {
          setError("Impossible de charger les métriques backend.");
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

  const files = metrics && metrics.files ? metrics.files : {};
  const fileEntries = Object.entries(files);

  const existsCount = fileEntries.filter(
    ([, v]) => v && v.exists
  ).length;

  const missingCount = fileEntries.filter(
    ([, v]) => v && v.exists === false
  ).length;

  // helpers d’affichage de statut
  const statusLabel = (() => {
    if (loading) return <span className="text-amber-400">Chargement…</span>;
    if (error && !metrics) return <span className="text-red-400">Erreur</span>;
    return <span className="text-emerald-400">OK</span>;
  })();

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Metrics & Fichiers</h1>
          <p className="text-sm text-zinc-400">
            Vue technique des fichiers JSON utilisés par le bot Nova Star
            Capital : existence, taille, nombre d’items…
          </p>
        </div>
        <div className="text-[11px] text-zinc-500">
          Endpoint : <code>/metrics</code>
          <br />
          {statusLabel}
        </div>
      </div>

      {/* Résumé global */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="Résumé">
          {error && !metrics ? (
            <p className="text-xs text-red-400">{error}</p>
          ) : !metrics ? (
            <p className="text-xs text-zinc-500">
              Aucune donnée pour l’instant.
            </p>
          ) : (
            <div className="space-y-1 text-sm">
              {metrics.status && (
                <p>
                  <span className="text-zinc-400">Status : </span>
                  <span className="text-zinc-100">{metrics.status}</span>
                </p>
              )}
              {metrics.updated_at && (
                <p>
                  <span className="text-zinc-400">Dernière mise à jour : </span>
                  <span className="text-zinc-100">{metrics.updated_at}</span>
                </p>
              )}
              <p className="text-[11px] text-zinc-500 mt-2">
                Cette vue lit uniquement le JSON retourné par l’API.
                Aucun calcul n’est fait côté client, afin de rester fidèle à
                l’état backend.
              </p>
            </div>
          )}
        </Card>

        <Card title="Fichiers présents">
          {fileEntries.length === 0 ? (
            <p className="text-xs text-zinc-500">
              Aucun détail de fichiers dans /metrics.
            </p>
          ) : (
            <div className="space-y-1 text-sm">
              <p>
                <span className="text-zinc-400">Total référencés : </span>
                <span className="text-zinc-100">{fileEntries.length}</span>
              </p>
              <p>
                <span className="text-zinc-400">Existants : </span>
                <span className="text-emerald-300">{existsCount}</span>
              </p>
              <p>
                <span className="text-zinc-400">Manquants : </span>
                <span className="text-red-300">{missingCount}</span>
              </p>
            </div>
          )}
        </Card>

        <Card title="Debug rapide">
          <div className="text-[11px] text-zinc-400 space-y-1">
            <p>
              Utilise cette page pour vérifier rapidement que les jobs
              (top movers, worst trades, profitability, ICO, etc.) produisent
              bien leurs fichiers JSON.
            </p>
            <p>
              En cas de problème d’interface, commence toujours par vérifier
              ici que les fichiers existent et contiennent des items.
            </p>
          </div>
        </Card>
      </div>

      {/* Tableau des fichiers */}
      <Card title="Détail des fichiers JSON">
        {fileEntries.length === 0 ? (
          <p className="text-xs text-zinc-500">
            Aucun fichier listé dans la clé <code>files</code> de /metrics.
          </p>
        ) : (
          <div className="text-xs overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400">
                  <th className="py-1 pr-2">Clé</th>
                  <th className="py-1 pr-2">Chemin</th>
                  <th className="py-1 pr-2 text-right">Items</th>
                  <th className="py-1 pr-2 text-right">Taille</th>
                  <th className="py-1 pr-0 text-right">Dernière modif</th>
                </tr>
              </thead>
              <tbody>
                {fileEntries.map(([key, info]) => {
                  const exists = info?.exists;
                  const items =
                    typeof info?.items === "number" ? info.items : null;
                  const size =
                    typeof info?.size_bytes === "number"
                      ? info.size_bytes
                      : null;
                  const mtime = info?.mtime || info?.modified || null;

                  return (
                    <tr
                      key={key}
                      className={
                        "border-b border-zinc-900/60 " +
                        (exists
                          ? ""
                          : "bg-red-500/5 hover:bg-red-500/10 transition-colors")
                      }
                    >
                      <td className="py-1 pr-2 align-top">
                        <div className="flex flex-col">
                          <span className="text-zinc-100">{key}</span>
                          <span className="text-[10px] text-zinc-500">
                            {exists ? "OK" : "Manquant"}
                          </span>
                        </div>
                      </td>
                      <td className="py-1 pr-2 align-top">
                        <span className="text-[11px] text-zinc-300 break-all">
                          {info?.path || "—"}
                        </span>
                      </td>
                      <td className="py-1 pr-2 text-right align-top">
                        <span
                          className={
                            "text-[11px] " +
                            (items === null
                              ? "text-zinc-500"
                              : items > 0
                              ? "text-emerald-300"
                              : "text-zinc-300")
                          }
                        >
                          {items === null ? "—" : items}
                        </span>
                      </td>
                      <td className="py-1 pr-2 text-right align-top">
                        <span className="text-[11px] text-zinc-400">
                          {size === null
                            ? "—"
                            : `${(size / 1024).toFixed(1)} Ko`}
                        </span>
                      </td>
                      <td className="py-1 pr-0 text-right align-top">
                        <span className="text-[11px] text-zinc-400">
                          {mtime || "—"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
