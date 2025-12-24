import React, { useEffect, useMemo, useState } from "react";
import { Card } from "../ui/Card.jsx";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function Pill({ label, tone = "zinc" }) {
  const cn = {
    zinc: "bg-zinc-800/60 text-zinc-200 ring-1 ring-zinc-700/60",
    green:"bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30",
    red:  "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30",
  }[tone];
  return <span className={`px-3 py-1 rounded-full text-sm ${cn}`}>{label}</span>;
}

export default function MarketRegime() {
  const [state, setState] = useState({ loading: true, error: null, regime: "unknown", score: null, history: [] });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // 1) Essaye un endpoint dédié /regime (si tu l’as)
        let r = await fetch(`${API_BASE}/regime`, { cache: "no-store" });
        if (r.ok) {
          const j = await r.json();
          if (!alive) return;
          setState({
            loading: false,
            error: null,
            regime: (j?.regime || j?.market_regime || "unknown").toLowerCase(),
            score: j?.score ?? null,
            history: j?.history ?? [],
          });
          return;
        }
      } catch {}

      // 2) Fallback: déduire depuis /metrics si exposé
      try {
        const r2 = await fetch(`${API_BASE}/metrics`, { cache: "no-store" });
        if (!r2.ok) throw new Error("metrics not ok");
        const m = await r2.json();
        if (!alive) return;
        const regime = String(m?.regime?.current ?? "unknown").toLowerCase();
        const score  = m?.regime?.score ?? null;
        const history = m?.regime?.history ?? [];
        setState({ loading: false, error: null, regime, score, history });
      } catch (e) {
        if (!alive) return;
        setState({ loading: false, error: "Impossible de récupérer le régime de marché.", regime: "unknown", score: null, history: [] });
      }
    })();
    return () => { alive = false; };
  }, []);

  const tone = useMemo(() => {
    if (state.regime === "bull") return "green";
    if (state.regime === "bear") return "red";
    return "zinc";
  }, [state.regime]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Régime actuel</h2>
          <Pill label={(state.loading ? "…" : state.regime).toUpperCase()} tone={tone} />
        </div>
        <div className="space-y-3 text-sm text-zinc-300">
          <div className="flex items-center justify-between">
            <span>Score</span>
            <span className="font-mono">{state.score ?? "n/a"}</span>
          </div>
          {state.error && <div className="text-rose-300">{state.error}</div>}
          <div className="text-zinc-500 text-xs">
            Source: <code>{API_BASE}</code>
          </div>
        </div>
      </Card>

      <Card className="xl:col-span-2">
        <h2 className="text-lg font-semibold mb-4">Historique du score / régime</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={state.history}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" hide />
              <YAxis />
              <Tooltip />
              <ReferenceLine y={0} strokeDasharray="3 3" />
              <Line type="monotone" dataKey="score" stroke="#22c55e" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h3 className="text-base font-semibold mb-3">Guides décisions</h3>
        <ul className="text-sm text-zinc-300 space-y-2 list-disc pl-5">
          <li><strong>Bull:</strong> augmenter la part Trading (ex: 65%), allonger les stops dynamiques.</li>
          <li><strong>Bear:</strong> réduire le risque, privilégier LT et sécurité, seuils d’arrêt plus stricts.</li>
          <li><strong>Neutre:</strong> tailles standard, filtrage strict des signaux momentum.</li>
        </ul>
      </Card>
    </div>
  );
}
