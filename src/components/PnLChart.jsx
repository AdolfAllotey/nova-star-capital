import React from "react";
import { usePnL } from "../hooks/useNscData";

const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

export default function PnLChart() {
  const { data, err, loading, refresh } = usePnL();

  if (err) return <CardError title="PnL / Equity" error={err} onRetry={refresh} />;
  if (loading) return <CardLoading title="PnL / Equity" />;

  if (!data) {
    return (
      <Card title="PnL / Equity">
        <p className="text-sm opacity-70">Aucune donnée (404). En attente du premier export.</p>
      </Card>
    );
  }

  const equity   = data.equity ?? data.equity_now ?? null;
  const pnlCum   = data.pnl_cum ?? data.pnl ?? null;
  const last     = data.last_update ?? data.updated_at ?? null;

  return (
    <Card title="PnL / Equity">
      <div className="grid md:grid-cols-3 gap-4">
        <Metric label="Equity" value={equity != null ? `${nf.format(equity)} €` : "—"} />
        <Metric label="PnL cumulé" value={pnlCum != null ? `${nf.format(pnlCum)} €` : "—"} />
        <Metric label="Dernière MAJ" value={last || "—"} small />
      </div>
      {/* Ici, branche ton graphique existant si tu as une série historique */}
    </Card>
  );
}

/* UI petites briques */
function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-800">
      <div className="mb-3 text-sm font-semibold opacity-80">{title}</div>
      {children}
    </div>
  );
}
function CardLoading({ title }) {
  return (
    <Card title={title}>
      <div className="animate-pulse h-6 w-40 bg-slate-200 dark:bg-slate-700 rounded" />
    </Card>
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
function Metric({ label, value, small = false }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide opacity-60">{label}</div>
      <div className={small ? "text-sm" : "text-xl font-semibold"}>{value}</div>
    </div>
  );
}
