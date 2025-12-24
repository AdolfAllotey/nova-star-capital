import React, { useEffect, useState } from "react";
import { Card } from "../ui/Card.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function Row({ k, v }) {
  return (
    <div className="grid grid-cols-[240px,1fr] gap-4 py-1 text-sm">
      <div className="text-zinc-400">{k}</div>
      <div className="font-mono break-all">{typeof v === "object" ? JSON.stringify(v) : String(v)}</div>
    </div>
  );
}

export default function Metrics() {
  const [m, setM] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/metrics`, { cache: "no-store" });
        if (!r.ok) throw new Error("metrics not ok");
        const j = await r.json();
        if (!alive) return;
        setM({ loading: false, error: null, data: j });
      } catch (e) {
        if (!alive) return;
        setM({ loading: false, error: "Impossible de charger /metrics.", data: null });
      }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Fichiers</h2>
          {m.loading && <span className="text-xs text-zinc-400">Chargement…</span>}
        </div>
        {m.data?.files ? (
          <div className="divide-y divide-zinc-800/60">
            {Object.entries(m.data.files).map(([k, meta]) => (
              <div key={k} className="py-2">
                <div className="font-medium">{k}</div>
                <div className="text-xs text-zinc-400">{meta?.path}</div>
                <div className="grid grid-cols-3 gap-3 mt-2 text-sm">
                  <div className="rounded-xl bg-zinc-900/40 p-3 ring-1 ring-zinc-800/60">
                    <div className="text-zinc-400">Existe</div>
                    <div className="font-mono">{String(meta?.exists)}</div>
                  </div>
                  <div className="rounded-xl bg-zinc-900/40 p-3 ring-1 ring-zinc-800/60">
                    <div className="text-zinc-400">Taille</div>
                    <div className="font-mono">{meta?.size_bytes ?? 0} o</div>
                  </div>
                  <div className="rounded-xl bg-zinc-900/40 p-3 ring-1 ring-zinc-800/60">
                    <div className="text-zinc-400">Items</div>
                    <div className="font-mono">{meta?.items ?? "n/a"}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          !m.loading && <div className="text-sm text-zinc-400">Aucune métrique de fichiers.</div>
        )}
        {m.error && <div className="mt-3 text-rose-300 text-sm">{m.error}</div>}
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-4">Serveur & Statut</h2>
        <div className="space-y-1">
          {m.data?.server
            ? Object.entries(m.data.server).map(([k, v]) => <Row key={k} k={k} v={v} />)
            : <div className="text-sm text-zinc-400">Aucune info serveur exposée.</div>}
        </div>
        <div className="mt-4">
          <h3 className="text-base font-semibold mb-2">Divers</h3>
          <div className="space-y-1">
            {m.data
              ? Object.entries(m.data).filter(([k]) => !["files","server"].includes(k))
                  .map(([k, v]) => <Row key={k} k={k} v={v} />)
              : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
