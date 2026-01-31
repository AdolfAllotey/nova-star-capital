// src/pages/PnLOverview.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

function formatCurrency(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return `${n.toFixed(2)} €`;
}

export default function PnLOverview() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [series, setSeries] = useState([]);
  const [unit, setUnit] = useState("€");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/pnl/recent", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr(r.error);
        setSeries([]);
        setUnit("€");
        setLoading(false);
        return;
      }

      const s = Array.isArray(r.data?.series) ? r.data.series : [];
      setSeries(s);
      setUnit(r.data?.unit || "€");
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = useMemo(() => {
    if (!series.length) return { last: null, total: null };
    const total = series.reduce((acc, it) => acc + (Number(it?.value ?? it?.y ?? 0) || 0), 0);
    const last = series[series.length - 1];
    const lastVal = Number(last?.value ?? last?.y ?? NaN);
    return { last: Number.isNaN(lastVal) ? null : lastVal, total };
  }, [series]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">PnL</h1>
          <p className="text-sm text-zinc-400">
            Vue PnL (source API) — parsing safe + erreurs normalisées.
          </p>
        </div>
        <div className="text-xs text-zinc-500">Endpoint: /pnl/recent</div>
      </header>

      <SectionCard
        title="Synthèse"
        right={`Unité: ${unit}`}
      >
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && series.length === 0}
          emptyText="Aucune série PnL disponible pour le moment."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Dernière période</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">
                {summary.last === null ? "—" : formatCurrency(summary.last)}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Cumul période</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">
                {summary.total === null ? "—" : formatCurrency(summary.total)}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Points</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{series.length}</div>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500">
                <tr className="border-b border-zinc-800">
                  <th className="py-2 text-left">Label</th>
                  <th className="py-2 text-left">Date</th>
                  <th className="py-2 text-right">Valeur</th>
                </tr>
              </thead>
              <tbody>
                {series.map((it, idx) => {
                  const v = Number(it?.value ?? it?.y ?? NaN);
                  const ok = !Number.isNaN(v);
                  return (
                    <tr key={idx} className="border-b border-zinc-900/60">
                      <td className="py-2">{it?.label ?? it?.x ?? "—"}</td>
                      <td className="py-2 text-zinc-400">{it?.date ?? "—"}</td>
                      <td className={`py-2 text-right ${ok && v >= 0 ? "text-emerald-400" : ok ? "text-red-400" : "text-zinc-500"}`}>
                        {ok ? formatCurrency(v) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </DataState>
      </SectionCard>
    </div>
  );
}
