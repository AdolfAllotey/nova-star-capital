import React, { useEffect, useState } from "react";
const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Debug() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/metrics?detail=1`, { cache: "no-store" });
        if (!r.ok) return;
        setMetrics(await r.json());
      } catch {}
    })();
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Debug</h1>
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="text-xs whitespace-pre-wrap">
          {metrics ? JSON.stringify(metrics, null, 2) : "Chargement…"}
        </div>
      </div>
    </div>
  );
}
