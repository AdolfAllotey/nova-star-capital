import React, { useEffect, useState } from "react";
import { getOpenPositions } from "../lib/api.js";

function Cell({ children }) {
  return <td className="px-3 py-2 border-b">{children}</td>;
}

export default function Positions() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let abort = new AbortController();
    setLoading(true);
    getOpenPositions({ signal: abort.signal })
      .then((data) => setRows(Array.isArray(data) ? data : data?.positions ?? []))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    return () => abort.abort();
  }, []);

  if (loading) return <div>Chargement des positions…</div>;
  if (err) return <div className="text-red-600">Erreur: {err}</div>;
  if (!rows.length) return <div>Aucune position ouverte.</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Positions ouvertes</h1>
      <div className="overflow-x-auto rounded-xl border">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Token</th>
              <th className="px-3 py-2 text-left">Exchange</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2 text-right">Entry</th>
              <th className="px-3 py-2 text-right">PnL €</th>
              <th className="px-3 py-2 text-left">Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <tr key={i}>
                <Cell>{p.token || p.symbol}</Cell>
                <Cell>{p.exchange || "-"}</Cell>
                <Cell>{Number(p.qty ?? p.quantity ?? 0).toLocaleString()}</Cell>
                <Cell>{Number(p.entry_price ?? p.entry ?? 0).toLocaleString()}</Cell>
                <Cell>{Number(p.pnl_eur ?? p.pnl ?? 0).toLocaleString()}</Cell>
                <Cell>{p.exit_reason || p.reason || "-"}</Cell>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
