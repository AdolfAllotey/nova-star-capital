// src/components/LiveMarketChart.jsx
import React, { useEffect, useState, useRef } from "react";
import { _LineChart, _Line, _XAxis, _YAxis, _Tooltip, _ResponsiveContainer } from "recharts";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function LiveMarketChart() {
  const [series, setSeries] = useState([]);
  const timer = useRef(null);

  async function tick() {
    try {
      const r = await fetch(`${API}/market/top-movers`);
      const j = await r.json();
      const items = Array.isArray(j?.items) ? j.items : [];
      // petit “index NSC” = moyenne des % changes (si ton JSON a "change_24h" par ex.)
      const changes = items
        .map((x) => (typeof x.change_24h === "number" ? x.change_24h : 0))
        .filter((n) => Number.isFinite(n));
      const avg = changes.length
        ? changes.reduce((a, b) => a + b, 0) / changes.length
        : 0;

      const point = { t: new Date().toLocaleTimeString(), idx: Number(avg.toFixed(2)) };
      setSeries((prev) => [...prev.slice(-59), point]); // garde ~10 min à 10 s
    } catch {
      // silencieux : le graphe ne plante pas si JSON vide
    }
  }

  useEffect(() => {
    const t0 = setTimeout(tick, 0);
    timer.current = setInterval(tick, 10_000);
    return () => {
      clearTimeout(t0);
      clearInterval(timer.current);
    };
  }, []);

  return (
    <div style={{ background: "#111114", border: "1px solid #24242a", borderRadius: 12, padding: 12 }}>
      <div style={{ marginBottom: 8, fontWeight: 600 }}>NSC Live Market Index</div>
      <_ResponsiveContainer width="100%" height={240}>
        <_LineChart data={series}>
          <_XAxis dataKey="t" hide />
          <_YAxis domain={["auto", "auto"]} tickFormatter={(v) => `${v}%`} />
          <_Tooltip formatter={(v) => [`${v}%`, "Index"]} />
          <_Line type="monotone" dataKey="idx" dot={false} strokeWidth={2} />
        </_LineChart>
      </_ResponsiveContainer>
    </div>
  );
}
