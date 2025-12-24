// src/pages/WorstTrades.jsx
import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

export default function WorstTrades(){
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let on=true;
    (async () => {
      try {
        const r = await getJSON("/worst-trades").catch(()=>({items:[]}));
        const list = r.items || r.trades || [];
        on && setItems(list);
        // optionnel: un résumé si exposé
        const s = await getJSON("/worst-trades/summary").catch(()=>null);
        on && setSummary(s);
      } catch(e){ on && setErr(e); }
    })();
    return ()=>{ on=false; };
  }, []);

  return (
    <div>
      <h2 style={{marginTop:0}}>Worst Trades</h2>
      {err && <div style={{color:"#f59e0b"}}>Erreur: {String(err.message||err)}</div>}

      {summary && (typeof summary === "string" ? (
        <div style={{border:"1px solid #26262c",background:"#131316",borderRadius:12,padding:12,marginBottom:12}}>
          {summary}
        </div>
      ) : summary && summary.text ? (
        <div style={{border:"1px solid #26262c",background:"#131316",borderRadius:12,padding:12,marginBottom:12}}>
          {summary.text}
        </div>
      ) : null)}

      {items.length===0 ? (
        <div style={{color:"#9aa0a6"}}>Aucun trade enregistré.</div>
      ) : (
        <table style={{width:"100%", borderCollapse:"collapse"}}>
          <thead>
            <tr style={{textAlign:"left",borderBottom:"1px solid #26262c"}}>
              <th>Token</th><th>Perte (€)</th><th>Date</th><th>Raison</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t, i)=>(
              <tr key={i} style={{borderBottom:"1px solid #1c1c20"}}>
                <td>{t.token||t.symbol||"-"}</td>
                <td>{t.loss_eur ?? t.pnl_eur ?? "-"}</td>
                <td>{t.timestamp||t.date||"-"}</td>
                <td>{t.reason||"-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
