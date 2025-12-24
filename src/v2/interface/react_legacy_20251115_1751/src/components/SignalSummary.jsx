import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

export default function SignalSummary() {
  const { data, error } = usePolling(`${BASE_URL}/api/signals/sentiment`, 20000);

  const sentiment = typeof data?.sentiment === "number" ? data.sentiment : null;
  const momentum  = typeof data?.momentum  === "number" ? data.momentum  : null;
  const updated   = data?.date || data?.updated_at || "—";

  const fmtPct = (n) =>
    typeof n === "number" ? `${(n * 100).toFixed(0)}%` : "—";

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="text-sm font-semibold opacity-80 mb-2">Sentiment & Momentum</div>

      {error && <div className="text-xs text-rose-500 mb-2">Erreur chargement</div>}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
          <div className="text-xs opacity-70">Sentiment</div>
          <div className="text-xl font-bold">
            {fmtPct(sentiment)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
          <div className="text-xs opacity-70">Momentum</div>
          <div className="text-xl font-bold">
            {fmtPct(momentum)}
          </div>
        </div>
      </div>

      <div className="mt-3 text-xs opacity-60">MAJ : {updated}</div>
    </div>
  );
}
