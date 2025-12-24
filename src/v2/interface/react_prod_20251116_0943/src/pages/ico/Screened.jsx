// src/pages/ico/Screened.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoScreened() {
  const [items, setItems] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await fetchJSON("/ico/screened", { items: [] });
      if (alive) setItems(Array.isArray(d?.items) ? d.items : []);
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">ICO — Screened</h1>

      {!items ? (
        <div className="text-sm text-zinc-400">Chargement…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-zinc-400">Aucun élément.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((it, i) => (
            <li key={i} className="rounded-md border border-zinc-800 p-3 bg-zinc-900/40">
              <div className="text-sm text-zinc-200">
                {it.name || it.symbol || "Projet ?"}
              </div>
              <div className="text-xs text-zinc-500">
                {(it.chain || it.network) ? `Chain: ${it.chain || it.network}` : "—"}{" "}
                {(it.category) ? `• Cat: ${it.category}` : ""}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
