// src/pages/Dashboard.jsx
import React, { useEffect, useState } from "react";
import * as api from "../lib/api";

function Card({ title, children, className = "" }) {
  return (
    <div
      className={
        "bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 flex flex-col gap-3 " +
        className
      }
    >
      <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
      {children}
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="text-[11px] text-zinc-400">{label}</div>
      <div className="text-lg font-semibold text-zinc-100">{value}</div>
      {hint && <div className="text-[11px] text-zinc-500">{hint}</div>}
    </div>
  );
}

function RegimePill({ regime }) {
  const mode = regime?.mode || "neutral";
  const score = typeof regime?.score === "number" ? regime.score : 0;
  const label =
    mode === "bull" ? "Bull" : mode === "bear" ? "Bear" : "Neutre / Range";

  const colorClasses =
    mode === "bull"
      ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/40"
      : mode === "bear"
      ? "bg-red-500/10 text-red-300 border-red-500/40"
      : "bg-zinc-500/10 text-zinc-200 border-zinc-500/40";

  return (
    <div className="flex items-center gap-3">
      <span
        className={
          "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs " +
          colorClasses
        }
      >
        <span
          className={
            "inline-block h-2 w-2 rounded-full " +
            (mode === "bull"
              ? "bg-emerald-400"
              : mode === "bear"
              ? "bg-red-400"
              : "bg-zinc-400")
          }
        />
        {label}
      </span>
      <span className="text-[11px] text-zinc-400">
        Score : {(score * 100).toFixed(0)} / 100
      </span>
    </div>
  );
}

function SentimentBadge({ sentiment }) {
  const score = typeof sentiment?.score === "number" ? sentiment.score : 0;
  const mode = sentiment?.mode || "neutral";
  const label =
    mode === "bullish"
      ? "Bullish"
      : mode === "bearish"
      ? "Bearish"
      : "Neutre";

  const colorClasses =
    mode === "bullish"
      ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
      : mode === "bearish"
      ? "bg-red-500/10 text-red-300 border-red-500/30"
      : "bg-sky-500/10 text-sky-300 border-sky-500/30";

  return (
    <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs mt-1">
      <span className={colorClasses + " px-2 py-0.5 rounded-full border"}>
        {label}
      </span>
      <span className="text-[11px] text-zinc-400">
        Score : {(score * 100).toFixed(0)} / 100
      </span>
    </div>
  );
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [regime, setRegime] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [profitMonths, setProfitMonths] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [worstTrades, setWorstTrades] = useState([]);
  const [whales, setWhales] = useState([]);
  const [topMovers, setTopMovers] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        // 1) Régime de marché
        if (api.getMarketRegime) {
          try {
            const data = await api.getMarketRegime();
            if (!cancelled) setRegime(data || null);
          } catch (e) {
            console.error("[Dashboard] getMarketRegime error:", e);
          }
        }

        // 2) Sentiment global
        if (api.getSentimentOverview) {
          try {
            const data = await api.getSentimentOverview();
            if (!cancelled) setSentiment(data || null);
          } catch (e) {
            console.error("[Dashboard] getSentimentOverview error:", e);
          }
        }

        // 3) Profitabilité mensuelle
        if (api.getMonthlyProfitability) {
          try {
            const data = await api.getMonthlyProfitability();
            const items = Array.isArray(data?.items) ? data.items : [];
            if (!cancelled) setProfitMonths(items);
          } catch (e) {
            console.error("[Dashboard] getMonthlyProfitability error:", e);
          }
        }

        // 4) Positions ouvertes
        if (api.getOpenPositions) {
          try {
            const data = await api.getOpenPositions();
            const positions = Array.isArray(data?.positions)
              ? data.positions
              : Array.isArray(data?.items)
              ? data.items
              : [];
            if (!cancelled) setOpenPositions(positions);
          } catch (e) {
            console.error("[Dashboard] getOpenPositions error:", e);
          }
        }

        // 5) Pires trades
        if (api.getWorstTrades) {
          try {
            const data = await api.getWorstTrades();
            const items = Array.isArray(data?.items) ? data.items : [];
            if (!cancelled) setWorstTrades(items);
          } catch (e) {
            console.error("[Dashboard] getWorstTrades error:", e);
          }
        }

        // 6) Whales leaderboard
        if (api.getWhaleLeaderboard) {
          try {
            const data = await api.getWhaleLeaderboard();
            const items = Array.isArray(data?.items) ? data.items : [];
            if (!cancelled) setWhales(items);
          } catch (e) {
            console.error("[Dashboard] getWhaleLeaderboard error:", e);
          }
        }

        // 7) Top movers
        if (api.getTopMovers) {
          try {
            const data = await api.getTopMovers();
            const items = Array.isArray(data?.items) ? data.items : [];
            if (!cancelled) setTopMovers(items);
          } catch (e) {
            console.error("[Dashboard] getTopMovers error:", e);
          }
        }
      } catch (e) {
        console.error("[Dashboard] global error:", e);
        if (!cancelled) {
          setError(
            "Une erreur est survenue lors du chargement des données du dashboard."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Quelques agrégats simples
  const nbMonths = profitMonths.length;
  const lastMonth = nbMonths > 0 ? profitMonths[nbMonths - 1] : null;
  const lastMonthNet =
    typeof lastMonth?.net === "number"
      ? lastMonth.net
      : typeof lastMonth?.pnl_net === "number"
      ? lastMonth.pnl_net
      : null;

  const openCount = openPositions.length;
  const worstCount = worstTrades.length;
  const whalesCount = whales.length;

  const top5 = topMovers.slice(0, 5);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Vue d’ensemble</h1>
          <p className="text-sm text-zinc-400">
            Résumé temps quasi-réel du bot Nova Star Capital : régime de
            marché, sentiment, performance et risques.
          </p>
        </div>
        <div className="text-[11px] text-zinc-500">
          API : <code>{import.meta.env.VITE_API_BASE || "http://localhost:8000"}</code>
          <br />
          {loading ? (
            <span className="text-amber-400">Chargement des données…</span>
          ) : error ? (
            <span className="text-red-400">Erreur de chargement</span>
          ) : (
            <span className="text-emerald-400">Données chargées</span>
          )}
        </div>
      </div>

      {/* Première rangée : régime + stats clés */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Régime de marché">
          {regime ? (
            <>
              <RegimePill regime={regime} />
              <p className="mt-2 text-[11px] text-zinc-400">
                Le Market Regime Detector pilote l’intensité du trading, la
                taille des positions et la répartition des gains entre trading,
                long terme et sécurité.
              </p>
            </>
          ) : (
            <p className="text-xs text-zinc-500">
              Aucune donnée de régime disponible pour le moment.
            </p>
          )}
        </Card>

        <Card title="Sentiment & Whales">
          <div className="flex flex-col gap-3">
            {sentiment ? (
              <SentimentBadge sentiment={sentiment} />
            ) : (
              <div className="text-xs text-zinc-500">
                Sentiment non disponible (scrapers en attente ou pipeline en
                pause).
              </div>
            )}
            <div className="grid grid-cols-2 gap-3 mt-1">
              <Stat
                label="Whales suivies"
                value={whalesCount}
                hint="wallets trackés dans le leaderboard"
              />
              <Stat
                label="Worst trades"
                value={worstCount}
                hint="trades surveillés pour la blacklist"
              />
            </div>
          </div>
        </Card>

        <Card title="Performance & exposition">
          <div className="grid grid-cols-2 gap-3">
            <Stat
              label="Historique mensuel"
              value={nbMonths}
              hint="mois de performance disponibles"
            />
            <Stat
              label="Positions ouvertes"
              value={openCount}
              hint="positions actuellement en portefeuille"
            />
          </div>
          <div className="mt-3">
            <div className="text-[11px] text-zinc-400 mb-1">
              Dernier mois (net, si disponible)
            </div>
            <div className="text-lg font-semibold">
              {lastMonthNet !== null ? (
                <>
                  {lastMonthNet.toLocaleString("fr-FR", {
                    style: "currency",
                    currency: "EUR",
                    maximumFractionDigits: 0,
                  })}
                </>
              ) : (
                <span className="text-zinc-500">N/A</span>
              )}
            </div>
            {lastMonth?.month && (
              <div className="text-[11px] text-zinc-500">
                Période : {lastMonth.month}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Deuxième rangée : Top movers + Open positions + Worst trades */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card title="Top movers (aperçu)">
          {top5.length === 0 ? (
            <p className="text-xs text-zinc-500">
              Aucune donnée de Top Movers pour le moment. Le job
              <code className="ml-1 text-[10px] bg-zinc-900 px-1 py-0.5 rounded">
                nsc-top-movers.service
              </code>{" "}
              met à jour ce bloc.
            </p>
          ) : (
            <div className="text-xs overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-400">
                    <th className="py-1 pr-2">Token</th>
                    <th className="py-1 pr-2 text-right">Δ 24h</th>
                    <th className="py-1 pr-0 text-right">Δ 1h</th>
                  </tr>
                </thead>
                <tbody>
                  {top5.map((item, idx) => {
                    const name =
                      item.name || item.symbol || item.id || "Token";
                    const symbol = item.symbol || "";
                    const c24 =
                      typeof item.change_24h === "number"
                        ? item.change_24h
                        : typeof item.price_change_24h === "number"
                        ? item.price_change_24h
                        : null;
                    const c1 =
                      typeof item.change_1h === "number"
                        ? item.change_1h
                        : null;

                    const fmt = (v) =>
                      v === null
                        ? "–"
                        : `${v > 0 ? "+" : ""}${v.toFixed(1)} %`;

                    return (
                      <tr key={item.id || symbol || idx} className="border-b border-zinc-900/60">
                        <td className="py-1 pr-2">
                          <div className="flex flex-col">
                            <span className="text-zinc-100">{name}</span>
                            {symbol && (
                              <span className="text-[11px] text-zinc-500">
                                {symbol.toUpperCase()}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-1 pr-2 text-right">
                          <span
                            className={
                              "text-[11px] " +
                              (c24 === null
                                ? "text-zinc-400"
                                : c24 >= 0
                                ? "text-emerald-400"
                                : "text-red-400")
                            }
                          >
                            {fmt(c24)}
                          </span>
                        </td>
                        <td className="py-1 pr-0 text-right">
                          <span
                            className={
                              "text-[11px] " +
                              (c1 === null
                                ? "text-zinc-400"
                                : c1 >= 0
                                ? "text-emerald-400"
                                : "text-red-400")
                            }
                          >
                            {fmt(c1)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Positions ouvertes (aperçu)">
          {openPositions.length === 0 ? (
            <p className="text-xs text-zinc-500">
              Aucune position ouverte actuellement ou fichier{" "}
              <code className="bg-zinc-900 px-1 py-0.5 rounded text-[10px]">
                trading/open_positions.json
              </code>{" "}
              vide.
            </p>
          ) : (
            <div className="text-xs overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-400">
                    <th className="py-1 pr-2">Token</th>
                    <th className="py-1 pr-2 text-right">Taille</th>
                    <th className="py-1 pr-0 text-right">P&L latent</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.slice(0, 5).map((pos, idx) => {
                    const symbol = pos.symbol || pos.token || "Asset";
                    const size =
                      typeof pos.amount === "number"
                        ? pos.amount
                        : typeof pos.size === "number"
                        ? pos.size
                        : null;
                    const unrealized =
                      typeof pos.unrealized_pnl === "number"
                        ? pos.unrealized_pnl
                        : typeof pos.pnl === "number"
                        ? pos.pnl
                        : null;

                    return (
                      <tr key={pos.id || symbol || idx} className="border-b border-zinc-900/60">
                        <td className="py-1 pr-2">
                          <span className="text-zinc-100">
                            {symbol.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-1 pr-2 text-right">
                          {size !== null ? (
                            <span className="text-[11px] text-zinc-100">
                              {size.toLocaleString("fr-FR", {
                                maximumFractionDigits: 4,
                              })}
                            </span>
                          ) : (
                            <span className="text-[11px] text-zinc-500">
                              N/A
                            </span>
                          )}
                        </td>
                        <td className="py-1 pr-0 text-right">
                          {unrealized !== null ? (
                            <span
                              className={
                                "text-[11px] " +
                                (unrealized >= 0
                                  ? "text-emerald-400"
                                  : "text-red-400")
                              }
                            >
                              {unrealized.toLocaleString("fr-FR", {
                                style: "currency",
                                currency: "EUR",
                                maximumFractionDigits: 0,
                              })}
                            </span>
                          ) : (
                            <span className="text-[11px] text-zinc-500">
                              N/A
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Risques & pires trades (aperçu)">
          {worstTrades.length === 0 ? (
            <p className="text-xs text-zinc-500">
              Aucun worst trade n’a encore été enregistré. La première
              simulation remplira{" "}
              <code className="bg-zinc-900 px-1 py-0.5 rounded text-[10px]">
                risk/worst_trades.json
              </code>
              .
            </p>
          ) : (
            <ul className="text-xs text-zinc-200 space-y-1.5">
              {worstTrades.slice(0, 4).map((t, idx) => {
                const symbol = t.symbol || t.token || "Asset";
                const loss =
                  typeof t.loss === "number"
                    ? t.loss
                    : typeof t.pnl === "number"
                    ? t.pnl
                    : 0;
                const reason = t.reason || t.note || t.comment || null;

                return (
                  <li
                    key={t.id || symbol || idx}
                    className="flex flex-col border-b border-zinc-900/60 pb-1.5 last:border-b-0 last:pb-0"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-zinc-100">
                        {symbol.toUpperCase()}
                      </span>
                      <span className="text-[11px] text-red-400">
                        {loss.toLocaleString("fr-FR", {
                          style: "currency",
                          currency: "EUR",
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    </div>
                    {reason && (
                      <span className="text-[11px] text-zinc-500 mt-0.5">
                        {reason}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
