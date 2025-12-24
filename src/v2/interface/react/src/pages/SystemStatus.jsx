// src/pages/SystemStatus.jsx
// État global du système NSC – basé sur / et /metrics

import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function StatusBadge({ ok }) {
  const color = ok
    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/40"
    : "bg-rose-500/10 text-rose-400 border-rose-500/40";

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border ${color}`}
    >
      <span
        className={`mr-1 h-1.5 w-1.5 rounded-full ${
          ok ? "bg-emerald-400" : "bg-rose-400"
        }`}
      ></span>
      {ok ? "OK" : "ERROR"}
    </span>
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

export default function SystemStatus() {
  const [rootInfo, setRootInfo] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function safeFetch(path) {
      try {
        const res = await fetch(buildUrl(path));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return await res.json();
      } catch (e) {
        console.error(`Erreur fetch ${path}:`, e);
        return null;
      }
    }

    async function loadStatus() {
      setLoading(true);
      setError("");

      const [root, m] = await Promise.all([
        safeFetch("/"),
        safeFetch("/metrics"),
      ]);

      if (cancelled) return;

      setRootInfo(root);
      setMetrics(m);

      // On considère que c’est une vraie erreur seulement si les 2 appels sont KO
      if (!root && !m) {
        setError("Impossible de charger l’état du système (API indisponible).");
      } else {
        setError("");
      }

      setLoading(false);
    }

    loadStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  const apiOk = !!rootInfo;
  const files = metrics?.files || {};

  return (
    <div className="space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            NSC Trading Desk – System Status
          </h1>
          <p className="text-sm text-zinc-400">
            Vue d’ensemble de la santé de l’API, des fichiers JSON et des
            briques critiques avant mise en production.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <div className="flex flex-col items-end">
            <span className="text-[11px] uppercase tracking-wide text-zinc-500">
              API Status
            </span>
            <StatusBadge ok={apiOk} />
          </div>
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Chargement de l’état du système…
        </div>
      ) : (
        <>
          {/* Bloc général */}
          <Section title="Statut général">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-zinc-500">
                  Statut général
                </span>
                <StatusBadge ok={apiOk} />
                {!apiOk && (
                  <span className="text-xs text-zinc-500">
                    Impossible de joindre l’API racine (GET /).
                  </span>
                )}
              </div>

              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-zinc-500">
                  Version déployée
                </span>
                <span className="text-sm text-zinc-100">
                  {rootInfo?.version || "n/d"}
                </span>
                <span className="text-xs text-zinc-500">
                  {rootInfo?.project || "Nova Star Capital"}
                </span>
              </div>

              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-zinc-500">
                  Message
                </span>
                <span className="text-sm text-zinc-100">
                  {rootInfo?.message || "API non joignable"}
                </span>
              </div>
            </div>
          </Section>

          {/* Bloc Fichiers / Modules */}
          <Section title="Fichiers & modules">
            {Object.keys(files).length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun détail de fichiers n’est disponible pour le moment.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 text-left">Module</th>
                      <th className="py-2 text-left">Path</th>
                      <th className="py-2 text-center">Existe</th>
                      <th className="py-2 text-right">Taille</th>
                      <th className="py-2 text-right">Items</th>
                      <th className="py-2 text-right">Dernière maj</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(files).map(([key, info]) => {
                      const ok = info.exists && info.size_bytes > 0;
                      return (
                        <tr
                          key={key}
                          className="border-b border-zinc-900/60 align-top"
                        >
                          <td className="py-2 pr-4 text-xs text-zinc-300">
                            {key}
                          </td>
                          <td className="py-2 pr-4 text-[11px] text-zinc-500 font-mono">
                            {info.path}
                          </td>
                          <td className="py-2 text-center">
                            <StatusBadge ok={ok} />
                          </td>
                          <td className="py-2 text-right text-xs text-zinc-300">
                            {info.size_bytes
                              ? `${info.size_bytes} o`
                              : "0 o"}
                          </td>
                          <td className="py-2 text-right text-xs text-zinc-300">
                            {typeof info.items === "number"
                              ? info.items
                              : "n/d"}
                          </td>
                          <td className="py-2 text-right text-[11px] text-zinc-500">
                            {info.mtime || "n/d"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <Section title="Notes">
            <p className="text-sm text-zinc-400">
              Cette page est surtout utile avant la mise en production réelle
              pour vérifier que les fichiers JSON alimentés par les jobs
              quotidiens existent et contiennent des données. Un fichier
              marqué en <span className="text-rose-400">ERROR</span> peut
              simplement signifier qu’aucun run de préproduction n’a encore
              produit de données pour ce module.
            </p>
          </Section>
        </>
      )}
    </div>
  );
}
