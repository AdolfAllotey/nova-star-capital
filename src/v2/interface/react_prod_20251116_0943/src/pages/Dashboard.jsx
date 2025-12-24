import React, { useEffect, useMemo, useState } from "react";
import { Card } from "../ui/Card";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const API = import.meta.env.VITE_API_BASE;

export default function Dashboard() {
  const [movers, setMovers] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [regime, setRegime] = useState(null);
  const [pnl, setPnl] = useState([]);
  const [ico, setIco] = useState([]);

  // chargement parallèle
  useEffect(() => {
    Promise.all([
      fetch(`${API}/market/top-movers`).then((r) => (r.ok ? r.json() : {})),
      fetch(`${API}/sentiment/overview`).then((r) => (r.ok ? r.json() : {})),
      fetch(`${API}/market/regime`).then((r) => (r.ok ? r.json() : {})),
      fetch(`${API}/live/pnl`).then((r) => (r.ok ? r.json() : {})),
      fetch(`${API}/ico/scored`).then((r) => (r.ok ? r.json() : {})),
    ]).then(([m, s, r, p, i]) => {
      setMovers(m.items || []);
      setSentiment(s || {});
      setRegime(r || {});
      setPnl(p.items || []);
      setIco(i.items || []);
    });
  }, []);

  // mini data equity
  const pnlData = useMemo(() => {
    return pnl.map((d, i) => ({
      t: d.t || i,
      equity: Number(d.equity ?? 0),
    }));
  }, [pnl]);

  const normalizedSent = useMemo(() => {
    const v = Number(sentiment.score ?? 0);
    if (v >= 0 && v <= 1) return v;
    if (v < 0) return (v + 1) / 2;
    return Math.min(1, v / 100);
  }, [sentiment]);

  const normalizedRegime = useMemo(() => {
    const v = Number(regime.score ?? 0);
    if (v >= 0 && v <= 1) return v;
    if (v < 0) return (v + 1) / 2;
    return Math.min(1, v / 100);
  }, [regime]);

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-semibold">Dashboard</h2>

      {/* Bloc 1 : Régime & Sentiment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold mb-2">Market Regime</h3>
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">
              {regime.mode || "—"} ({normalizedRegime.toFixed(2)})
            </span>
            <div className="w-48 h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500"
                style={{ width: `${normalizedRegime * 100}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            {regime.updated_at || "n/a"} — {regime.source || "default"}
          </p>
        </Card>

        <Card>
          <h3 className="font-semibold mb-2">Sentiment</h3>
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">
              {sentiment.mode || "—"} ({normalizedSent.toFixed(2)})
            </span>
            <div className="w-48 h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full bg-cyan-500"
                style={{ width: `${normalizedSent * 100}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            {sentiment.updated_at || "n/a"} — {sentiment.source || "default"}
          </p>
        </Card>
      </div>

      {/* Bloc 2 : Équity live */}
      <Card>
        <h3 className="font-semibold mb-2">Évolution equity (live)</h3>
        <div className="h-48">
          {pnlData.length ? (
            <ResponsiveContainer>
              <LineChart data={pnlData}>
                <XAxis dataKey="t" hide />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #27272a" }}
                />
                <Line type="monotone" dataKey="equity" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-zinc-500 text-sm p-3">
              Aucune donnée de simulation en cours.
            </div>
          )}
        </div>
      </Card>

      {/* Bloc 3 : Top Movers */}
      <Card>
        <h3 className="font-semibold mb-3">Top Movers</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 text-sm">
          {movers.slice(0, 6).map((m, i) => (
            <div
              key={i}
              className="rounded-lg bg-zinc-900/60 p-2 border border-zinc-800"
            >
              <div className="font-medium">{m.symbol}</div>
              <div
                className={`text-xs ${
                  m.change24h >= 0 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {m.change24h?.toFixed?.(2)}%
              </div>
            </div>
          ))}
          {!movers.length && (
            <div className="text-zinc-500 text-sm p-2">Aucun mouvement disponible.</div>
          )}
        </div>
      </Card>

      {/* Bloc 4 : ICO résumé */}
      <Card>
        <h3 className="font-semibold mb-3">ICO — projets scorés</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {ico.slice(0, 3).map((p, i) => (
            <div
              key={i}
              className="rounded-lg bg-zinc-900/60 p-3 border border-zinc-800 text-sm"
            >
              <div className="font-semibold">{p.name || p.ticker || "—"}</div>
              <div className="text-zinc-400 text-xs mt-1">
                Score: {p.score ?? "—"} | Risque: {p.risk ?? "—"}
              </div>
            </div>
          ))}
          {!ico.length && (
            <div className="text-zinc-500 text-sm p-2">
              Aucun projet ICO scoré pour le moment.
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
