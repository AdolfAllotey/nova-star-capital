// src/pages/ico/Allocation.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  try {
    return Number(value).toLocaleString("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    });
  } catch {
    return String(value);
  }
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  try {
    return `${Number(value).toFixed(1)} %`;
  } catch {
    return String(value);
  }
}

export default function IcoAllocation() {
  const [data, setData] = useState(null);
  const [bucketFilter, setBucketFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Chargement des données depuis l'API
  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getIcoAllocation(); // --> /ico/allocation
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[ICO/Allocation] Erreur:", err);
        setError(
          err?.message ||
            "Erreur lors du chargement du plan d'allocation ICO."
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
    if (!data || !Array.isArray(data.items)) return [];
    let list = data.items;

    if (bucketFilter !== "all") {
      list = list.filter((it) => (it.bucket || "autre") === bucketFilter);
    }
    return list;
  }, [data, bucketFilter]);

  const buckets = useMemo(() => {
    if (!data || !Array.isArray(data.items)) return [];
    const set = new Set();
    for (const it of data.items) {
      if (it.bucket) set.add(it.bucket);
    }
    return Array.from(set);
  }, [data]);

  const totals = useMemo(() => {
    if (!data || !Array.isArray(data.items)) return null;
    const totalAllocated = data.items.reduce(
      (acc, it) => acc + (Number(it.allocated_eur) || 0),
      0
    );
    const totalWeight = data.items.reduce(
      (acc, it) => acc + (Number(it.weight) || 0),
      0
    );
    return { totalAllocated, totalWeight };
  }, [data]);

  const filteredTotals = useMemo(() => {
    if (!items.length) return null;
    const totalAllocated = items.reduce(
      (acc, it) => acc + (Number(it.allocated_eur) || 0),
      0
    );
    const totalWeight = items.reduce(
      (acc, it) => acc + (Number(it.weight) || 0),
      0
    );
    return { totalAllocated, totalWeight };
  }, [items]);

  return (
    <div className="flex flex-col gap-4">
      {/* En-tête */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">ICO — Allocation</h1>
          <p className="text-sm text-zinc-400">
            Vue synthétique du plan d&apos;allocation par projet ICO.
          </p>
          {data?.updated_at && (
            <p className="text-xs text-zinc-500 mt-1">
              Dernière mise à jour :{" "}
              {new Date(data.updated_at).toLocaleString("fr-FR")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-zinc-300">Filtre bucket :</label>
          <select
            value={bucketFilter}
            onChange={(e) => setBucketFilter(e.target.value)}
            className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-100"
          >
            <option value="all">Tous</option>
            {buckets.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Résumés */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3">
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Projets (filtrés)
          </div>
          <div className="text-2xl font-semibold mt-1">{items.length}</div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3">
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Alloc. EUR (filtre)
          </div>
          <div className="text-lg font-semibold mt-1">
            {filteredTotals ? formatCurrency(filteredTotals.totalAllocated) : "—"}
          </div>
          {totals && (
            <div className="text-xs text-zinc-500 mt-1">
              Total global : {formatCurrency(totals.totalAllocated)}
            </div>
          )}
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3">
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Poids (filtre)
          </div>
          <div className="text-lg font-semibold mt-1">
            {filteredTotals ? formatPercent(filteredTotals.totalWeight) : "—"}
          </div>
          {totals && (
            <div className="text-xs text-zinc-500 mt-1">
              Total global : {formatPercent(totals.totalWeight)}
            </div>
          )}
        </div>
      </div>

      {/* États de chargement / erreur */}
      {loading && (
        <div className="text-sm text-zinc-400">Chargement des données…</div>
      )}
      {error && (
        <div className="text-sm text-red-400">
          Erreur : <span className="font-mono">{error}</span>
        </div>
      )}
      {!loading && !error && !items.length && (
        <div className="text-sm text-zinc-400">
          Aucun projet dans ce bucket pour le moment.
        </div>
      )}

      {/* Tableau principal */}
      {!loading && !error && items.length > 0 && (
        <div className="border border-zinc-800 rounded-xl overflow-hidden">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-zinc-900">
              <tr className="text-zinc-300 text-xs uppercase tracking-wide">
                <th className="px-3 py-2 text-left">Token</th>
                <th className="px-3 py-2 text-left">Projet</th>
                <th className="px-3 py-2 text-left">Bucket</th>
                <th className="px-3 py-2 text-right">Score</th>
                <th className="px-3 py-2 text-right">Alloc. EUR</th>
                <th className="px-3 py-2 text-right">Poids</th>
                <th className="px-3 py-2 text-left">Notes</th>
              </tr>
            </thead>
            <tbody className="bg-zinc-950/80 divide-y divide-zinc-800/60">
              {items.map((it) => (
                <tr key={it.id || it.symbol || it.name}>
                  <td className="px-3 py-2 font-mono text-xs text-zinc-200">
                    {it.symbol || "—"}
                  </td>
                  <td className="px-3 py-2 text-zinc-100">
                    {it.name || "—"}
                  </td>
                  <td className="px-3 py-2 text-zinc-300">
                    {it.bucket || "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-zinc-100">
                    {it.score != null ? it.score.toFixed(1) : "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-zinc-100">
                    {formatCurrency(it.allocated_eur)}
                  </td>
                  <td className="px-3 py-2 text-right text-zinc-100">
                    {formatPercent(it.weight)}
                  </td>
                  <td className="px-3 py-2 text-zinc-400 max-w-xs">
                    <span className="line-clamp-2">
                      {it.notes || it.rationale || "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
