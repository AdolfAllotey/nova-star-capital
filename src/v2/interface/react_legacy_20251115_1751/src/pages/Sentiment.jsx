// src/pages/Sentiment.jsx
import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

const MODE_LABELS = {
  bull: "Bull (risk-on)",
  bear: "Bear (risk-off)",
  neutral: "Neutre / Range",
};

const MODE_COLORS = {
  bull: "text-emerald-400 border-emerald-500/40 bg-emerald-500/5",
  bear: "text-red-400 border-red-500/40 bg-red-500/5",
  neutral: "text-zinc-300 border-zinc-500/40 bg-zinc-500/5",
};

function formatDate(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString("fr-FR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return String(value);
  }
}

export default function Sentiment() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getSentimentOverview();
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[Sentiment] Erreur API:", err);
        setError(err?.message || "Erreur lors du chargement du sentiment.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    // on pourra plus tard ajouter un refresh auto si besoin
    return () => {
      alive = false;
    };
  }, []);

  const mode = data?.mode || "neutral";
  const score = typeof data?.score === "number" ? data.score : null;
  const updatedAt = data?.updated_at || data?.updatedAt;
  const source = data?.source || "n/a";

  const badgeColor =
    MODE_COLORS[mode] || MODE_COLORS.neutral;
  const modeLabel =
    MODE_LABELS[mode] || `Mode : ${mode}`;

  return (
    <div className="p-6 space-y-6">
      {/* Titre + résumé */}
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            Sentiment & Market Mood
          </h1>
          <p className="text-sm text-zinc-400">
            Synthèse du sentiment agrégé (Telegram, Twitter, Reddit, flux marché…)
          </p>
        </div>
        <div className="text-xs text-right text-zinc-500 space-y-1">
          <div>
            Dernière mise à jour :{" "}
            <span className="text-zinc-300">
              {formatDate(updatedAt)}
            </span>
          </div>
          <div>
            Source : <span className="text-zinc-300">{source}</span>
          </div>
        </div>
      </header>

      {/* Carte principale : mode + score */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Bloc mode */}
        <div className="col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 shadow-lg shadow-black/40">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">
                Régime de sentiment
              </h2>
              <p className="mt-1 text-lg font-semibold text-zinc-50">
                {modeLabel}
              </p>
            </div>
            <span
              className={[
                "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
                badgeColor,
              ].join(" ")}
            >
              {mode.toUpperCase()}
            </span>
          </div>

          {/* Gauge / Progress textuelle */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-zinc-500 mb-2">
              <span>Bearish</span>
              <span>Neutre</span>
              <span>Bullish</span>
            </div>
            <div className="relative h-2 rounded-full bg-zinc-800 overflow-hidden">
              {/* fond gradient */}
              <div className="absolute inset-0 bg-gradient-to-r from-red-500/50 via-amber-400/40 to-emerald-500/60" />
              {/* curseur */}
              {score != null && (
                <div
                  className="absolute top-0 h-full w-1 bg-zinc-50 shadow-[0_0_10px_rgba(255,255,255,0.8)]"
                  style={{
                    left: `${Math.min(Math.max(score, 0), 1) * 100}%`,
                  }}
                />
              )}
            </div>
            <div className="mt-2 text-xs text-zinc-400">
              Score agrégé :{" "}
              <span className="text-zinc-100 font-medium">
                {score != null ? score.toFixed(2) : "n/a"}
              </span>{" "}
              (0 = très négatif, 1 = très positif)
            </div>
          </div>

          {/* État chargement / erreur */}
          <div className="mt-4 text-xs">
            {loading && (
              <p className="text-amber-400">
                Chargement du sentiment en cours…
              </p>
            )}
            {!loading && error && (
              <p className="text-red-400">
                Erreur : {error}
              </p>
            )}
            {!loading && !error && !data && (
              <p className="text-zinc-500">
                Aucune donnée de sentiment disponible pour le moment.
              </p>
            )}
          </div>
        </div>

        {/* Bloc debug / raw data */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-4 text-xs text-zinc-400 font-mono overflow-auto max-h-[260px]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-zinc-300 font-semibold">
              Debug / Raw data
            </span>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] uppercase tracking-wide">
              /sentiment/overview
            </span>
          </div>
          <pre className="whitespace-pre-wrap break-words">
            {loading && "Chargement…"}
            {!loading && error && `Erreur: ${error}`}
            {!loading && !error && data
              ? JSON.stringify(data, null, 2)
              : !loading && !error && !data
              ? "Aucune donnée."
              : null}
          </pre>
        </div>
      </div>
    </div>
  );
}
