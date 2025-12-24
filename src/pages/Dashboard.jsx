import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

const API_BASE = ""; // même origine (Caddy reverse-proxy), sinon "https://api.preprod.novastarcapital.fr"

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [regime, setRegime] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [trades, setTrades] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setLoading(true);
        const [r, s, m, t] = await Promise.all([
          fetch(`${API_BASE}/api/market/regime`).then((r) => r.json()),
          fetch(`${API_BASE}/api/signals/sentiment`).then((r) => r.json()),
          fetch(`${API_BASE}/api/status/metrics`).then((r) => r.json()),
          fetch(`${API_BASE}/api/trades`).then((r) => r.json()),
        ]);
        if (!alive) return;
        setRegime(r);
        setSentiment(s);
        setMetrics(m);
        setTrades(t);
      } catch (e) {
        if (!alive) return;
        setError(e?.message || "Fetch error");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    const id = setInterval(load, 30_000); // rafraîchit toutes les 30s
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Construit une série PnL à partir des trades simulés si dispo (fallback sinon)
  const pnlSeries = useMemo(() => {
    const simulated = trades?.simulated || [];
    if (Array.isArray(simulated) && simulated.length > 0) {
      // attend un champ cumulative_pnl ou pnl; sinon cumule
      let cum = 0;
      return simulated.slice(-30).map((tr, i) => {
        const delta = Number(tr.pnl ?? tr.profit ?? 0);
        cum += isFinite(delta) ? delta : 0;
        return { t: tr.date || tr.timestamp || `T${i + 1}`, pnl: Number(cum.toFixed(2)) };
      });
    }
    // Fallback visuel (3 points)
    return [
      { t: "M-2", pnl: 950 },
      { t: "M-1", pnl: -320 },
      { t: "M",   pnl: 480 },
    ];
  }, [trades]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <header className="mb-8">
        <nav className="text-sm mb-2 space-x-4">
          <a href="/" className="font-semibold">NSC</a>
          <a href="/" className="opacity-70 hover:opacity-100">Dashboard</a>
          <a href="/status" className="opacity-70 hover:opacity-100">Statut</a>
        </nav>
        <h1 className="text-3xl font-extrabold tracking-tight">NSC — Dashboard</h1>
        {error && <p className="mt-2 text-red-500 text-sm">Erreur: {error}</p>}
      </header>

      {/* Cards top */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Market Regime" loading={loading}>
          <p className="uppercase tracking-widest font-black">
            {regime?.regime || "—"}
          </p>
          <p className="mt-1">
            <b>Score:</b> {fmt(regime?.score)}<br/>
            <b>Date:</b> {iso(regime?.date)}
          </p>
        </Card>

        <Card title="Sentiment & Momentum" loading={loading}>
          <p><b>Sentiment:</b> {fmt(sentiment?.sentiment)}</p>
          <p><b>Momentum:</b> {fmt(sentiment?.momentum)}</p>
          <p><b>Date:</b> {iso(sentiment?.date)}</p>
        </Card>

        <Card title="System Metrics" loading={loading}>
          <p className="whitespace-pre-wrap text-sm">
            app: {metrics?.app || "n/a"} | py: {metrics?.python || "n/a"} | host: {metrics?.host || "n/a"}
          </p>
        </Card>
      </section>

      {/* PnL */}
      <section className="mt-8">
        <Card title="PnL (Derniers points)">
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={pnlSeries} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="pnl" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Bottom widgets */}
      <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Whales" loading={loading}>
          <p>{(trades?.whales?.length ?? 0) > 0 ? `${trades.whales.length} évènement(s)` : "Aucun événement."}</p>
        </Card>
        <Card title="Trades — Simulated" loading={loading}>
          <p>{trades?.count_simulated ?? (trades?.simulated?.length ?? 0)} trade(s)</p>
        </Card>
        <Card title="Open positions" loading={loading}>
          <p>{trades?.count_open ?? (trades?.open_positions?.length ?? 0)} position(s)</p>
        </Card>
      </section>
    </div>
  );
}

function Card({ title, children, loading }) {
  return (
    <div className="rounded-2xl border border-neutral-200/40 dark:border-neutral-800/60 p-5 bg-white/70 dark:bg-neutral-900/60 backdrop-blur">
      <h2 className="text-lg font-bold mb-2">{title}</h2>
      {loading ? <p className="text-sm opacity-70">Chargement…</p> : children}
    </div>
  );
}

function fmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}
function iso(v) {
  if (!v) return "—";
  try { return new Date(v).toISOString(); } catch { return String(v); }
}
