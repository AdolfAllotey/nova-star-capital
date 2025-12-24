import { useEffect, useMemo, useState } from "react";
import { getPnL } from "../lib/api";

export default function PnLCard() {
  const [pnl, setPnl] = useState(null);

  useEffect(() => {
    getPnL().then(setPnl).catch(() => setPnl({ raw: {} }));
  }, []);

  const rows = useMemo(() => {
    const raw = pnl?.raw || {};
    return Object.keys(raw)
      .filter(k => /^\d{4}-\d{2}$/.test(k))
      .sort()
      .map(k => ({ month: k, ...raw[k] }));
  }, [pnl]);

  return (
    <div className="rounded-2xl border border-slate-200 p-4">
      <div className="flex justify-between items-baseline mb-3">
        <div className="text-sm font-semibold">PnL mensuel</div>
        <div className="text-xs opacity-60">maj {new Date(pnl?.last_update || Date.now()).toLocaleString()}</div>
      </div>
      <div className="space-y-2">
        {rows.length === 0 && <div className="text-sm opacity-60">Aucune donnée</div>}
        {rows.map(r => (
          <div key={r.month} className="flex items-center justify-between text-sm">
            <span className="font-mono">{r.month}</span>
            <span className={Number(r.pnl) >= 0 ? "text-emerald-600" : "text-rose-600"}>
              {Number(r.pnl).toFixed(2)}
            </span>
            <span className="opacity-60">{r.trade_count} trades</span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-slate-200 flex justify-between text-sm">
        <span className="opacity-70">PnL cum.</span>
        <span className={Number(pnl?.pnl_cum) >= 0 ? "text-emerald-600" : "text-rose-600"}>
          {Number(pnl?.pnl_cum || 0).toFixed(2)}
        </span>
      </div>
    </div>
  );
}
