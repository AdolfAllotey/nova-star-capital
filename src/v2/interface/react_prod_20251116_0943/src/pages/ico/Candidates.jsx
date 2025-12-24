// src/pages/ico/Candidates.jsx
import React, { useEffect, useMemo, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoCandidates() {
  const [items, setItems] = useState(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await fetchJSON("/ico/candidates", { items: [] });
      if (alive) setItems(Array.isArray(d?.items) ? d.items : []);
    })();
    return () => { alive = false; };
  }, []);

  const filtered = useMemo(() => {
    if (!items) return null;
    if (!q.trim()) return items;
    const k = q.toLowerCase();
    return items.filter((it) =>
      [it.name, it.symbol, it.chain, it.network, it.category]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(k))
    );
  }, [items, q]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">ICO — Candidates</h1>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filtrer (nom, symbole, chain, catégorie)…"
          className="px-3 py-2 rounded-md bg-zinc-900/60 border border-zinc-800 text-sm outline-none focus:border-zinc-600"
        />
      </div>

      {!filtered ? (
        <div className="text-sm text-zinc-400">Chargement…</div>
      ) : filtered.length === 0 ? (
        <div className="text-sm text-zinc-400">Aucun candidat.</div>
      ) : (
        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900/60 text-zinc-300">
              <tr>
                <th className="px-3 py-2 text-left">Projet</th>
                <th className="px-3 py-2 text-left">Symbole</th>
                <th className="px-3 py-2 text-left">Réseau</th>
                <th className="px-3 py-2 text-left">Catégorie</th>
                <th className="px-3 py-2 text-left">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {filtered.map((it, i) => (
                <tr key={i} className="hover:bg-zinc-900/40">
                  <td className="px-3 py-2">{it.name || "—"}</td>
                  <td className="px-3 py-2">{it.symbol || "—"}</td>
                  <td className="px-3 py-2">
                    {it.chain || it.network || "—"}
                  </td>
                  <td className="px-3 py-2">{it.category || "—"}</td>
                  <td className="px-3 py-2 text-zinc-400 text-xs">
                    {it.source || "—"}
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
