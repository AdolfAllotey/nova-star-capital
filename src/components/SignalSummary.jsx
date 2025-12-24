import React from "react";
import { useSentiment } from "../hooks/useNscData";

export default function SignalSummary() {
  const { data, err, loading, refresh } = useSentiment();

  if (err) return <CardError title="Sentiment & Momentum" error={err} onRetry={refresh} />;

  return (
    <Card title="Sentiment & Momentum">
      {loading ? (
        <div className="animate-pulse h-6 w-40 bg-slate-200 dark:bg-slate-700 rounded" />
      ) : (
        <div className="flex items-center gap-6">
          <Badge label="Sentiment" value={data?.sentiment} />
          <Badge label="Momentum" value={data?.momentum} />
          <div className="text-xs opacity-60">MAJ: {data?.updated_at || "—"}</div>
        </div>
      )}
    </Card>
  );
}

function Badge({ label, value }) {
  const txt = value == null ? "—" : `${Math.round(value * 100)}%`;
  return (
    <span className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1">
      <span className="text-xs opacity-60">{label}</span>
      <span className="text-sm font-medium">{txt}</span>
    </span>
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
