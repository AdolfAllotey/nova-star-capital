// src/ui/LiveStatusBar.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { getApiStatus, getMetrics } from "../lib/api";

function Dot({ ok }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        ok ? "bg-emerald-400" : "bg-rose-400"
      }`}
      aria-hidden
    />
  );
}

function Item({ label, value, ok = true, title }) {
  return (
    <div className="flex items-center gap-2" title={title}>
      <Dot ok={ok} />
      <span className="text-xs text-zinc-300">{label}:</span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}

export default function LiveStatusBar() {
  const [ping, setPing] = useState(null);
  const [ok, setOk] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [err, setErr] = useState("");
  const tRef = useRef();

  const updatedAt = useMemo(() => {
    if (!metrics?.files) return null;
    // Montre les 4 jeux clés
    const keys = [
      "market.top_movers",
      "trading.open_positions",
      "risk.worst_trades",
      "ico.scored",
    ];
    return keys
      .map((k) => {
        const f = metrics.files[k];
        return [k, f?.mtime || null, f?.items ?? 0];
      })
      .filter(([, m]) => m)
      .slice(0, 4);
  }, [metrics]);

  useEffect(() => {
    let alive = true;

    const tick = async () => {
      try {
        const t0 = performance.now();
        const status = await getApiStatus();
        const t1 = performance.now();
        if (!alive) return;
        setPing(Math.max(0, Math.round(t1 - t0)));
        setOk(status?.status === "ok");
        const m = await getMetrics();
        if (!alive) return;
        setMetrics(m);
        setErr("");
      } catch (e) {
        if (!alive) return;
        setOk(false);
        setErr(e.message || String(e));
      }
    };

    tick();
    tRef.current = setInterval(tick, 15000);
    return () => {
      alive = false;
      clearInterval(tRef.current);
    };
  }, []);

  return (
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40">
      <div className="rounded-full bg-zinc-900/80 backdrop-blur px-4 py-2 ring-1 ring-white/10 shadow-lg flex items-center gap-4">
        <Item label="API" value={ok ? "OK" : "Down"} ok={!!ok} />
        <Item label="Ping" value={ping !== null ? `${ping}ms` : "…" } ok={ping !== null && ping < 800} />
        {updatedAt?.map(([k, mtime, items]) => (
          <Item
            key={k}
            label={k.replace(".", "·")}
            value={`${items} • ${new Date(mtime).toLocaleTimeString("fr-FR")}`}
            ok={items > 0}
            title={mtime}
          />
        ))}
        {err && <span className="text-xs text-rose-300">ERR: {err}</span>}
      </div>
    </div>
  );
}
