// src/pages/Strategy.jsx
// Page stratégie – version statique pour la préproduction

import React from "react";

export default function Strategy() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          Stratégie NSC – Vue d’ensemble
        </h1>
        <p className="text-sm text-zinc-400">
          Résumé des grands blocs stratégiques du bot Nova Star Capital. Cette
          page sera progressivement alimentée par des données temps réel.
        </p>
      </header>

      <section className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-100">
          Périmètre actuel (V2 préprod)
        </h2>
        <ul className="text-xs text-zinc-400 space-y-1 list-disc list-inside">
          <li>Trading crypto spot (Binance / MEXC) avec signaux internes.</li>
          <li>
            Suivi de la profitabilité mensuelle et des pires trades pour ajuster
            le risque.
          </li>
          <li>
            Préparation des modules avancés : market regime, momentum, whales,
            ICO, airdrops…
          </li>
        </ul>
      </section>

      <section className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-100">
          Axes principaux (roadmap proche)
        </h2>
        <div className="grid gap-4 md:grid-cols-3 text-xs text-zinc-400">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-zinc-100">
              1. Market Regime
            </h3>
            <p>
              Adapter automatiquement l’intensité du bot (risk-on / risk-off) en
              fonction du contexte : bull, bear, neutre.
            </p>
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-zinc-100">
              2. Momentum & Signaux
            </h3>
            <p>
              Détection des mouvements forts (prix, volumes, sentiment) avec
              filtres anti &quot;pump &amp; dump&quot;.
            </p>
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-zinc-100">
              3. Gestion du risque
            </h3>
            <p>
              Trailing stops, ventes partielles, blacklist tokens à partir des
              pires trades, et réallocation dynamique.
            </p>
          </div>
        </div>
      </section>

      <section className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-4 space-y-2">
        <h2 className="text-sm font-semibold text-zinc-100">
          Note préproduction
        </h2>
        <p className="text-xs text-zinc-400">
          Pendant cette phase de préproduction, la page Stratégie sert surtout à
          documenter le plan de jeu. Dans les prochaines versions, elle sera
          alimentée par des données consolidées (performances par stratégie,
          pondérations dynamiques, commentaires automatiques LLM, etc.).
        </p>
      </section>
    </div>
  );
}
