import { useEffect, useState } from "react";
import { getTrades } from "../lib/api";

export default function TradesWidget() {
  const [data, setData] = useState({ simulated: [], open_positions: [], count_simulated: 0, count_open: 0 });

  useEffect(() => {
    getTrades().then(setData).catch(() => setData({ simulated: [], open_positions: [], count_simulated: 0, count_open: 0 }));
  }, []);

  return (
    <div className="rounded-2xl border border-slate-200 p-4">
      <div className="text-sm font-semibold mb-2">Trades</div>
      <div className="flex gap-4 text-sm mb-3">
        <span className="opacity-70">Simulés:</span><span className="font-semibold">{data.count_simulated}</span>
        <span className="opacity-70">Ouverts:</span><span className="font-semibold">{data.count_open}</span>
      </div>
      <div className="text-xs opacity-70">Aperçu (max 5)</div>
      <ul className="space-y-1 mt-1 text-sm">
        {data.simulated.slice(0, 5).map((t, i) => (
          <li key={i} className="flex gap-2">
            <span className="font-mono">{t.token}</span>
            <span className="uppercase opacity-70">{t.side}</span>
            <span className="opacity-70">@{t.exchange}</span>
            {"pnl" in t && <span className={t.pnl >= 0 ? "text-emerald-600" : "text-rose-600"}>{t.pnl}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
