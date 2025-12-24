// src/pages/WorstTrades.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

// Helpers formats
function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  try {
    return Number(value).toLocaleString("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    });
  } catch {
    return String(value);
  }
}

function formatPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  try {
    return `${Number(value).toFixed(1)} %`;
  } catch {
    return String(value);
  }
}

function formatDateTime(value) {
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

export default function WorstTrades() {
  const [data, setData] = useState(null); // réponse brute de l'API
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // On utilise le helper générique, comme pour Sentiment/Profitability
        const res = await api.getJSON("/worst-trades");
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[WorstTrades] Erreur API:", err);
        setError(err?.message || "Erreur lors du chargement des pires trades.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, []);

  // Normalisation de la liste de trades
  const trades = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data.trades)) return data.trades;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.worst_trades)) return data.worst_trades;
    return [];
  }, [data]);

  const updatedAt =
    data?.updated_at || data?.updatedAt || data?.generated_at || null;

  // Résumé LLM éventuel
  const summaryText = useMemo(() => {
    if (!data) return null;
    const s = data.summary || data.llm_summary || data.analysis;
    if (!s) return null;
    if (typeof s === "string") return s;
    // si c'est un objet, on essaie quelques clés classiques
    return (
      s.text ||
      s.content ||
      s.overview ||
      JSON.stringify(s, null, 2)
    );
  }, [data]);

  // Métriques simples
  const metrics = useMemo(() => {
    if (!trades.length) {
      return {
        totalLoss: null,
        avgLoss: null,
        worstLoss: null,
      };
    }

    const normalized = trades.map((t) => {
      const lossEur =
        Number(
          t.loss_eur ??
            t.loss_EUR ??
            t.lossFiat ??
            t.loss ??
            (t.pnl && t.pnl < 0 ? -t.pnl : 0),
        ) || 0;
      const lossPct =
        Number(
          t.loss_pct ??
            t.lossPercent ??
            t.pnl_pct ??
            t.pnlPct ??
            0,
        ) || 0;

      return { ...t, _lossEur: lossEur, _lossPct: lossPct };
    });

    let totalLoss = 0;
    for (const t of normalized) {
      if (Number.isFinite(t._lossEur)) totalLoss += t._lossEur;
    }
    const avgLoss = normalized.length ? totalLoss / normalized.length : null;

    const worstLoss = normalized.reduce(
      (acc, t) => (acc == null || t._lossEur > acc._lossEur ? t : acc),
      null,
    );

    return { totalLoss, avgLoss, worstLoss };
  }, [trades]);

  return (
    <div className="p-6 space-y-6">
      {/* Titre + meta */}
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            Worst Trades & Blacklist
          </h1>
          <p className="text-sm text-zinc-400">
            Vue consolidée des pires trades simulés / réels, pour piloter le
            risque et la blacklist.
          </p>
        </div>
        <div className="text-xs text-right text-zinc-500 space-y-1">
          <div>
            Dernière analyse :{" "}
            <span className="text-zinc-300">{formatDateTime(updatedAt)}</span>
          </div>
          <div className="text-zinc-500">
            Endpoint :{" "}
            <code className="text-zinc-300 bg-zinc-900 px-1.5 py-0.5 rounded">
              /worst-trades
            </code>
          </div>
        </div>
      </header>

      {/* États globaux */}
      {loading && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-amber-400">
          Chargement des pires trades…
        </div>
      )}
      {!loading && error && (
        <div className="rounded-xl border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Erreur lors du chargement : {error}
        </div>
      )}

      {/* Contenu principal */}
      {!loading && !error && (
        <>
          {/* Cartes synthèse */}
          <section className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                Pertes cumulées (pire set)
              </div>
              <div className="mt-2 text-2xl font-semibold text-red-400">
                {metrics.totalLoss != null
                  ? `-${formatCurrency(metrics.totalLoss)}`
                  : "—"}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Somme des pertes des trades marqués comme &quot;worst&quot;.
              </p>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                Perte moyenne par trade
              </div>
              <div className="mt-2 text-2xl font-semibold text-amber-400">
                {metrics.avgLoss != null
                  ? `-${formatCurrency(metrics.avgLoss)}`
                  : "—"}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Permet de calibrer les tailles de position max.
              </p>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                Trade le plus destructeur
              </div>
              {metrics.worstLoss ? (
                <div className="mt-2">
                  <div className="text-sm text-zinc-200">
                    {metrics.worstLoss.token || metrics.worstLoss.symbol || "—"}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-red-400">
                    -{formatCurrency(metrics.worstLoss._lossEur)}{" "}
                    <span className="ml-2 text-xs text-red-300">
                      ({formatPct(metrics.worstLoss._lossPct)})
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    Raison :{" "}
                    {metrics.worstLoss.reason ||
                      metrics.worstLoss.exit_reason ||
                      "—"}
                  </p>
                </div>
              ) : (
                <p className="mt-2 text-xs text-zinc-500">
                  Pas encore de trades marqués comme &quot;pire&quot;.
                </p>
              )}
            </div>
          </section>

          {/* Résumé LLM / Analysis */}
          {summaryText && (
            <section className="rounded-2xl border border-emerald-900/60 bg-emerald-950/20 p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-medium text-emerald-300">
                  Synthèse stratégique (LLM)
                </h2>
                <span className="text-[10px] uppercase tracking-wide text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full">
                  worst_trades_summary
                </span>
              </div>
              <p className="text-sm text-emerald-100 whitespace-pre-line">
                {summaryText}
              </p>
            </section>
          )}

          {/* Tableau des trades */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-zinc-200">
                Détail des pires trades
              </h2>
              <span className="text-xs text-zinc-500">
                {trades.length} trade(s)
              </span>
            </div>

            {trades.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aucune ligne pour le moment. Dès que l&apos;analyse des pires
                trades sera exécutée, les tokens concernés apparaîtront ici.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-2 pr-4">Token</th>
                      <th className="py-2 pr-4">Perte (€)</th>
                      <th className="py-2 pr-4">Perte (%)</th>
                      <th className="py-2 pr-4">Entry</th>
                      <th className="py-2 pr-4">Exit</th>
                      <th className="py-2 pr-4">Raison</th>
                      <th className="py-2 pr-4">Tags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, idx) => {
                      const lossEur =
                        Number(
                          t.loss_eur ??
                            t.loss_EUR ??
                            t.lossFiat ??
                            t.loss ??
                            (t.pnl && t.pnl < 0 ? -t.pnl : 0),
                        ) || 0;
                      const lossPct =
                        Number(
                          t.loss_pct ??
                            t.lossPercent ??
                            t.pnl_pct ??
                            t.pnlPct ??
                            0,
                        ) || 0;

                      const entry =
                        t.entry_price ?? t.entry ?? t.entryPrice ?? null;
                      const exit =
                        t.exit_price ?? t.exit ?? t.exitPrice ?? null;

                      const tags =
                        t.tags ||
                        t.labels ||
                        (typeof t.category === "string"
                          ? [t.category]
                          : Array.isArray(t.category)
                          ? t.category
                          : []);

                      return (
                        <tr
                          key={idx}
                          className="border-b border-zinc-900/80 last:border-0"
                        >
                          <td className="py-1.5 pr-4 text-zinc-200">
                            {t.token || t.symbol || t.pair || "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-red-400">
                            -{formatCurrency(lossEur)}
                          </td>
                          <td className="py-1.5 pr-4 text-red-300">
                            {formatPct(lossPct)}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-300">
                            {entry != null ? entry : "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-300">
                            {exit != null ? exit : "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {t.reason ||
                              t.exit_reason ||
                              t.comment ||
                              "—"}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {Array.isArray(tags) && tags.length
                              ? tags.join(", ")
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Bloc debug JSON */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-4 text-xs text-zinc-400 font-mono overflow-auto max-h-[260px]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-300 font-semibold">
                Debug / Raw JSON
              </span>
              <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[10px] uppercase tracking-wide">
                risk.worst_trades
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
          </section>
        </>
      )}
    </div>
  );
}
