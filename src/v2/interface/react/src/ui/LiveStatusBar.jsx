// src/ui/LiveStatusBar.jsx
// Version polished + fine-tuning visuel (animations douces, rendu premium)

import React, { useEffect, useState } from "react";
import { API_BASE } from "../lib/apiBase";
import { Wifi, BarChart2, Gauge, TrendingUp } from "lucide-react";

function pill(ok) {
  return ok
    ? "inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 text-[11px]"
    : "inline-flex items-center gap-1.5 rounded-full bg-red-500/10 text-red-300 border border-red-500/40 px-2.5 py-0.5 text-[11px]";
}

export default function LiveStatusBar() {
  const [apiOk, setApiOk] = useState(true);
  const [regime, setRegime] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [profitability, setProfitability] = useState(null);
  const [loading, setLoading] = useState(true);

  // Pour une petite animation de “pulse” quand le PnL change de signe
  const [pnlSign, setPnlSign] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function safe(path) {
      try {
        const res = await fetch(`${API_BASE}${path}`);
        if (!res.ok) return null;
        return await res.json();
      } catch {
        return null;
      }
    }

    async function load() {
      const [status, reg, sent, prof] = await Promise.all([
        safe("/status"),
        safe("/market/regime"),
        safe("/sentiment/overview"),
        safe("/profitability/monthly"),
      ]);

      if (cancelled) return;

      setApiOk(status?.ok !== false);
      setRegime(reg);
      setSentiment(sent);
      setProfitability(prof);
      setLoading(false);
    }

    load();
    const id = setInterval(load, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const regimeLabel = regime?.label || "Inconnu";
  const confidence =
    typeof regime?.confidence === "number"
      ? `${(regime.confidence * 100).toFixed(0)} %`
      : "n/d";

  const sentimentScoreNum =
    typeof sentiment?.score === "number" ? sentiment.score : null;

  const sentimentScore =
    sentimentScoreNum !== null ? sentimentScoreNum.toFixed(2) : "n/d";

  const sentimentLabel = sentiment?.label || sentimentScore;

  const monthlyNet =
    typeof profitability?.net_pnl === "number"
      ? profitability.net_pnl
      : typeof profitability?.monthly_pnl === "number" &&
        typeof profitability?.monthly_costs === "number"
      ? profitability.monthly_pnl - profitability.monthly_costs
      : null;

  // Classe pour le PnL + petite animation quand ça change de signe
  let pnlClassBase = "transition-colors duration-300";
  let newSign = 0;

  if (typeof monthlyNet === "number" && Number.isFinite(monthlyNet)) {
    if (monthlyNet > 0) {
      newSign = 1;
      pnlClassBase += " text-emerald-400";
    } else if (monthlyNet < 0) {
      newSign = -1;
      pnlClassBase += " text-red-400";
    } else {
      pnlClassBase += " text-zinc-200";
    }
  } else {
    pnlClassBase += " text-zinc-200";
  }

  // Détecter un changement de signe (de positif à négatif ou inversement)
  useEffect(() => {
    if (newSign !== 0 && newSign !== pnlSign) {
      setPnlSign(newSign);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newSign]);

  const pnlAnimatedClass =
    pnlSign !== 0
      ? pnlClassBase +
        " animate-[pulse_0.6s_ease-out_1]"
      : pnlClassBase;

  const f = (v) =>
    typeof v === "number"
      ? new Intl.NumberFormat("fr-FR", {
          style: "currency",
          currency: "EUR",
          maximumFractionDigits: 2,
        }).format(v)
      : "n/d";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 px-4 py-2.5 text-xs text-zinc-300 flex flex-wrap items-center gap-x-6 gap-y-2">
      {/* API */}
      <div className="flex items-center gap-2">
        <span className={pill(apiOk)}>
          <Wifi className="w-3.5 h-3.5" />
          {apiOk ? "API OK" : "API ERROR"}
        </span>
        {loading && (
          <span className="text-[10px] text-zinc-500">
            Mise à jour…
          </span>
        )}
      </div>

      {/* Régime */}
      <div className="flex items-center gap-2">
        <Gauge className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-[11px] text-zinc-500 uppercase">Régime :</span>
        <span className="text-zinc-100 transition-colors duration-300">
          {regimeLabel}
        </span>
        <span className="text-zinc-500 text-[10px]">({confidence})</span>
      </div>

      {/* Sentiment */}
      <div className="flex items-center gap-2">
        <BarChart2 className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-[11px] text-zinc-500 uppercase">
          Sentiment :
        </span>
        <span className="text-zinc-100 transition-colors duration-300">
          {sentimentLabel}
        </span>
        <span className="text-zinc-500 text-[10px]">
          ({sentimentScore})
        </span>
      </div>

      {/* PnL net */}
      <div className="flex items-center gap-2">
        <TrendingUp className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-[11px] text-zinc-500 uppercase">
          PnL net (mois) :
        </span>
        <span className={pnlAnimatedClass}>{f(monthlyNet)}</span>
      </div>
    </div>
  );
}
