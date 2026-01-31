// src/pages/SystemStatus.jsx
import React, { useEffect, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { apiUrl, fetchJson } from "../lib/apiClient";

export default function SystemStatus() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/metrics", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr(r.error || "Erreur API");
        setMetrics(null);
        setLoading(false);
        return;
      }

      setMetrics(r.data || null);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">System Status</h1>
          <p className="text-sm text-zinc-400">
            Santé de l’API + environnement PREPROD.
          </p>
        </div>
        <div className="text-xs text-zinc-500">Source: {apiUrl("/metrics")}</div>
      </header>

      <SectionCard title="Metrics">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !metrics}
          emptyText="Aucune donnée metrics."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">App</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{metrics?.app || "—"}</div>
              <div className="mt-1 text-xs text-zinc-500">Host: {metrics?.host || "—"}</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Env</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{metrics?.env || "—"}</div>
              <div className="mt-1 text-xs text-zinc-500">Version: {metrics?.version || "—"}</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Status</div>
              <div className={"mt-1 text-xl font-semibold " + (metrics?.status === "ok" ? "text-emerald-400" : "text-amber-300")}>
                {metrics?.status || "—"}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Uptime: {metrics?.uptime_s ? `${Math.round(metrics.uptime_s)}s` : "—"}
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
            <div className="text-xs text-zinc-400 mb-2">Raw</div>
            <pre className="text-xs text-zinc-300 overflow-x-auto">
{JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
        </DataState>
      </SectionCard>
    </div>
  );
}
