import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

export default function WorstTrades() {
  const { data: list,  error: e1 } = usePolling(`${BASE_URL}/api/risk/worst`, 30000);
  const { data: summ,  error: e2 } = usePolling(`${BASE_URL}/api/risk/worst/summary`, 60000);

  const items = Array.isArray(list) ? list.slice(0, 5) : [];

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Pires trades (Top 5 pertes)</h2>
        {(e1 || e2) && <div className="text-xs text-rose-500">Erreur</div>}
      </div>

      {items.length === 0 ? (
        <div className="text-sm opacity-60">Aucune perte analysée.</div>
      ) : (
        <div className="grid gap-2">
          {items.map((t, i) => {
            const loss = typeof t?.loss === "number" ? t.loss : t?.pnl;
            return (
              <div key={i} className="grid md:grid-cols-5 gap-2">
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                  <div className="text-[11px] opacity-70">Token</div>
                  <div className="text-sm font-medium">{t.token || t.symbol || "—"}</div>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                  <div className="text-[11px] opacity-70">Date</div>
                  <div className="text-sm font-medium">{t.date || t.ts || "—"}</div>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                  <div className="text-[11px] opacity-70">Perte</div>
                  <div className="text-sm font-semibold text-rose-500">
                    {loss == null ? "—" : `${Number(loss).toLocaleString()} €`}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                  <div className="text-[11px] opacity-70">Raison</div>
                  <div className="text-sm font-medium">{t.reason || t.exit_reason || "—"}</div>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
                  <div className="text-[11px] opacity-70">Exchange</div>
                  <div className="text-sm font-medium">{t.exchange || "—"}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-800 p-3">
        <div className="text-sm font-semibold opacity-80 mb-1">Résumé LLM</div>
        <div className="text-sm opacity-80 whitespace-pre-line">
          {typeof summ === "string"
            ? summ
            : summ?.summary || summ?.text || "—"}
        </div>
      </div>
    </div>
  );
}
