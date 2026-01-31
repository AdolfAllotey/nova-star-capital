// src/pages/Whales.jsx
// Vue Whales & Smart Money à partir de /whales/leaderboard

import React, { useEffect, useState, useMemo } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function Section({ title, description, children }) {
  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-lg font-semibold text-zinc-100 border-b border-zinc-800 pb-1">
          {title}
        </h2>
        {description && (
          <p className="text-xs text-zinc-500 ml-4">{description}</p>
        )}
      </div>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold text-zinc-100">{value}</span>
      {hint && <span className="text-[11px] text-zinc-500 mt-0.5">{hint}</span>}
    </div>
  );
}

function formatPct(val) {
  if (val === null || val === undefined || isNaN(val)) return "–";
  return `${val.toFixed(1)} %`;
}

function formatMoney(val) {
  if (val === null || val === undefined || isNaN(val)) return "–";
  if (Math.abs(val) >= 1_000_000) {
    return `${(val / 1_000_000).toFixed(1)} M€`;
  }
  if (Math.abs(val) >= 1_000) {
    return `${(val / 1_000).toFixed(1)} k€`;
  }
  return `${val.toFixed(0)} €`;
}

export default function WhalesPage() {
  const [whales, setWhales] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filtre simple : top N
  const [limit, setLimit] = useState(20);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(buildUrl("/whales"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();

        const items = Array.isArray(data)
          ? data
          : Array.isArray(data.items)
          ? data.items
          : [];

        if (!cancelled) {
          setWhales(items);
          setUpdatedAt(data.updated_at || null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Error fetching whales leaderboard:", err);
          setError("Impossible de charger le leaderboard des whales.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    if (!whales.length) {
      return {
        count: 0,
        avgWinRate: null,
        avgPnl30d: null,
        bestPnl30d: null,
      };
    }

    const count = whales.length;
    const winRates = whales
      .map((w) => Number(w.win_rate_30d ?? w.win_rate ?? NaN))
      .filter((v) => !isNaN(v));
    const pnl30 = whales
      .map((w) => Number(w.pnl_30d_eur ?? w.pnl_30d ?? NaN))
      .filter((v) => !isNaN(v));

    const avgWinRate =
      winRates.length > 0
        ? winRates.reduce((a, b) => a + b, 0) / winRates.length
        : null;
    const avgPnl30d =
      pnl30.length > 0 ? pnl30.reduce((a, b) => a + b, 0) / pnl30.length : null;
    const bestPnl30d =
      pnl30.length > 0 ? Math.max(...pnl30.map((v) => Number(v))) : null;

    return { count, avgWinRate, avgPnl30d, bestPnl30d };
  }, [whales]);

  const visibleWhales = useMemo(
    () => whales.slice(0, limit),
    [whales, limit]
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-100 mb-1">
          Whales &amp; Smart Money
        </h1>
        <p className="text-sm text-zinc-400">
          Classement des portefeuilles les plus performants suivis par Nova
          Star Capital. Objectif : identifier les{" "}
          <span className="font-medium text-emerald-400">
            leaders à suivre
          </span>{" "}
          et les{" "}
          <span className="font-medium text-amber-400">
            signaux à haute conviction
          </span>
          .
        </p>
        {updatedAt && (
          <p className="text-[11px] text-zinc-500 mt-1">
            Dernière mise à jour : {updatedAt}
          </p>
        )}
      </header>

      {/* Stats globales */}
      <Section
        title="Synthèse Whales"
        description="Vue d'ensemble des portefeuilles suivis (période 30 jours)."
      >
        {loading && !whales.length ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : whales.length === 0 ? (
          <div className="text-sm text-zinc-400">
            Aucun portefeuille whale n’a encore été détecté.  
            L’onglet se remplira automatiquement dès que le module Whales sera
            actif en préproduction.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-sm">
            <Stat
              label="Nombre de whales suivies"
              value={stats.count || "–"}
              hint="Wallets avec historique exploitable"
            />
            <Stat
              label="Win rate moyen (30j)"
              value={
                stats.avgWinRate !== null ? formatPct(stats.avgWinRate * 100) : "–"
              }
              hint="Trades gagnants / total"
            />
            <Stat
              label="P&L moyen 30j"
              value={
                stats.avgPnl30d !== null ? formatMoney(stats.avgPnl30d) : "–"
              }
              hint="P&L réalisé par wallet"
            />
            <Stat
              label="Meilleur P&L 30j"
              value={
                stats.bestPnl30d !== null ? formatMoney(stats.bestPnl30d) : "–"
              }
              hint="Top portefeuille sur 30 jours"
            />
          </div>
        )}
      </Section>

      {/* Leaderboard détaillé */}
      <Section
        title="Leaderboard des whales"
        description="Classement trié par P&L 30 jours. Utilisé par le moteur de copie sélective."
      >
        {loading && !whales.length ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : whales.length === 0 ? (
          <div className="text-sm text-zinc-400">
            Dès que les premiers wallets seront identifiés, le tableau
            apparaîtra automatiquement ici.
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3 text-xs text-zinc-500">
              <span>
                Affichage des{" "}
                <span className="text-zinc-200 font-medium">
                  {visibleWhales.length}
                </span>{" "}
                wallets sur{" "}
                <span className="text-zinc-200 font-medium">
                  {whales.length}
                </span>{" "}
                suivis.
              </span>
              <div className="flex items-center gap-2">
                <span>Limiter à :</span>
                {[10, 20, 50].map((n) => (
                  <button
                    key={n}
                    onClick={() => setLimit(n)}
                    className={`px-2 py-0.5 rounded border text-xs ${
                      limit === n
                        ? "border-emerald-500 text-emerald-400 bg-emerald-500/10"
                        : "border-zinc-700 text-zinc-300 hover:border-zinc-500"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                    <th className="text-left py-2 pr-2">#</th>
                    <th className="text-left py-2 pr-2">Wallet</th>
                    <th className="text-left py-2 pr-2">Tags</th>
                    <th className="text-right py-2 pr-2">P&L 30j</th>
                    <th className="text-right py-2 pr-2">P&L 90j</th>
                    <th className="text-right py-2 pr-2">Win rate 30j</th>
                    <th className="text-right py-2 pl-2">Volume 30j</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleWhales.map((w, idx) => {
                    const rank = idx + 1;
                    const address =
                      w.address || w.wallet || w.id || "Adresse inconnue";
                    const tags =
                      Array.isArray(w.tags) && w.tags.length > 0
                        ? w.tags
                        : w.cluster
                        ? [w.cluster]
                        : [];

                    const pnl30 =
                      Number(w.pnl_30d_eur ?? w.pnl_30d ?? NaN) || null;
                    const pnl90 =
                      Number(w.pnl_90d_eur ?? w.pnl_90d ?? NaN) || null;
                    const winRate =
                      Number(w.win_rate_30d ?? w.win_rate ?? NaN) || null;
                    const vol30 =
                      Number(w.volume_30d_eur ?? w.volume_30d ?? NaN) || null;

                    return (
                      <tr
                        key={w.id || w.address || w.wallet || rank}
                        className="border-b border-zinc-800/60 hover:bg-zinc-900/60"
                      >
                        <td className="py-2 pr-2 text-xs text-zinc-500">
                          {rank}
                        </td>
                        <td className="py-2 pr-2">
                          <div className="flex flex-col">
                            <span className="text-xs font-mono text-zinc-300 truncate max-w-[220px]">
                              {address}
                            </span>
                            {w.label && (
                              <span className="text-[11px] text-zinc-500">
                                {w.label}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 pr-2">
                          <div className="flex flex-wrap gap-1">
                            {tags.length > 0 ? (
                              tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="px-1.5 py-0.5 rounded-full text-[11px] bg-zinc-800 text-zinc-300 border border-zinc-700"
                                >
                                  {tag}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-zinc-500">–</span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 pr-2 text-right text-zinc-100">
                          {pnl30 !== null ? formatMoney(pnl30) : "–"}
                        </td>
                        <td className="py-2 pr-2 text-right text-zinc-100">
                          {pnl90 !== null ? formatMoney(pnl90) : "–"}
                        </td>
                        <td className="py-2 pr-2 text-right">
                          {winRate !== null ? (
                            <span
                              className={
                                winRate >= 0.6
                                  ? "text-emerald-400"
                                  : winRate <= 0.4
                                  ? "text-red-400"
                                  : "text-zinc-200"
                              }
                            >
                              {formatPct(winRate * 100)}
                            </span>
                          ) : (
                            <span className="text-zinc-500">–</span>
                          )}
                        </td>
                        <td className="py-2 pl-2 text-right text-zinc-100">
                          {vol30 !== null ? formatMoney(vol30) : "–"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
