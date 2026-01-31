// src/pages/Dashboard.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { apiUrl, fetchJson } from "../lib/apiClient";

function n(v) {
  if (v === null || v === undefined) return null;
  const x = typeof v === "number" ? v : Number(v);
  return Number.isNaN(x) ? null : x;
}

function fmt(v, digits = 2) {
  const x = n(v);
  if (x === null) return "—";
  return x.toFixed(digits);
}

function fmtCurrency(v) {
  const x = n(v);
  if (x === null) return "—";
  return `${x.toFixed(2)} €`;
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const [metrics, setMetrics] = useState(null);
  const [pnlRecent, setPnlRecent] = useState(null);
  const [topMovers, setTopMovers] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const [m, p, t] = await Promise.all([
        fetchJson("/metrics", { timeoutMs: 8000 }),
        fetchJson("/pnl/recent", { timeoutMs: 8000 }),
        fetchJson("/market/top-movers", { timeoutMs: 8000 }),
      ]);

      if (cancelled) return;

      const firstErr = [m, p, t].find((x) => x && x.ok === false);
      if (firstErr) {
        setErr(firstErr.error || "Erreur API");
        setMetrics(null);
        setPnlRecent(null);
        setTopMovers(null);
        setLoading(false);
        return;
      }

      setMetrics(m?.data || null);
      setPnlRecent(p?.data || null);
      setTopMovers(t?.data || null);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const pnlSum = useMemo(() => {
    const series = pnlRecent?.series;
    if (!Array.isArray(series)) return null;
    return series.reduce((a, it) => a + (n(it?.value ?? it?.y) || 0), 0);
  }, [pnlRecent]);

  const moversCount = useMemo(() => {
    const items = topMovers?.items;
    if (!Array.isArray(items)) return 0;
    return items.length;
  }, [topMovers]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Dashboard</h1>
          <p className="text-sm text-zinc-400">
            Vue globale (PREPROD). KPI + santé API.
          </p>
        </div>
        <div className="text-xs text-zinc-500">
          API: <code>{apiUrl("")}</code>
        </div>
      </header>

      <SectionCard title="KPI (snapshot)">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !metrics && !pnlRecent && !topMovers}
          emptyText="Aucune donnée disponible pour le moment."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">API Status</div>
              <div className="mt-1 text-xl font-semibold text-emerald-400">
                {metrics?.status || "—"}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Uptime: {metrics?.uptime_s ? `${Math.round(metrics.uptime_s)}s` : "—"}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Env</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">
                {metrics?.env || "—"}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Version: {metrics?.version || "—"}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">PnL (recent)</div>
              <div className={"mt-1 text-xl font-semibold " + ((pnlSum ?? 0) >= 0 ? "text-emerald-400" : "text-red-400")}>
                {pnlSum === null ? "—" : fmtCurrency(pnlSum)}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Source: <code>/pnl/recent</code>
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Top movers</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">
                {moversCount || 0}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                Source: <code>/market/top-movers</code>
              </div>
            </div>
          </div>
        </DataState>
      </SectionCard>

      <SectionCard
        title="Sources"
        description="Endpoints utilisés par cette page (debug rapide)."
      >
        <ul className="text-sm text-zinc-300 space-y-2">
          <li><code className="text-zinc-400">{apiUrl("/metrics")}</code></li>
          <li><code className="text-zinc-400">{apiUrl("/pnl/recent")}</code></li>
          <li><code className="text-zinc-400">{apiUrl("/market/top-movers")}</code></li>
        </ul>
      </SectionCard>
    </div>
  );
}
