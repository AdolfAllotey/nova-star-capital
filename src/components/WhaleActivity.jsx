import React from "react";
import { useWhales } from "../hooks/useNscData";

const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

export default function WhaleActivity() {
  const { data, err, loading, refresh } = useWhales();

  if (err) return <CardError title="Whales / Wallets" error={err} onRetry={refresh} />;

  return (
    <Card title="Whales / Wallets">
      {loading ? (
        <div className="animate-pulse h-16 bg-slate-200 dark:bg-slate-700 rounded" />
      ) : !data?.length ? (
        <div className="text-sm opacity-70">Aucune détection récente</div>
      ) : (
        <div className="space-y-2">
          {data.slice(0, 10).map((w, i) => (
            <div key={w.id || i} className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 p-2">
              <div className="font-medium">{(w.action || "").toUpperCase()} {w.token}</div>
              <div className="text-sm opacity-80">Qté: {w.amount ?? "—"}</div>
              <div className="text-sm opacity-80">{w.exchange || "—"}</div>
              <div className="text-sm">{w.value_eur != null ? `${nf.format(w.value_eur)} €` : "—"}</div>
              <div className="text-xs opacity-60">{w.timestamp || "—"}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-800">
      <div className="mb-3 text-sm font-semibold opacity-80">{title}</div>
      {children}
    </div>
  );
}
function CardError({ title, error, onRetry }) {
  return (
    <Card title={title}>
      <div className="text-sm text-red-600 mb-2">Erreur : {error.message}</div>
      <button onClick={onRetry} className="px-3 py-1 rounded bg-slate-900 text-white text-sm">
        Réessayer
      </button>
    </Card>
  );
}
