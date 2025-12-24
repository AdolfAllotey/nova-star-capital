// src/pages/OpenPositions.jsx
// Vue des positions ouvertes à partir de /open-positions

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

function formatCurrency(v) {
  if (v === null || v === undefined || isNaN(v)) return "–";
  return `${v.toFixed(2)} €`;
}

function formatNumber(v, decimals = 4) {
  if (v === null || v === undefined || isNaN(v)) return "–";
  return v.toFixed(decimals);
}

function formatDate(value) {
  if (!value) return "–";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

export default function OpenPositionsPage() {
  const [data, setData] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(buildUrl("/open-positions"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          // tolérant: soit { items: [...] }, soit [...]
          const list = Array.isArray(json)
            ? json
            : Array.isArray(json.items)
            ? json.items
            : [];
          setItems(list);
        }
      } catch (err) {
        console.error("Error fetching open positions:", err);
        if (!cancelled) {
          setError(
            "Impossible de charger les positions ouvertes. Vérifie l’API /open-positions."
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

  const aggregates = useMemo(() => {
    if (!items.length) {
      return {
        totalNotional: null,
        positionsCount: 0,
        exchangesCount: 0,
      };
    }

    let totalNotional = 0;
    const exchanges = new Set();

    for (const p of items) {
      const size =
        typeof p.size === "number" ? p.size : Number(p.size ?? NaN);
      const avgPrice =
        typeof p.avg_entry_price_eur === "number"
          ? p.avg_entry_price_eur
          : Number(p.avg_entry_price_eur ?? NaN);
      if (!isNaN(size) && !isNaN(avgPrice)) {
        totalNotional += size * avgPrice;
      }
      if (p.exchange) {
        exchanges.add(String(p.exchange).toUpperCase());
      }
    }

    return {
      totalNotional,
      positionsCount: items.length,
      exchangesCount: exchanges.size,
    };
  }, [items]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-100 mb-1">
          Positions ouvertes
        </h1>
        <p className="text-sm text-zinc-400">
          Vue en temps quasi-réel des positions maintenues par le bot Nova Star
          Capital (préprod). Cette page lit directement les données du
          <code className="mx-1 px-1 py-0.5 rounded bg-zinc-900/80 border border-zinc-800 text-[11px]">
            open_positions.json
          </code>{" "}
          agrégé côté API.
        </p>
      </header>

      {/* Synthèse */}
      <Section
        title="Synthèse"
        description="Aperçu global du risque engagé par le bot sur les différents exchanges."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !items.length ? (
          <div className="text-sm text-zinc-400">
            Aucune position ouverte pour le moment.  
            Dès que le bot prendra une première position, elle apparaîtra
            automatiquement ici.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Stat
              label="Nombre de positions"
              value={aggregates.positionsCount}
              hint="Total de lignes en portefeuille"
            />
            <Stat
              label="Notionnel total"
              value={formatCurrency(aggregates.totalNotional)}
              hint="Somme (taille × prix d’entrée moyen)"
            />
            <Stat
              label="Exchanges"
              value={aggregates.exchangesCount}
              hint="Nombre de plateformes utilisées (Binance, MEXC…)"
            />
          </div>
        )}
      </Section>

      {/* Détail positions */}
      <Section
        title="Détail des positions"
        description="Liste détaillée de chaque position, avec taille, prix moyen et timestamps."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !items.length ? (
          <div className="text-sm text-zinc-400">
            Aucune position à afficher pour le moment.  
            En préprod, tu peux vérifier que{" "}
            <span className="font-medium text-emerald-400">
              position_manager
            </span>{" "}
            met bien à jour <code>open_positions.json</code> après les entrées /
            sorties de trades.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="text-left py-2 pr-2">Token</th>
                  <th className="text-left py-2 pr-2">Exchange</th>
                  <th className="text-right py-2 pr-2">Taille</th>
                  <th className="text-right py-2 pr-2">
                    Prix moyen d’entrée (€)
                  </th>
                  <th className="text-right py-2 pr-2">
                    Valeur théorique (≈) (€)
                  </th>
                  <th className="text-right py-2 pr-2">Ouverte le</th>
                  <th className="text-right py-2 pl-2">Dernière mise à jour</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p, idx) => {
                  const token = (p.token || p.symbol || p.id || "N/A").toUpperCase();
                  const exchange = (p.exchange || "–").toUpperCase();
                  const size =
                    typeof p.size === "number"
                      ? p.size
                      : Number(p.size ?? NaN);
                  const avgPrice =
                    typeof p.avg_entry_price_eur === "number"
                      ? p.avg_entry_price_eur
                      : Number(p.avg_entry_price_eur ?? NaN);

                  const notional =
                    !isNaN(size) && !isNaN(avgPrice) ? size * avgPrice : NaN;

                  return (
                    <tr
                      key={`${token}-${exchange}-${idx}`}
                      className="border-b border-zinc-800/60 hover:bg-zinc-900/60"
                    >
                      <td className="py-2 pr-2 text-zinc-100">{token}</td>
                      <td className="py-2 pr-2 text-zinc-300">{exchange}</td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatNumber(isNaN(size) ? null : size, 6)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatCurrency(isNaN(avgPrice) ? null : avgPrice)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatCurrency(isNaN(notional) ? null : notional)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-300">
                        {formatDate(p.opened_at || p.openedAt)}
                      </td>
                      <td className="py-2 pl-2 text-right text-zinc-300">
                        {formatDate(p.last_update || p.lastUpdate)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Explications */}
      <Section
        title="Rôle de cette vue en préproduction"
        description="Contrôles à faire avant de passer en mode réel."
      >
        <div className="space-y-2 text-sm text-zinc-300">
          <p>
            Cette page te sert à vérifier que{" "}
            <span className="font-medium text-emerald-400">
              le tracking des positions ouvertes
            </span>{" "}
            fonctionne correctement : chaque entrée de trade devrait créer /
            augmenter une ligne, et chaque sortie fermer ou réduire la taille.
          </p>
          <p>
            En préprod, tu peux comparer cette vue aux fichiers{" "}
            <code>trade_simulation.json</code>,{" "}
            <code>open_positions.json</code> et <code>exit_events.json</code>{" "}
            pour t’assurer que la logique de{" "}
            <span className="font-medium">position_manager.py</span> se
            comporte comme prévu.
          </p>
          <p className="text-xs text-zinc-500">
            Une fois en production, cette page sera l’un des écrans
            “salle de marché” principaux, avec un rafraîchissement régulier et
            la synchronisation avec les exchanges (Binance, MEXC, etc.).
          </p>
        </div>
      </Section>
    </div>
  );
}
