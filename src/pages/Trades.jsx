import React, { useEffect, useState } from "react";
import { getTrades, getTradesHistory } from "../lib/api.js";

function Section({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-3">{title}</h2>
      {children}
    </div>
  );
}

function Table({ rows }) {
  if (!rows?.length) return <div>Aucun trade.</div>;
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left">Time</th>
            <th className="px-3 py-2 text-left">Token</th>
            <th className="px-3 py-2 text-left">Side</th>
            <th className="px-3 py-2 text-right">Qty</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">PnL €</th>
            <th className="px-3 py-2 text-left">Exchange</th>
            <th className="px-3 py-2 text-left">Strategy</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t, i) => (
            <tr key={i}>
              <td className="px-3 py-2 border-b">{t.ts || t.time || t.timestamp || "-"}</td>
              <td className="px-3 py-2 border-b">{t.token || t.symbol}</td>
              <td className="px-3 py-2 border-b">{t.side}</td>
              <td className="px-3 py-2 border-b text-right">{Number(t.qty ?? t.quantity ?? 0).toLocaleString()}</td>
              <td className="px-3 py-2 border-b text-right">{Number(t.price ?? 0).toLocaleString()}</td>
              <td className="px-3 py-2 border-b text-right">{Number(t.pnl_eur ?? t.pnl ?? 0).toLocaleString()}</td>
              <td className="px-3 py-2 border-b">{t.exchange || "-"}</td>
              <td className="px-3 py-2 border-b">{t.strategy || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Trades() {
  const [live, setLive] = useState([]);
  const [hist, setHist] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let abort = new AbortController();
    setLoading(true);
    Promise.all([
      getTrades({ signal: abort.signal }).catch(() => []),
      getTradesHistory({ signal: abort.signal }).catch(() => []),
    ])
      .then(([a, b]) => {
        setLive(Array.isArray(a) ? a : a?.trades ?? []);
        setHist(Array.isArray(b) ? b : b?.trades ?? []);
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    return () => abort.abort();
  }, []);

  if (loading) return <div>Chargement des trades…</div>;
  if (err) return <div className="text-red-600">Erreur: {err}</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Trades</h1>
      <Section title="En cours / récents">
        <Table rows={live} />
      </Section>
      <Section title="Historique">
        <Table rows={hist} />
      </Section>
    </div>
  );
}
