// src/pages/LiveSimulation.jsx
import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

function Card({ title, children }) {
  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function StatRow({ label, value }) {
  return (
    <div className="flex items-center justify-between text-xs text-zinc-300">
      <span className="text-zinc-400">{label}</span>
      <span className="font-mono text-zinc-100">{value}</span>
    </div>
  );
}

export default function LiveSimulation() {
  const [lastUpdate, setLastUpdate] = useState(null);
  const [regime, setRegime] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [topMovers, setTopMovers] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [profitability, setProfitability] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);

  // Tick toutes les 5 secondes pour simuler un "live"
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 5000);
    return () => clearInterval(id);
  }, []);

  // Charge les données à chaque tick + au premier render
  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setError(null);

        const [
          regimeRes,
          sentimentRes,
          topMoversRes,
          openPositionsRes,
          profitabilityRes,
        ] = await Promise.allSettled([
          api.getMarketRegime(),
          api.getSentimentOverview(),
          api.getTopMovers(),
          api.getOpenPositions(),
          api.getMonthlyProfitability(),
        ]);

        if (!alive) return;

        if (regimeRes.status === "fulfilled") {
          setRegime(regimeRes.value);
        }
        if (sentimentRes.status === "fulfilled") {
          setSentiment(sentimentRes.value);
        }
        if (topMoversRes.status === "fulfilled") {
          setTopMovers(topMoversRes.value?.items || []);
        }
        if (openPositionsRes.status === "fulfilled") {
          setOpenPositions(openPositionsRes.value?.positions || []);
        }
        if (profitabilityRes.status === "fulfilled") {
          setProfitability(profitabilityRes.value);
        }

        setLastUpdate(new Date().toISOString());
      } catch (err) {
        console.error("[LiveSimulation] Erreur globale:", err);
        if (!alive) return;
        setError(err?.message || "Erreur lors du rafraîchissement des données.");
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [tick]);

  const regimeLabel =
    regime?.mode === "bull"
      ? "Bull market"
      : regime?.mode === "bear"
      ? "Bear market"
      : "Neutre";

  const sentimentScore =
    sentiment?.score != null ? sentiment.score.toFixed(2) : "—";

  const lastMonthPnl =
    profitability?.items && profitability.items.length > 0
      ? profitability.items[profitability.items.length - 1]
      : null;

  return (
    <div className="flex flex-col gap-4">
      {/* Titre + méta */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Live Simulation</h1>
          <p className="text-sm text-zinc-400">
            Vue temps réel simplifiée du bot Nova Star Capital (préprod).
          </p>
          {lastUpdate && (
            <p className="text-xs text-zinc-500 mt-1">
              Dernier rafraîchissement :{" "}
              {new Date(lastUpdate).toLocaleTimeString("fr-FR")}
            </p>
          )}
        </div>

        <div className="text-xs text-zinc-500">
          Rafraîchissement auto toutes les{" "}
          <span className="font-mono text-zinc-200">5 sec</span>
        </div>
      </div>

      {/* Erreur globale éventuelle */}
      {error && (
        <div className="text-sm text-red-400">
          Erreur : <span className="font-mono">{error}</span>
        </div>
      )}

      {/* Grille principale */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Colonne 1 : Regime + Sentiment */}
        <div className="flex flex-col gap-3">
          <Card title="Market Regime">
            <div className="text-sm">
              <span className="font-semibold text-zinc-100">
                {regimeLabel}
              </span>
              {regime && (
                <span className="ml-2 text-xs text-zinc-500">
                  score: {regime.score?.toFixed?.(2) ?? regime.score ?? "—"}
                </span>
              )}
            </div>
            <StatRow
              label="Source"
              value={regime?.source || "default / préprod"}
            />
          </Card>

          <Card title="Sentiment global">
            <StatRow label="Score" value={sentimentScore} />
            <StatRow
              label="Mode"
              value={sentiment?.mode || sentiment?.label || "—"}
            />
            <StatRow
              label="Dernière mise à jour"
              value={
                sentiment?.updated_at
                  ? new Date(sentiment.updated_at).toLocaleTimeString("fr-FR")
                  : "—"
              }
            />
          </Card>

          <Card title="PNL récent (mensuel)">
            {lastMonthPnl ? (
              <>
                <StatRow
                  label="Mois"
                  value={`${lastMonthPnl.year}-${String(
                    lastMonthPnl.month
                  ).padStart(2, "0")}`}
                />
                <StatRow
                  label="PNL net"
                  value={`${(lastMonthPnl.pnl_net_eur || 0).toFixed(0)} €`}
                />
                <StatRow
                  label="Coûts"
                  value={`${(lastMonthPnl.costs_eur || 0).toFixed(0)} €`}
                />
              </>
            ) : (
              <div className="text-xs text-zinc-400">
                Pas encore de données de rentabilité.
              </div>
            )}
          </Card>
        </div>

        {/* Colonne 2 : Open positions */}
        <div className="flex flex-col gap-3">
          <Card title={`Positions ouvertes (${openPositions.length})`}>
            {openPositions.length === 0 ? (
              <div className="text-xs text-zinc-400">
                Aucune position ouverte pour le moment.
              </div>
            ) : (
              <div className="max-h-64 overflow-auto text-xs">
                <table className="w-full border-collapse">
                  <thead className="text-zinc-400 border-b border-zinc-800">
                    <tr>
                      <th className="text-left py-1 pr-2">Token</th>
                      <th className="text-right py-1 pr-2">Px entrée</th>
                      <th className="text-right py-1 pr-2">Px actuel</th>
                      <th className="text-right py-1 pr-2">PNL %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openPositions.map((p, idx) => (
                      <tr
                        key={p.id || p.symbol || idx}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-1 pr-2 font-mono text-zinc-100">
                          {p.symbol || p.token || "—"}
                        </td>
                        <td className="py-1 pr-2 text-right text-zinc-200">
                          {p.entry_price != null
                            ? Number(p.entry_price).toFixed(4)
                            : "—"}
                        </td>
                        <td className="py-1 pr-2 text-right text-zinc-200">
                          {p.current_price != null
                            ? Number(p.current_price).toFixed(4)
                            : "—"}
                        </td>
                        <td className="py-1 pr-2 text-right">
                          {p.pnl_pct != null ? (
                            <span
                              className={
                                Number(p.pnl_pct) >= 0
                                  ? "text-emerald-400"
                                  : "text-red-400"
                              }
                            >
                              {Number(p.pnl_pct).toFixed(1)} %
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* Colonne 3 : Top Movers (vue live simple) */}
        <div className="flex flex-col gap-3">
          <Card title={`Top Movers (snapshot)`}>
            {topMovers.length === 0 ? (
              <div className="text-xs text-zinc-400">
                Pas encore de données de marché.
              </div>
            ) : (
              <div className="max-h-64 overflow-auto text-xs">
                <table className="w-full border-collapse">
                  <thead className="text-zinc-400 border-b border-zinc-800">
                    <tr>
                      <th className="text-left py-1 pr-2">Token</th>
                      <th className="text-right py-1 pr-2">Δ 24h %</th>
                      <th className="text-right py-1 pr-2">Cap. (M$)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topMovers.slice(0, 15).map((t, idx) => (
                      <tr
                        key={t.id || t.symbol || idx}
                        className="border-b border-zinc-900/60 last:border-0"
                      >
                        <td className="py-1 pr-2">
                          <span className="font-mono text-zinc-100">
                            {t.symbol || "—"}
                          </span>
                          <span className="ml-1 text-zinc-500">
                            {t.name || ""}
                          </span>
                        </td>
                        <td className="py-1 pr-2 text-right">
                          <span
                            className={
                              Number(t.price_change_percentage_24h || 0) >= 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }
                          >
                            {t.price_change_percentage_24h != null
                              ? t.price_change_percentage_24h.toFixed(1)
                              : "—"}{" "}
                            %
                          </span>
                        </td>
                        <td className="py-1 pr-2 text-right text-zinc-200">
                          {t.market_cap
                            ? (t.market_cap / 1_000_000).toFixed(1)
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
