// src/components/MarketRegimeBar.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../lib/api";

const COLORS = {
  bull: "bg-emerald-500",
  bear: "bg-rose-500",
  neutral: "bg-zinc-500",
};

export default function MarketRegimeBar() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await fetchJSON("/market/regime", { mode: "neutral", score: 0, updated_at: null, source: "fallback" });
      if (alive) setData(d);
    })();
    return () => { alive = false; };
  }, []);

  const mode = data?.mode || "neutral";
  const score = typeof data?.score === "number" ? data.score : 0;
  const barClass = COLORS[mode] || COLORS.neutral;

  return (
    <div className="rounded-md border border-zinc-800 p-3 bg-zinc-900/40">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${barClass}`} />
          <span className="text-zinc-200 capitalize">{mode}</span>
          <span className="text-zinc-500">• score {score.toFixed(2)}</span>
        </div>
        <span className="text-xs text-zinc-500">
          {data?.updated_at ? new Date(data.updated_at).toLocaleString() : "—"}
        </span>
      </div>
      <div className="mt-2 h-2 w-full rounded bg-zinc-800 overflow-hidden">
        <div
          className={`h-full ${barClass}`}
          style={{ width: `${Math.max(0, Math.min(100, Math.round((score + 1) * 50)))}%` }}
        />
      </div>
    </div>
  );
}
