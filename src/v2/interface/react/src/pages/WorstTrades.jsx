// src/pages/WorstTrades.jsx
// Vue des pires trades à partir de /worst-trades

import React, { useEffect, useMemo, useState } from "react";

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

function formatMoney(val) {
  if (val === null || val === undefined || isNaN(val)) return "–";
  const abs = Math.abs(val);
  let txt;
  if (abs >= 1_000_000) {
    txt = `${(abs / 1_000_000).toFixed(1)} M€`;
  } else if (abs >= 1_000) {
    txt = `${(abs / 1_000).toFixed(1)} k€`;
  } else {
    txt = `${abs.toFixed(0)} €`;
  }
  return val < 0 ? `- ${txt}` : txt;
}

function formatDate(d) {
  if (!d) return "–";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return d;
  return dt.toLocaleString();
}

export default function WorstTradesPage() {
  const [trades, setTrades] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Limite d’affichage, au cas où la liste est longue
  const [limit, setLimit] = useState(20);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(buildUrl("/worst-trades"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();

        // Tolérant: soit {items: [...]}, soit un array direct
        const items = Array.isArray(data)
          ? data
          : Array.isArray(data.items)
          ? data.items
          : [];

        if (!cancelled) {
          setTrades(items);
          setUpdatedAt(data.updated_at || null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Error fetching worst trades:", err);
          setError(
            "Impossible de charger les pires trades. Vérifie l’API /worst-trades."
          );
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
    if (!trades.length) {
      return {
        count: 0,
        totalLoss: null,
        avgLoss: null,
        worstLoss: null,
      };
    }

    // On part du principe que loss_eur est négatif ou que pnl_eur < 0
    const losses = trades
      .map((t) => {
        const loss =
          Number(
            t.loss_eur ??
              t.pnl_eur ??
              t.pnl ??
              (t.realized_pnl_eur ?? t.realized_pnl)
          ) || 0;
        return loss;
      })
      // On ne garde que les pertes (valeurs < 0)
      .filter((v) => !Number.isNaN(v) && v < 0);

    if (!losses.length) {
      return {
        count: trades.length,
        totalLoss: 0,
        avgLoss: 0,
        worstLoss: 0,
      };
    }

    const totalLoss = losses.reduce((a, b) => a + b, 0);
    const avgLoss = totalLoss / losses.length;
    const worstLoss = Math.min(...losses);

    return {
      count: trades.length,
      totalLoss,
      avgLoss,
      worstLoss,
    };
  }, [trades]);

  const visibleTrades = useMemo(
    () => trades.slice(0, limit),
    [trades, limit]
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-100 mb-1">
          Pires trades &amp; zones de risque
        </h1>
        <p className="text-sm text-zinc-400">
          Surveillance des{" "}
          <span className="font-medium text-red-400">plus grosses pertes</span>{" "}
          pour ajuster les règles du bot, affiner les blacklists et renforcer le
          contrôle du risque.
        </p>
        {updatedAt && (
          <p className="text-[11px] text-zinc-500 mt-1">
            Dernière mise à jour : {updatedAt}
          </p>
        )}
      </header>

      {/* Synthèse */}
      <Section
        title="Synthèse des pires trades"
        description="Vue agrégée des pertes réalisées utilisées par le module de risk management."
      >
        {loading && !trades.length ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : trades.length === 0 ? (
          <div className="text-sm text-zinc-400">
            Aucun trade n’a encore été analysé.  
            Dès que la simulation / le réel tournera, les{" "}
            <span className="font-medium text-red-400">
              pires trades apparaîtront ici
            </span>{" "}
            et alimenteront la blacklist.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-sm">
            <Stat
              label="Nombre de trades analysés"
              value={stats.count || "–"}
              hint="Base de calcul pour la synthèse"
            />
            <Stat
              label="Perte totale (pire trades)"
              value={
                stats.totalLoss !== null ? formatMoney(stats.totalLoss) : "–"
              }
              hint="Somme des pertes sélectionnées"
            />
            <Stat
              label="Perte moyenne"
              value={stats.avgLoss !== null ? formatMoney(stats.avgLoss) : "–"}
              hint="Moyenne par trade perdant"
            />
            <Stat
              label="Plus grosse perte"
              value={
                stats.worstLoss !== null ? formatMoney(stats.worstLoss) : "–"
              }
              hint="Trade qui impacte le plus le P&L"
            />
          </div>
        )}
      </Section>

      {/* Tableau détaillé */}
      <Section
        title="Détail des pires trades"
        description="Liste triée des pires pertes. Sert de base au module worst_trade_analyzer & blacklist."
      >
        {loading && !trades.length ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : trades.length === 0 ? (
          <div className="text-sm text-zinc-400">
            Dès que le bot aura exécuté des trades perdants significatifs,
            l’onglet montrera{" "}
            <span className="font-medium text-red-400">
              les cas à ne plus reproduire
            </span>{" "}
            (tokens, taille, timing…).
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3 text-xs text-zinc-500">
              <span>
                Affichage des{" "}
                <span className="text-zinc-200 font-medium">
                  {visibleTrades.length}
                </span>{" "}
                pires trades sur{" "}
                <span className="text-zinc-200 font-medium">
                  {trades.length}
                </span>{" "}
                analysés.
              </span>
              <div className="flex items-center gap-2">
                <span>Limiter à :</span>
                {[5, 10, 20, 50].map((n) => (
                  <button
                    key={n}
                    onClick={() => setLimit(n)}
                    className={`px-2 py-0.5 rounded border text-xs ${
                      limit === n
                        ? "border-red-500 text-red-400 bg-red-500/10"
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
                    <th className="text-left py-2 pr-2">Token</th>
                    <th className="text-left py-2 pr-2">Side</th>
                    <th className="text-right py-2 pr-2">Montant</th>
                    <th className="text-right py-2 pr-2">Prix entrée</th>
                    <th className="text-right py-2 pr-2">Prix sortie</th>
                    <th className="text-right py-2 pr-2">P&L (€)</th>
                    <th className="text-left py-2 pr-2">Stratégie</th>
                    <th className="text-left py-2 pr-2">Exchange</th>
                    <th className="text-left py-2 pl-2">Ouvert / Fermé</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleTrades.map((t, idx) => {
                    const token = t.token || t.symbol || "N/A";
                    const side = (t.side || "").toUpperCase();
                    const amount = Number(t.amount ?? t.size ?? NaN);
                    const entry = Number(
                      t.entry_price_eur ??
                        t.entry_price ??
                        t.price_entry_eur ??
                        t.price_eur ??
                        NaN
                    );
                    const exit = Number(
                      t.exit_price_eur ??
                        t.exit_price ??
                        t.price_exit_eur ??
                        t.exit_price_eur ??
                        NaN
                    );
                    const pnl =
                      Number(
                        t.loss_eur ??
                          t.pnl_eur ??
                          t.pnl ??
                          t.realized_pnl_eur ??
                          t.realized_pnl ??
                          NaN
                      ) || null;

                    const openedAt = t.opened_at || t.entry_time || t.timestamp;
                    const closedAt = t.closed_at || t.exit_time;

                    return (
                      <tr
                        key={t.id || `${token}-${idx}`}
                        className="border-b border-zinc-800/60 hover:bg-zinc-900/60"
                      >
                        <td className="py-2 pr-2">
                          <div className="flex flex-col">
                            <span className="text-sm text-zinc-100">
                              {token}
                            </span>
                            {t.reason && (
                              <span className="text-[11px] text-zinc-500">
                                {t.reason}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 pr-2">
                          <span
                            className={
                              side === "SELL"
                                ? "text-red-400 text-xs font-semibold"
                                : "text-zinc-300 text-xs"
                            }
                          >
                            {side || "–"}
                          </span>
                        </td>
                        <td className="py-2 pr-2 text-right text-zinc-100">
                          {Number.isNaN(amount)
                            ? "–"
                            : amount.toLocaleString(undefined, {
                                maximumFractionDigits: 6,
                              })}
                        </td>
                        <td className="py-2 pr-2 text-right text-zinc-100">
                          {Number.isNaN(entry)
                            ? "–"
                            : `${entry.toFixed(4)} €`}
                        </td>
                        <td className="py-2 pr-2 text-right text-zinc-100">
                          {Number.isNaN(exit) ? "–" : `${exit.toFixed(4)} €`}
                        </td>
                        <td className="py-2 pr-2 text-right">
                          {pnl !== null ? (
                            <span className="text-red-400 font-semibold">
                              {formatMoney(pnl)}
                            </span>
                          ) : (
                            <span className="text-zinc-500">–</span>
                          )}
                        </td>
                        <td className="py-2 pr-2 text-left text-xs text-zinc-200">
                          {t.strategy || "–"}
                        </td>
                        <td className="py-2 pr-2 text-left text-xs text-zinc-200">
                          {(t.exchange || "").toUpperCase() || "–"}
                        </td>
                        <td className="py-2 pl-2 text-left text-xs text-zinc-300">
                          <div className="flex flex-col">
                            <span>{openedAt ? formatDate(openedAt) : "–"}</span>
                            <span className="text-[11px] text-zinc-500">
                              {closedAt ? `Fermé : ${formatDate(closedAt)}` : ""}
                            </span>
                          </div>
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
