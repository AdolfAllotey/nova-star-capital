// src/pages/TopMovers.jsx
import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

export default function TopMovers() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let on = true;
    (async () => {
      try { const r = await getJSON("/market/top-movers"); on && setItems(r.items || []); }
      catch (e) { on && setErr(e); }
    })();
    return () => { on = false; };
  }, []);

  if (err) return <div style={{ color: "#f59e0b" }}>Erreur: {String(err.message || err)}</div>;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Top Movers</h2>
      {items.length === 0 ? (
        <div style={{ color: "#9aa0a6" }}>Aucun item</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #26262c" }}>
              <th>Symbol</th><th>Price</th><th>Δ 24h</th><th>Volume</th>
            </tr>
          </thead>
          <tbody>
            {items.map((x) => (
              <tr key={x.id || x.symbol} style={{ borderBottom: "1px solid #1c1c20" }}>
                <td>{x.symbol || x.id}</td>
                <td>{x.current_price != null ? x.current_price : "-"}</td>
                <td>{x.price_change_24h != null ? `${x.price_change_24h.toFixed(2)}%` : "-"}</td>
                <td>{x.total_volume != null ? x.total_volume : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
