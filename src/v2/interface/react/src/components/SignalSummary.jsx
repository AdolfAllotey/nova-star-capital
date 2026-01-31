// src/components/SignalSummary.jsx
import React, { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

const _Box = ({ title, children }) => (
  <div style={{
    border:"1px solid #26262c", background:"#111114", borderRadius:12, padding:16,
    display:"flex", flexDirection:"column", gap:8, minWidth:220
  }}>
    <div style={{fontWeight:600, color:"#c9ccd1"}}>{title}</div>
    <div>{children}</div>
  </div>
);

export default function SignalSummary(){
  const [data, setData] = useState(null);
  const [err, setErr]   = useState(null);

  useEffect(() => {
    let on=true;
    (async () => {
      try {
        // Essaie endpoints “standards”, tombe en grâce s’ils n’existent pas
        const worst   = await getJSON("/worst-trades").catch(()=>({items:[]}));
        const regime  = await getJSON("/market/regime").catch(()=>({mode:"neutral",score:0}));
        const top     = await getJSON("/market/top-movers").catch(()=>({items:[]}));
        const senti   = await getJSON("/sentiment/summary").catch(()=>({score:0,updated_at:null}));
        on && setData({ worst, regime, top, senti });
      } catch(e){ on && setErr(e); }
    })();
    return ()=>{ on=false; };
  }, []);

  if(err) return <div style={{color:"#f59e0b"}}>Erreur: {String(err.message||err)}</div>;
  if(!data) return <div style={{color:"#9aa0a6"}}>Chargement…</div>;

  const worstCount = (data.worst.items||data.worst.trades||[]).length;
  const movers10   = (data.top.items||[]).slice(0,10);
  const regimeText = (data.regime.mode||"neutral").toUpperCase();
  const regimeScore= Number(data.regime.score||0).toFixed(2);

  return (
    <div style={{display:"flex", gap:16, flexWrap:"wrap"}}>
      <_Box title="Market regime">
        <div>Mode: <b>{regimeText}</b></div>
        <div>Score: {regimeScore}</div>
        <div style={{fontSize:12, color:"#9aa0a6"}}>{data.regime.updated_at||""}</div>
      </_Box>

      <_Box title="Sentiment (global)">
        <div>Score: <b>{Number(data.senti.score||0).toFixed(2)}</b></div>
        <div style={{fontSize:12, color:"#9aa0a6"}}>{data.senti.updated_at||""}</div>
      </_Box>

      <_Box title="Worst trades (compteur)">
        <div>{worstCount} entrées</div>
      </_Box>

      <_Box title="Top Movers (aperçu)">
        {movers10.length===0 ? <div style={{color:"#9aa0a6"}}>Aucun</div> : (
          <ul style={{margin:0, paddingLeft:18}}>
            {movers10.map((x)=>(
              <li key={x.id||x.symbol}>
                {x.symbol||x.id} — {x.price_change_24h!=null ? `${x.price_change_24h.toFixed(2)}%` : "-"}
              </li>
            ))}
          </ul>
        )}
      </_Box>
    </div>
  );
}
