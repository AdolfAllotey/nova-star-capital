import React from "react";
import { useWorst, useWorstSummary } from "../hooks/useNscData";

const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

export default function WorstTrades() {
  const { data: worst, err: errW, loading: loadW, refresh: refW } = useWorst();
  const { data: summary, err: errS, loading: loadS, refresh: refS } = useWorstSummary();

  if (errW) return <CardError title="Pires trades" error={errW} onRetry={refW} />;
  if (errS) return <CardError title="Résumé LLM" error={errS} onRetry={refS} />;

  return (
    <div className="grid gap-4">
      <Card title="Résumé LLM">
        {loadS ? (
          <div className="animate-pulse h-5 w-64 bg-slate-200 dark:bg-slate-700 rounded" />
        ) : (
          <p className="text-sm opacity-80">{summary?.summary || "—"}</p>
        )}
      </Card>

      <Card title="Top 5 pertes">
        {loadW ? (
          <div className="animate-pulse h-24 bg-slate-200 dark:bg-slate-700 rounded" />
        ) : !worst?.length ? (
          <div className="text-sm opacity-70">Aucune perte enregistrée</div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {worst.slice(0, 5).map((w) => (
              <div key={w.id || `${w.token}-${w.closed_at}`} className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
                <div className="font-semibold">{w.token}</div>
                <div className="text-red-600">Perte : {fmt(w.loss_eur)} €</div>
                <div className="text-xs opacity-70">{w.exchange}</div>
                <div className="text-xs opacity-60">{w.opened_at} → {w.closed_at || "—"}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
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
const fmt = (v) => (v == null ? "—" : nf.format(v));
