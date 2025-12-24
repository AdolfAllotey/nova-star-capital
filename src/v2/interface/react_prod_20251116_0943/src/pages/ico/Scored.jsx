// src/pages/ico/Scored.jsx
import React, { useEffect, useMemo, useState } from "react";
import { fetchJSON } from "../../lib/api";
import Sparkline from "../../components/Sparkline"; // facultatif : si absent, commentez cette ligne

function TextInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full md:w-64 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-700"
    />
  );
}

export default function Scored() {
  const [data, setData] = useState({ items: [], updated_at: null });
  const [q, setQ] = useState("");
  const [minScore, setMinScore] = useState("");
  const [chain, setChain] = useState("");

  const [status, setStatus] = useState("idle"); // idle | loading | ok | error
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setStatus("loading");
        setErrorMsg("");
        // Endpoints standardisés côté API: /ico/scored
        const res = await fetchJSON("/ico/scored", { items: [], updated_at: null });
        if (!alive) return;

        // normalisation douce
        const items = Array.isArray(res?.items) ? res.items : [];
        setData({
          items,
          updated_at: res?.updated_at || null,
        });
        setStatus("ok");
      } catch (err) {
        if (!alive) return;
        setStatus("error");
        setErrorMsg(err?.message || String(err));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    let arr = Array.isArray(data.items) ? data.items : [];

    if (q?.trim()) {
      const needle = q.trim().toLowerCase();
      arr = arr.filter((it) =>
        `${it?.name || ""} ${it?.symbol || ""} ${it?.category || ""}`
          .toLowerCase()
          .includes(needle)
      );
    }
    if (minScore !== "" && !Number.isNaN(Number(minScore))) {
      const m = Number(minScore);
      arr = arr.filter((it) => Number(it?.score ?? -Infinity) >= m);
    }
    if (chain?.trim()) {
      const c = chain.trim().toLowerCase();
      arr = arr.filter(
        (it) =>
          String(it?.chain || it?.network || "")
            .toLowerCase()
            .includes(c)
      );
    }
    return arr;
  }, [data.items, q, minScore, chain]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">ICO — Scored</h1>
        <div className="text-xs text-zinc-400">
          {data.updated_at ? `Maj: ${new Date(data.updated_at).toLocaleString()}` : "—"}
        </div>
      </div>

      {/* Filtres */}
      <div className="flex flex-col md:flex-row md:items-center gap-3">
        <TextInput value={q} onChange={setQ} placeholder="Rechercher (nom, symbol, catégorie)..." />
        <TextInput value={chain} onChange={setChain} placeholder="Filtrer par chain/network..." />
        <input
          type="number"
          step="0.01"
          value={minScore}
          onChange={(e) => setMinScore(e.target.value)}
          placeholder="Score min"
          className="w-full md:w-40 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-700"
        />
      </div>

      {/* Etats */}
      {status === "loading" && (
        <div className="text-sm text-zinc-400">Chargement…</div>
      )}
      {status === "error" && (
        <div className="text-sm text-red-400">
          Erreur: {errorMsg || "échec de chargement"}
        </div>
      )}

      {/* Tableau */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <div className="px-4 py-3 bg-zinc-900/60 text-sm text-zinc-300">
          Projets scorés — {filtered.length} résultat(s)
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900/40 text-zinc-300">
              <tr>
                <th className="px-3 py-2 text-left">Projet</th>
                <th className="px-3 py-2 text-left">Symbole</th>
                <th className="px-3 py-2 text-left">Score</th>
                <th className="px-3 py-2 text-left">Network</th>
                <th className="px-3 py-2 text-left">Catégorie</th>
                <th className="px-3 py-2 text-left">Sparkline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {filtered.map((it, i) => {
                const score = Number(it?.score ?? NaN);
                const network = it?.chain || it?.network || "—";
                const history = Array.isArray(it?.history) ? it.history : null;

                return (
                  <tr key={i} className="hover:bg-zinc-900/30">
                    <td className="px-3 py-2 font-medium">
                      {it?.name || "—"}
                    </td>
                    <td className="px-3 py-2">{it?.symbol || "—"}</td>
                    <td className="px-3 py-2">
                      {Number.isFinite(score) ? score.toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2">{network}</td>
                    <td className="px-3 py-2">{it?.category || "—"}</td>
                    <td className="px-3 py-2 w-40">
                      {history && history.length > 1 ? (
                        <Sparkline data={history} height={36} strokeWidth={1.5} />
                      ) : (
                        <span className="text-zinc-500 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && status === "ok" && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-zinc-500">
                    Aucun résultat
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
