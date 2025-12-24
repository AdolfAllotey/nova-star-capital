// src/pages/ICOAllocation.jsx
// Vue des allocations ICO calculées par l'engine (somme par projet)

import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
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

export default function ICOAllocation() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      setLoading(true);

      const res = await fetch(buildUrl("/ico/allocation"))
        .then((r) => r.json())
        .catch(() => ({ items: [] }));

      setItems(Array.isArray(res.items) ? res.items : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="text-zinc-400 text-sm">Chargement des allocations ICO…</div>
    );
  }

  return (
    <div className="space-y-8">
      <Section title="Allocations ICO">
        {items.length === 0 ? (
          <div className="text-zinc-500 text-sm">
            Aucune allocation disponible pour le moment.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 text-left">Projet</th>
                <th className="py-2 text-left">Symbole</th>
                <th className="py-2 text-right">Montant (€)</th>
                <th className="py-2 text-right">Poids (%)</th>
              </tr>
            </thead>

            <tbody>
              {items.map((p, idx) => (
                <tr
                  key={idx}
                  className="border-b border-zinc-800/60 hover:bg-zinc-800/40"
                >
                  <td className="py-2 text-zinc-100">{p.name || "N/A"}</td>
                  <td className="py-2 text-zinc-400">
                    {p.symbol ? p.symbol.toUpperCase() : "—"}
                  </td>

                  <td className="py-2 text-right text-zinc-100 font-semibold">
                    {p.amount_eur != null ? p.amount_eur.toFixed(2) : "—"}
                  </td>

                  <td className="py-2 text-right text-zinc-300">
                    {p.weight != null ? `${(p.weight * 100).toFixed(1)} %` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}
