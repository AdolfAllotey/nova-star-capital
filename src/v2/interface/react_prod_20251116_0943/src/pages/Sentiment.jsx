// src/pages/Sentiment.jsx
import React, { useEffect, useState } from "react";
import { getSentimentOverview } from "../lib/api.js";

export default function Sentiment() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let aborted = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const res = await getSentimentOverview();
        if (!aborted) {
          setData(res);
        }
      } catch (e) {
        if (!aborted) {
          console.error("[Sentiment] error:", e);
          setError(e);
        }
      } finally {
        if (!aborted) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      aborted = true;
    };
  }, []);

  const mode = data?.mode ?? "neutral";
  const score = typeof data?.score === "number" ? data.score : 0;
  const updatedAt = data?.updated_at;

  const modeLabel =
    mode === "bull"
      ? "Bullish"
      : mode === "bear"
      ? "Bearish"
      : "Neutre";

  const barColor =
    mode === "bull"
      ? "bg-emerald-500"
      : mode === "bear"
      ? "bg-red-500"
      : "bg-slate-500";

  const percent = Math.min(Math.max((score + 1) / 2, 0), 1) * 100;

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Sentiment du marché
          </h1>
          <p className="text-sm text-zinc-400">
            Synthèse agrégée Telegram / Twitter / Reddit.
          </p>
        </div>
        {updatedAt && (
          <p className="text-xs text-zinc-500">
            Dernière mise à jour&nbsp;:{" "}
            {new Date(updatedAt).toLocaleString("fr-FR")}
          </p>
        )}
      </header>

      {loading && (
        <div className="text-sm text-zinc-400">Chargement du sentiment…</div>
      )}

      {error && (
        <div className="text-sm text-red-400">
          Erreur de chargement du sentiment.
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-6 md:grid-cols-[2fr,1fr]">
          {/* Gauge principale */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-zinc-500">
                  Sentiment agrégé
                </p>
                <p className="text-lg font-semibold">{modeLabel}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-zinc-500">Score</p>
                <p className="text-2xl font-bold">
                  {score.toFixed(2)}
                  <span className="text-sm text-zinc-500 ml-1">/ 1.00</span>
                </p>
              </div>
            </div>

            <div className="h-3 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className={`h-full ${barColor} transition-all duration-500`}
                style={{ width: `${percent}%` }}
              />
            </div>

            <div className="mt-2 flex justify-between text-[11px] text-zinc-500">
              <span>Bearish</span>
              <span>Neutre</span>
              <span>Bullish</span>
            </div>
          </div>

          {/* Détails bruts */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-xs text-zinc-400 space-y-2">
            <p className="font-semibold text-zinc-200">Détails bruts</p>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all">
              {JSON.stringify(data ?? {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </section>
  );
}
