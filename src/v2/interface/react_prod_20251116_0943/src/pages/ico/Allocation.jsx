// src/pages/ico/Allocation.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoAllocation() {
  const [items, setItems] = useState(null);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await fetchJSON("/ico/allocation", { items: [], updated_at: null });
      if (!alive) return;
      setItems(Array.isArray(d?.items) ? d.items : []);
      setMeta({ updated_at: d?.updated_at || null });
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">ICO — Allocation</h1>

      {meta?.updated_at && (
        <div className="text-xs text-zinc-500">
          Maj: {new Date(meta.updated_at).toLocaleString()}
        </div>
      )}

      {!items ? (
        <div className="text-sm text-zinc-400">Chargement…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-zinc-400">Aucune allocation calculée.</div>
      ) : (
        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900/60 text-zinc-300">
              <tr>
                <th className="px-3 py-2 text-left">Projet</th>
                <th className="px-3 py-2 text-left">Poids (%)</th>
                <th className="px-3 py-2 text-left">Montant (si dispo)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {items.map((it, i) => (
                <tr key={i} className="hover:bg-zinc-900/40">
                  <td className="px-3 py-2">{it.name || it.symbol || "?"}</td>
                  <td className="px-3 py-2">
                    {it.weight_pct != null ? `${Number(it.weight_pct).toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {it.amount != null ? it.amount : "—"}
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
