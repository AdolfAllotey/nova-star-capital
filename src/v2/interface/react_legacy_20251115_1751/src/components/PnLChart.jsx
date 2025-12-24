import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

/**
 * Bloc PnL / Equity (versions minimaliste + robuste).
 * Attend un JSON de la forme:
 * {
 *   "date": "2025-10-31",
 *   "pnl": 1234.56,
 *   "equity": 56789.01
 * }
 */
export default function PnLChart() {
  const { data, error } = usePolling(`${BASE_URL}/api/status/pnl`, 20000);

  if (error) {
    return (
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
        <h2 className="text-lg font-semibold mb-2">Performance (PnL cumulé)</h2>
        <div className="text-red-500 text-sm">Erreur chargement PnL : {error.message}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
        <h2 className="text-lg font-semibold mb-2">Performance (PnL cumulé)</h2>
        <div className="opacity-60 text-sm">Chargement…</div>
      </div>
    );
  }

  const pnl = typeof data.pnl === "number" ? data.pnl : null;
  const equity = typeof data.equity === "number" ? data.equity : null;
  const date = data.date || "—";

  const fmt = (n) =>
    typeof n === "number"
      ? n.toLocaleString(undefined, { style: "currency", currency: "EUR", maximumFractionDigits: 2 })
      : "—";

  const pnlColor = pnl == null ? "opacity-70" : pnl >= 0 ? "text-emerald-500" : "text-rose-500";

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Performance (PnL cumulé)</h2>
        <div className="text-xs opacity-70">Dernière MAJ : {date}</div>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
          <div className="text-xs opacity-70">PnL cumulé</div>
          <div className={`text-2xl font-bold ${pnlColor}`}>{fmt(pnl)}</div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
          <div className="text-xs opacity-70">Equity</div>
          <div className="text-2xl font-bold">{fmt(equity)}</div>
        </div>
      </div>

      {/* Placeholder pour un futur chart (Recharts) si tu veux l’historique */}
      {/* <div className="mt-4 text-sm opacity-60">Historique à venir…</div> */}
    </div>
  );
}
