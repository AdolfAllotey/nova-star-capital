// src/pages/SystemStatus.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../lib/api";

function StatusPill({ ok }) {
  const color = ok ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300";
  const label = ok ? "OK" : "KO";
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium " +
        color
      }
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current mr-1" />
      {label}
    </span>
  );
}

export default function SystemStatus() {
  const [rootStatus, setRootStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // On essaye de charger / et /metrics en parallèle
        const [rootRes, metricsRes] = await Promise.allSettled([
          fetchJSON("/"),
          fetchJSON("/metrics"),
        ]);

        if (cancelled) return;

        if (rootRes.status === "fulfilled") {
          setRootStatus(rootRes.value);
        } else {
          console.warn("SystemStatus: / error", rootRes.reason);
        }

        if (metricsRes.status === "fulfilled") {
          setMetrics(metricsRes.value);
        } else {
          console.warn("SystemStatus: /metrics error", metricsRes.reason);
        }

        if (
          rootRes.status === "rejected" &&
          metricsRes.status === "rejected"
        ) {
          setError("Impossible de charger les informations système.");
        }
      } catch (err) {
        if (cancelled) return;
        console.error("SystemStatus fatal error:", err);
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const apiOk = !!rootStatus;
  const metricsOk = !!metrics;

  const files = metrics?.files || {};
  const topMoversFile = files["market.top_movers"];
  const openPositionsFile = files["trading.open_positions"];
  const worstTradesFile = files["risk.worst_trades"];
  const pnlFile = files["profit.monthly_pnl"];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">System status</h1>
          <p className="text-sm text-zinc-400">
            Vue rapide de l’état du backend Nova Star Capital (API, fichiers
            clés, métriques).
          </p>
        </div>
        {loading && (
          <div className="text-xs text-zinc-500">Chargement…</div>
        )}
      </header>

      {/* Bloc d’erreur global éventuel */}
      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">
          Erreur lors du chargement du status système :{" "}
          <span className="font-mono">{error}</span>
        </div>
      )}

      {/* Cartes de statut principaux */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* API */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-200">API backend</h2>
            <StatusPill ok={apiOk} />
          </div>
          <p className="text-xs text-zinc-400">
            {apiOk
              ? rootStatus?.message || "Backend API is running"
              : "Impossible de joindre /"}
          </p>
          {apiOk && (
            <p className="text-[11px] text-zinc-500 mt-1">
              Version : <span className="font-mono">{rootStatus?.version}</span>
            </p>
          )}
        </div>

        {/* Metrics */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-200">Metrics</h2>
            <StatusPill ok={metricsOk} />
          </div>
          <p className="text-xs text-zinc-400">
            {metricsOk
              ? "Endpoint /metrics accessible."
              : "Endpoint /metrics non disponible."}
          </p>
          {metricsOk && (
            <p className="text-[11px] text-zinc-500 mt-1">
              Fichiers suivis :{" "}
              <span className="font-mono">
                {Object.keys(files).length || 0}
              </span>
            </p>
          )}
        </div>

        {/* Market data */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-200">Market data</h2>
            <StatusPill ok={!!topMoversFile} />
          </div>
          <p className="text-xs text-zinc-400">
            Fichier <span className="font-mono">market.top_movers</span>
          </p>
          {topMoversFile && (
            <p className="text-[11px] text-zinc-500 mt-1">
              Items :{" "}
              <span className="font-mono">
                {topMoversFile.items ?? "?"}
              </span>{" "}
              — Taille :{" "}
              <span className="font-mono">
                {(topMoversFile.size_bytes ?? 0).toLocaleString("fr-FR")} o
              </span>
            </p>
          )}
        </div>

        {/* Trading / Risk */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-200">
              Trading &amp; Risk
            </h2>
            <StatusPill ok={!!(openPositionsFile || worstTradesFile || pnlFile)} />
          </div>
          <p className="text-xs text-zinc-400">
            Fichiers clés :{" "}
            <span className="font-mono">open_positions, worst_trades, pnl</span>
          </p>
          <ul className="text-[11px] text-zinc-500 mt-1 space-y-0.5">
            <li>
              open_positions :{" "}
              <StatusPill ok={!!openPositionsFile} />
            </li>
            <li>
              worst_trades : <StatusPill ok={!!worstTradesFile} />
            </li>
            <li>
              monthly_pnl : <StatusPill ok={!!pnlFile} />
            </li>
          </ul>
        </div>
      </div>

      {/* Debug bas de page */}
      <details className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-xs text-zinc-400">
        <summary className="cursor-pointer text-zinc-300">
          Détails bruts (debug)
        </summary>
        <div className="mt-2 space-y-2">
          <div>
            <div className="font-medium text-zinc-300 mb-1">/ (root)</div>
            <pre className="whitespace-pre-wrap break-all bg-zinc-900/60 rounded-lg p-2">
              {JSON.stringify(rootStatus, null, 2)}
            </pre>
          </div>
          <div>
            <div className="font-medium text-zinc-300 mb-1">/metrics</div>
            <pre className="whitespace-pre-wrap break-all bg-zinc-900/60 rounded-lg p-2">
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
        </div>
      </details>
    </div>
  );
}
