import { useEffect, useState } from "react";
import { fetchJSON } from "../../lib/api";

export default function IcoScreened() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const data = await fetchJSON("/ico/screened", { signal: ctrl.signal });
        setItems(Array.isArray(data?.items) ? data.items : data);
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
      <h1 className="text-2xl font-semibold mb-4">ICO — Screened</h1>
      {loading && <p>Chargement…</p>}
      {err && <p className="text-red-600">Erreur : {err}</p>}
      {!loading && !err && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">Projet</th>
                <th className="py-2 pr-4">Ticker</th>
                <th className="py-2 pr-4">Hard Cap</th>
                <th className="py-2 pr-4">Chain</th>
                <th className="py-2 pr-4">KYC</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 pr-4">{it.name || "-"}</td>
                  <td className="py-2 pr-4">{it.symbol || "-"}</td>
                  <td className="py-2 pr-4">{it.hard_cap_usd ?? "-"}</td>
                  <td className="py-2 pr-4">{it.chain || "-"}</td>
                  <td className="py-2 pr-4">{it.kyc ? "✅" : "—"}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td className="py-4 text-gray-500" colSpan={5}>Aucun élément filtré.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
