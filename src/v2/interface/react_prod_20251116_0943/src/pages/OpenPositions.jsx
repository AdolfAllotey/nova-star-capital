// src/pages/OpenPositions.jsx
import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

export default function OpenPositions() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try { const r = await getJSON("/open-positions"); on && setItems(r.positions || r.items || []); }
      catch (e) { on && setErr(e); }
    })();
    return () => { on = false; };
  }, []);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Open Positions</h2>
      {err && <div style={{ color: "#f59e0b" }}>Erreur: {String(err.message || err)}</div>}
      {items.length === 0 ? (
        <div style={{ color: "#9aa0a6" }}>Aucune position ouverte</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #26262c" }}>
              <th>Token</th><th>Qty</th><th>Entry</th><th>Unrealized PnL</th><th>Exchange</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                <td>{p.token || p.symbol || "-"}</td>
                <td>{p.qty ?? "-"}</td>
                <td>{p.entry_price ?? "-"}</td>
                <td>{p.unrealized_pnl ?? "-"}</td>
                <td>{p.exchange ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
