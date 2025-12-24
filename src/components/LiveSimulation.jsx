import React from "react";
import { useTrades } from "../hooks/useNscData";

const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 4 });

export default function LiveSimulation() {
  const { data, err, loading, refresh } = useTrades();

  if (err) return <CardError title="Trades & Positions" error={err} onRetry={refresh} />;
  if (loading) return <CardLoading title="Trades & Positions" />;

  const trades = Array.isArray(data) ? data : (data?.trades || []);
  const open   = Array.isArray(data?.open_positions) ? data.open_positions : (data?.open || []);

  return (
    <Card title="Trades & Positions">
      <div className="grid md:grid-cols-2 gap-4">
        <section>
          <h4 className="font-semibold mb-2">Positions ouvertes</h4>
          {open?.length ? (
            <div className="space-y-2">
              {open.map((p) => (
                <Row key={p.id || `${p.token}-${p.opened_at}`}>
                  <div className="font-medium">{p.token}</div>
                  <div className="text-xs opacity-70">{p.exchange}</div>
                  <div className="text-sm">Entrée : {fmtNum(p.entry_price)}</div>
                  <div className="text-sm">Qté : {fmtNum(p.amount)}</div>
                </Row>
              ))}
            </div>
          ) : (
            <Empty label="Aucune position ouverte" />
          )}
        </section>
        <section>
          <h4 className="font-semibold mb-2">Derniers trades</h4>
          {trades?.length ? (
            <div className="space-y-2">
              {trades.slice(0, 20).map((t) => (
                <Row key={t.id || `${t.token}-${t.opened_at}`}>
                  <div className="font-medium">{t.token} · {t.side?.toUpperCase?.() || "?"}</div>
                  <div className="text-xs opacity-70">{t.exchange}</div>
                  <div className={Number(t.pnl) >= 0 ? "text-green-700" : "text-red-600"}>
                    PnL : {fmtNum(t.pnl)}
                  </div>
                  <div className="text-xs opacity-60">{t.opened_at}</div>
                </Row>
              ))}
            </div>
          ) : (
            <Empty label="Aucun trade récent" />
          )}
        </section>
      </div>
    </Card>
  );
}

/* helpers & UI */
const fmtNum = (v) => (v == null ? "—" : nf.format(v));
function Card({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-800">
      <div className="mb-3 text-sm font-semibold opacity-80">{title}</div>
      {children}
    </div>
  );
}
function Row({ children }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 p-2">
      {children}
    </div>
  );
}
function Empty({ label }) {
  return <div className="text-sm opacity-70">{label}</div>;
}
function CardLoading({ title }) {
  return (
    <Card title={title}>
      <div className="animate-pulse h-24 bg-slate-200 dark:bg-slate-700 rounded" />
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
