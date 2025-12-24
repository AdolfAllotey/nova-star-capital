import React from "react";
import usePolling from "../hooks/usePolling";
import { BASE_URL } from "../lib/api";

function Cell({ label, children }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 p-2">
      <div className="text-[11px] opacity-70">{label}</div>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}

/**
 * Affiche la liste des trades (simulation + positions ouvertes).
 * Attend un JSON de /api/trades de la forme:
 * - soit { "trades": [ ... ] }
 * - soit directement [ ... ]
 */
export default function LiveSimulation() {
  const { data, error } = usePolling(`${BASE_URL}/api/trades`, 15000);
  const trades = Array.isArray(data?.trades) ? data.trades : Array.isArray(data) ? data : [];

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Trades — simulation & positions ouvertes</h2>
        {error && <div className="text-xs text-rose-500">Erreur</div>}
      </div>

      {trades.length === 0 ? (
        <div className="text-sm opacity-60">Aucun trade à afficher.</div>
      ) : (
        <div className="grid gap-2">
          {trades.slice(0, 12).map((t, i) => {
            const pnl = typeof t?.pnl === "number" ? t.pnl : null;
            const pnlCls = pnl == null ? "opacity-70" : pnl >= 0 ? "text-emerald-500" : "text-rose-500";

            return (
              <div key={i} className="grid md:grid-cols-6 gap-2">
                <Cell label="Token">{t.token || t.symbol || "—"}</Cell>
                <Cell label="Side">{t.side || t.action || "—"}</Cell>
                <Cell label="Prix">{t.price != null ? Number(t.price).toLocaleString() : "—"}</Cell>
                <Cell label="Exchange">{t.exchange || "—"}</Cell>
                <Cell label="Status">{t.status || (t.is_open ? "OPEN" : "CLOSED")}</Cell>
                <Cell label="PnL">
                  <span className={`font-semibold ${pnlCls}`}>
                    {pnl == null ? "—" : pnl.toLocaleString(undefined, { maximumFractionDigits: 2 }) + " €"}
                  </span>
                </Cell>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
