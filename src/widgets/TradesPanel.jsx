import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api.js";

export default function TradesPanel() {
  const [data, setData] = useState({ simulated: [], open_positions: [] });

  useEffect(() => {
    getJSON("/api/trades").then(d => setData(d || { simulated: [], open_positions: [] }));
  }, []);

  const S = data.simulated || [];
  const O = data.open_positions || [];

  return (
    <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap: 12}}>
      <div>
        <div style={{fontWeight:600, marginBottom:6}}>Simulated</div>
        {S.length === 0 ? <div>—</div> : (
          <ul style={{margin:0, paddingLeft:18}}>
            {S.map((t, i) => (
              <li key={i}>{t.token} {t.side} @ {t.price} — {t.exchange} — {t.status} — pnl {t.pnl}</li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <div style={{fontWeight:600, marginBottom:6}}>Open positions</div>
        {O.length === 0 ? <div>—</div> : (
          <ul style={{margin:0, paddingLeft:18}}>
            {O.map((p, i) => (
              <li key={i}>{p.token} {p.side} avg {p.avg_price} — {p.exchange} — pnl {p.pnl}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
