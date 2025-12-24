// src/pages/ICOScored.jsx
// Page des ICO scorées provenant de l'API preprod

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

export default function ICOScored() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchData() {
    try {
      setLoading(true);
      const url = buildUrl("/ico/scored");
      const res = await fetch(url);
      const data = await res.json();

      if (Array.isArray(data.items)) {
        setItems(data.items);
      } else if (Array.isArray(data)) {
        setItems(data);
      } else {
        setItems([]);
      }
    } catch (e) {
      console.error("ICOScored → fetch error:", e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="text-zinc-400 text-sm">Chargement des évaluations…</div>
    );
  }

  return (
    <div className="space-y-8">
      <Section title="ICO – Projets scorés">
        {items.length === 0 ? (
          <div className="text-zinc-500 text-sm">
            Aucun projet scoré pour le moment.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 text-left">Nom</th>
                <th className="py-2 text-left">Symbole</th>
                <th className="py-2 text-right">Score</th>
                <th className="py-2 text-left">Catégorie</th>
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
                    {p.symbol ? p.symbol.toUpperCase() : "–"}
                  </td>

                  <td className="py-2 text-right text-zinc-100 font-semibold">
                    {p.score ?? "—"}
                  </td>

                  <td className="py-2 text-zinc-400">{p.category || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}
