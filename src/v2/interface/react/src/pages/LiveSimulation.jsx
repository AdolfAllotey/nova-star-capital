// src/pages/LiveSimulation.jsx

import React, { useEffect, useMemo, useRef, useState } from "react";
import { connectLive } from "../lib/live";
import Sparkline from "../components/Sparkline";
import { fetchJSON } from "../lib/api";

const WS_URL =
  (import.meta.env.VITE_WS_BASE || "").replace(/\/+$/, "") ||
  // fallback si non défini : dérive de l'URL API http://localhost:8000 -> ws://localhost:8000
  (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/^http/, "ws") +
    "/ws/live";

/**
 * Attendu côté serveur (messages JSON) :
 * { type: "pnl.tick", payload: { t: <iso>, v: <number> } }
 * { type: "trade", payload: { t: <iso>, side: "buy|sell", symbol: "...", amount: ..., price: ... } }
 * { type: "regime", payload: { mode: "bull|bear|neutral", score: <number>, t: <iso> } }
 */
export default function LiveSimulation() {
  
  const [nowEpochMs] = useState(() => Date.now());
const [pnl, setPnl] = useState([]);         // [{t, v}]
  const [events, setEvents] = useState([]);   // feed des derniers trades/infos
  const [regime, setRegime] = useState(null); // dernier mode reçu
  const connRef = useRef(null);

  // Fallback de sécurité : on précharge quelques points (optionnel)
  useEffect(() => {
    let alive = true;
    (async () => {
      // si tu as un endpoint PnL "snapshot" (optionnel), sinon on saute
      const snap = await fetchJSON("/live/snapshot", { pnl: [] });
      if (alive && Array.isArray(snap?.pnl)) {
        setPnl(
          snap.pnl
            .map((d) => ({ t: d.t, v: Number(d.v) }))
            .filter((d) => Number.isFinite(d.v))
        );
      }
    })();
    return () => { alive = false; };
  }, []);

  // Connexion live
  useEffect(() => {
    const conn = connectLive({
      url: WS_URL,
      onMessage: (msg) => {
        if (!msg || typeof msg !== "object") return;
        const { type, payload } = msg;

        if (type === "pnl.tick" && payload) {
          setPnl((prev) => {
            const next = [...prev, { t: payload.t || Date.now(), v: Number(payload.v) }];
            // limitation à 500 points pour garder le graph fluide
            return next.slice(-500);
          });
        }

        if (type === "trade" && payload) {
          setEvents((prev) =>
            [{ ...payload, _t: payload.t || Date.now() }, ...prev].slice(0, 50)
          );
        }

        if (type === "regime" && payload) {
          setRegime({ mode: payload.mode, score: payload.score, t: payload.t || Date.now() });
        }
      },
      onError: () => {},
    });
    connRef.current = conn;
    return () => { conn && conn.close(); };
  }, []);

  const pnlStats = useMemo(() => {
    if (pnl.length < 2) return null;
    const first = pnl[0].v;
    const last = pnl[pnl.length - 1].v;
    const delta = last - first;
    const pct = first !== 0 ? (delta / Math.abs(first)) * 100 : 0;
    return { first, last, delta, pct };
  }, [pnl]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-lg font-semibold">Live Simulation</h1>
        <div className="text-sm text-zinc-400">
          WS: <code className="text-zinc-300">{WS_URL.replace(/^ws:\/\//, "")}</code>
        </div>
      </div>

      {/* Bloc Regime instantané */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-xl border border-zinc-800 p-4">
          <div className="text-sm text-zinc-400">Market Regime (live)</div>
          <div className="mt-2 text-xl font-semibold">
            {regime ? regime.mode?.toUpperCase() : "—"}
          </div>
          <div className="text-sm text-zinc-400">
            score: {regime ? (Number(regime.score)?.toFixed(2)) : "—"}
          </div>
        </div>

        {/* Stats PnL */}
        <div className="rounded-xl border border-zinc-800 p-4">
          <div className="text-sm text-zinc-400">PnL (session)</div>
          {pnlStats ? (
            <div className="mt-2">
              <div className="text-xl font-semibold">
                {pnlStats.last.toFixed(2)} <span className="text-sm text-zinc-400">€</span>
              </div>
              <div className="text-sm">
                Δ {pnlStats.delta >= 0 ? "+" : ""}
                {pnlStats.delta.toFixed(2)} ({pnlStats.pct >= 0 ? "+" : ""}
                {pnlStats.pct.toFixed(2)}%)
              </div>
            </div>
          ) : (
            <div className="mt-2 text-zinc-400 text-sm">En attente de ticks…</div>
          )}
        </div>

        {/* Graph sparkline PnL */}
        <div className="rounded-xl border border-zinc-800 p-4">
          <div className="text-sm text-zinc-400">PnL — Live</div>
          <div className="mt-2">
            <Sparkline data={pnl} height={56} />
          </div>
        </div>
      </div>

      {/* Feed des derniers événements trades */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <div className="px-4 py-3 bg-zinc-900/60 text-sm text-zinc-300">
          Derniers événements (trades / signaux)
        </div>
        <div className="divide-y divide-zinc-800">
          {events.length === 0 ? (
            <div className="px-4 py-6 text-sm text-zinc-400">Aucun événement pour l’instant.</div>
          ) : (
            events.map((e, idx) => (
              <div key={idx} className="px-4 py-3 flex items-center justify-between">
                <div className="text-sm">
                  <span className="px-2 py-0.5 rounded-md border border-zinc-700 mr-2">
                    {e.side ? e.side.toUpperCase() : e.type || "EVENT"}
                  </span>
                  {e.symbol ? <strong>{e.symbol}</strong> : null}
                  {typeof e.amount !== "undefined" && (
                    <span className="ml-2 text-zinc-400">amount: {e.amount}</span>
                  )}
                  {typeof e.price !== "undefined" && (
                    <span className="ml-2 text-zinc-400">@ {e.price}</span>
                  )}
                </div>
                <div className="text-xs text-zinc-500">
                  {new Date(e._t || 0).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
