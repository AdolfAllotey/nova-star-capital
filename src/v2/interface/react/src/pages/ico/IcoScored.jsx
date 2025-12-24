import { useEffect, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoScored() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const data = await fetchJSON("/ico/scored", { signal: ctrl.signal });
        // Supporte deux formats : {items:[]} ou [] direct
        const list = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : []);
        // tri desc score si présent
        list.sort((a,b) => (b.score ?? 0) - (a.score ?? 0));
        setItems(list);
      } catch (e) {
        setErr(String(e.message || e));
      } finally {
        setLoading(false);
      }
    })();
    return () => ctrl.abort();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">ICO — Scored</h1>
      {loading && <p>Chargement…</p>}
      {err && <p className="text-red-600">Erreur : {err}</p>}
      {!loading && !err && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">Projet</th>
                <th className="py-2 pr-4">Ticker</th>
                <th className="py-2 pr-4">Score</th>
                <th className="py-2 pr-4">Risque</th>
                <th className="py-2 pr-4">Lien</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 pr-4">{it.name || "-"}</td>
                  <td className="py-2 pr-4">{it.symbol || "-"}</td>
                  <td className="py-2 pr-4 font-medium">{(it.score ?? 0).toFixed?.(2) ?? it.score}</td>
                  <td className="py-2 pr-4">{it.risk ?? "-"}</td>
                  <td className="py-2 pr-4">
                    {it.website ? (
                      <a href={it.website} className="text-blue-600 underline" target="_blank" rel="noreferrer">
                        website
                      </a>
                    ) : "-"}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td className="py-4 text-gray-500" colSpan={5}>Aucun projet scoré.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
