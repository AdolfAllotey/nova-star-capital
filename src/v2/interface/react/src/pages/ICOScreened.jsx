// src/pages/ICOScreened.jsx
// Liste des ICO pré-sélectionnées par l’engine (screening)

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

export default function ICOScreened() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      setLoading(true);

      const res = await fetch(buildUrl("/ico/screened"))
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
      <div className="text-zinc-400 text-sm">Chargement des ICO filtrées…</div>
    );
  }

  return (
    <div className="space-y-8">
      <Section title="ICO filtrées (screening)">
        {items.length === 0 ? (
          <div className="text-zinc-500 text-sm">
            Aucun projet filtré pour le moment.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 text-left">Projet</th>
                <th className="py-2 text-left">Symbole</th>
                <th className="py-2 text-left">Catégorie</th>
                <th className="py-2 text-right">Note Screening</th>
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

                  <td className="py-2 text-zinc-300">
                    {p.category ?? "—"}
                  </td>

                  <td className="py-2 text-right text-zinc-100 font-semibold">
                    {p.screen_score != null
                      ? p.screen_score.toFixed(2)
                      : "—"}
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
