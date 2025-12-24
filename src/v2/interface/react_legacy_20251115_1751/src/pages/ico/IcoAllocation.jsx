import { useEffect, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoAllocation() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const data = await fetchJSON("/ico/allocation", { signal: ctrl.signal });
        setItems(Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : []));
      } catch (e) {
        setErr(String(e.message || e));
      } finally {
        setLoading(false);
      }
    })();
    return () => ctrl.abort();
  }, []);

  const total = items.reduce((s, x) => s + (x.amount_usd ?? 0), 0);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-3">ICO — Allocation</h1>
      {loading && <p>Chargement…</p>}
      {err && <p className="text-red-600">Erreur : {err}</p>}

      {!loading && !err && (
        <>
          <p className="mb-3 text-sm text-gray-600">Total alloué : <b>${total.toLocaleString()}</b></p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="py-2 pr-4">Projet</th>
                  <th className="py-2 pr-4">Ticker</th>
                  <th className="py-2 pr-4">Montant (USD)</th>
                  <th className="py-2 pr-4">% du total</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it, i) => {
                  const pct = total > 0 ? ((it.amount_usd ?? 0) / total) * 100 : 0;
                  return (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2 pr-4">{it.name || "-"}</td>
                      <td className="py-2 pr-4">{it.symbol || "-"}</td>
                      <td className="py-2 pr-4">${(it.amount_usd ?? 0).toLocaleString()}</td>
                      <td className="py-2 pr-4">{pct.toFixed(1)}%</td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr><td className="py-4 text-gray-500" colSpan={4}>Aucune allocation.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
