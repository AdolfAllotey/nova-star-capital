import React, { useEffect, useState } from "react";
import { Card } from "../ui/Card.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function Kvp({ k, v }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-zinc-400">{k}</span>
      <span className="font-mono text-zinc-100">{v}</span>
    </div>
  );
}

export default function Strategy() {
  const [data, setData] = useState({ loading: true, error: null, weights: {}, rules: {}, status: {} });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/strategy`, { cache: "no-store" });
        if (!r.ok) throw new Error("endpoint /strategy indisponible");
        const j = await r.json();
        if (!alive) return;
        setData({
          loading: false,
          error: null,
          weights: j?.weights ?? {},
          rules: j?.rules ?? {},
          status: j?.status ?? {},
        });
      } catch (e) {
        // fallback depuis /metrics si tu exposes strategy dedans
        try {
          const r2 = await fetch(`${API_BASE}/metrics`, { cache: "no-store" });
          if (!r2.ok) throw new Error("metrics not ok");
          const m = await r2.json();
          if (!alive) return;
          setData({
            loading: false,
            error: null,
            weights: m?.strategy?.weights ?? {},
            rules: m?.strategy?.rules ?? {},
            status: m?.strategy?.status ?? {},
          });
        } catch (err) {
          if (!alive) return;
          setData({ loading: false, error: "Impossible de charger la stratégie.", weights: {}, rules: {}, status: {} });
        }
      }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="lg:col-span-2">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Pondérations par stratégie</h2>
          {data.loading && <span className="text-xs text-zinc-400">Chargement…</span>}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(data.weights).map(([name, val]) => (
            <div key={name} className="rounded-xl bg-zinc-900/40 p-3 ring-1 ring-zinc-800/60">
              <div className="text-sm text-zinc-400">{name}</div>
              <div className="text-2xl font-semibold">{Math.round(val * 100)}%</div>
            </div>
          ))}
          {Object.keys(data.weights).length === 0 && !data.loading && (
            <div className="text-sm text-zinc-400">Aucune pondération disponible.</div>
          )}
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Règles principales</h2>
        <div className="space-y-1">
          {Object.entries(data.rules).map(([k, v]) => <Kvp key={k} k={k} v={String(v)} />)}
          {Object.keys(data.rules).length === 0 && !data.loading && (
            <div className="text-sm text-zinc-400">Aucune règle exposée.</div>
          )}
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Statut stratégie</h2>
        <div className="space-y-1">
          {Object.entries(data.status).map(([k, v]) => <Kvp key={k} k={k} v={String(v)} />)}
          {Object.keys(data.status).length === 0 && !data.loading && (
            <div className="text-sm text-zinc-400">Aucun statut disponible.</div>
          )}
        </div>
      </Card>
    </div>
  );
}
