// src/pages/IcoDashboard.jsx
// Vue synthétique des modules ICO (candidats, screened, scored, allocation)

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

function Metric({ label, value }) {
  return (
    <div className="flex flex-col bg-zinc-800/40 rounded-lg p-3 border border-zinc-700/40">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-lg font-semibold text-zinc-100">
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function IcoDashboard() {
  const [cand, setCand] = useState([]);
  const [screened, setScreened] = useState([]);
  const [scored, setScored] = useState([]);
  const [alloc, setAlloc] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    try {
      setLoading(true);

      const urls = [
        buildUrl("/ico/candidates"),
        buildUrl("/ico/screened"),
        buildUrl("/ico/scored"),
        buildUrl("/ico/allocation"),
      ];

      const [c1, c2, c3, c4] = await Promise.all(
        urls.map((u) =>
          fetch(u)
            .then((r) => r.json())
            .catch(() => ({ items: [] }))
        )
      );

      setCand(Array.isArray(c1.items) ? c1.items : []);
      setScreened(Array.isArray(c2.items) ? c2.items : []);
      setScored(Array.isArray(c3.items) ? c3.items : []);
      setAlloc(Array.isArray(c4.items) ? c4.items : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  if (loading) {
    return (
      <div className="text-zinc-400 text-sm">Chargement des données ICO…</div>
    );
  }

  return (
    <div className="space-y-8">
      <Section title="Synthèse des modules ICO">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Metric label="Candidats" value={cand.length} />
          <Metric label="Screened" value={screened.length} />
          <Metric label="Scorés" value={scored.length} />
          <Metric label="Allocations" value={alloc.length} />
        </div>
      </Section>

      <Section title="Derniers projets scorés">
        {scored.length === 0 ? (
          <div className="text-zinc-500 text-sm">Aucun score disponible.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 text-left">Nom</th>
                <th className="py-2 text-left">Symbole</th>
                <th className="py-2 text-right">Score</th>
              </tr>
            </thead>

            <tbody>
              {scored.slice(0, 5).map((p, idx) => (
                <tr
                  key={idx}
                  className="border-b border-zinc-800/60 hover:bg-zinc-800/40"
                >
                  <td className="py-2 text-zinc-100">{p.name || "N/A"}</td>
                  <td className="py-2 text-zinc-400">
                    {p.symbol ? p.symbol.toUpperCase() : "—"}
                  </td>
                  <td className="py-2 text-right font-semibold text-zinc-100">
                    {p.score ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Derniers projets filtrés">
        {screened.length === 0 ? (
          <div className="text-zinc-500 text-sm">
            Aucun projet filtré pour le moment.
          </div>
        ) : (
          <ul className="space-y-2">
            {screened.slice(0, 5).map((p, idx) => (
              <li key={idx} className="text-zinc-300">
                • {p.name || "N/A"}{" "}
                <span className="text-zinc-500">
                  ({p.symbol ? p.symbol.toUpperCase() : "—"})
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
