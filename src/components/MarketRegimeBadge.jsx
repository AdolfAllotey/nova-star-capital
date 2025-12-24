import React from "react";
import { useMarketRegime } from "../hooks/useNscData";

export default function MarketRegimeBadge() {
  const { data, err, loading, refresh } = useMarketRegime();

  if (err) {
    return (
      <span className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-1 text-red-700">
        Régime: erreur
        <button onClick={refresh} className="text-xs underline">réessayer</button>
      </span>
    );
  }

  if (loading) {
    return <span className="inline-block h-6 w-28 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />;
  }

  const regime = (data?.regime || "—").toLowerCase();
  const conf   = data?.confidence;
  const tone =
    regime === "bull" ? "bg-green-600" :
    regime === "bear" ? "bg-red-600" :
    regime === "neutre" ? "bg-gray-600" : "bg-slate-500";

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-white ${tone}`}>
      Régime: {regime} {conf != null ? `(${Math.round(conf * 100)}%)` : ""}
    </span>
  );
}
