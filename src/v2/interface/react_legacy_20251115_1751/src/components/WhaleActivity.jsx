import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

export default function WhaleActivity() {
  const { data, error } = usePolling(`${BASE_URL}/api/monitor/whales`, 20000);

  const items = Array.isArray(data) ? data.slice(0, 6) : [];

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="text-sm font-semibold opacity-80 mb-2">Whales — dernières détections</div>
      {error && <div className="text-xs text-rose-500 mb-2">Erreur chargement</div>}

      {items.length === 0 ? (
        <div className="text-sm opacity-60">Aucune détection récente.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((w, idx) => (
            <li key={idx} className="text-sm rounded-lg border border-slate-200 dark:border-slate-800 p-2">
              <div className="flex justify-between">
                <span className="opacity-80">{w.token || w.asset || "?"}</span>
                <span className="opacity-60">{w.exchange || w.chain || ""}</span>
              </div>
              <div className="text-xs opacity-70">
                {w.type || w.action || "move"} • {w.amount ? Number(w.amount).toLocaleString() : "—"}
                {w.ts || w.time ? ` • ${w.ts || w.time}` : ""}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
