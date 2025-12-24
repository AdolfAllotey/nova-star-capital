// src/pages/Profitability.jsx
import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

export default function Profitability() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try { const r = await getJSON("/profitability/monthly"); on && setItems(r.items || []); }
      catch (e) { on && setErr(e); }
    })();
    return () => { on = false; };
  }, []);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Profitability</h2>
      {err && <div style={{ color: "#f59e0b" }}>Erreur: {String(err.message || err)}</div>}
      {items.length === 0 ? (
        <div style={{ color: "#9aa0a6" }}>Aucune donnée</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #26262c" }}>
              <th>Mois</th><th>PNL (€)</th><th>Coûts (€)</th><th>Net (€)</th>
            </tr>
          </thead>
          <tbody>
            {items.map((x, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                <td>{x.month || "-"}</td>
                <td>{x.pnl_eur ?? "-"}</td>
                <td>{x.costs_eur ?? "-"}</td>
                <td>{x.net_eur ?? (x.pnl_eur != null && x.costs_eur != null ? x.pnl_eur - x.costs_eur : "-")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
