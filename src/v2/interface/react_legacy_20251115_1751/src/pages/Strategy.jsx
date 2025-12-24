// src/pages/Strategy.jsx
import React from "react";

function Card({ title, children }) {
  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
      {children}
    </div>
  );
}

function Pill({ children }) {
  return (
    <span className="inline-flex items-center rounded-full border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-[11px] text-zinc-200">
      {children}
    </span>
  );
}

export default function Strategy() {
  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Stratégie du bot</h1>
          <p className="text-sm text-zinc-400">
            Vue synthétique de la logique Nova Star Capital V2 : régimes de
            marché, poches de capital et moteurs de décision.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Pill>Préproduction</Pill>
          <Pill>Multi-stratégies</Pill>
          <Pill>Market regime aware</Pill>
        </div>
      </div>

      {/* Grille principale */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Colonne 1 : Régimes de marché */}
        <div className="flex flex-col gap-3">
          <Card title="Régimes de marché (Market Regime Detector)">
            <p className="text-xs text-zinc-300">
              Le bot adapte son intensité selon le régime détecté :
            </p>
            <ul className="mt-2 text-xs text-zinc-200 space-y-1.5 list-disc list-inside">
              <li>
                <span className="font-semibold text-emerald-400">Bull</span> :
                levier sur le trading, suivi de tendance, prise de profits
                progressive.
              </li>
              <li>
                <span className="font-semibold text-yellow-300">Neutre</span> :
                exposition modérée, focus sur signaux à fort conviction,
                réduction du turnover.
              </li>
              <li>
                <span className="font-semibold text-red-400">Bear</span> :
                réduction du risque, allègement progressif, priorité au long
                terme et à la trésorerie.
              </li>
            </ul>
          </Card>

          <Card title="Répartition du capital par régime (rappel)">
            <p className="text-xs text-zinc-300 mb-2">
              Exemple de répartition des gains nets (après IS), selon le régime
              global :
            </p>
            <div className="text-[11px] overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-400">
                    <th className="text-left py-1 pr-2">Régime</th>
                    <th className="text-right py-1 pr-2">Trading</th>
                    <th className="text-right py-1 pr-2">Long Terme</th>
                    <th className="text-right py-1 pr-2">BFR</th>
                    <th className="text-right py-1 pr-0">Sécurité</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-zinc-900">
                    <td className="py-1 pr-2 text-emerald-400 font-medium">
                      Bull
                    </td>
                    <td className="py-1 pr-2 text-right">65 %</td>
                    <td className="py-1 pr-2 text-right">25 %</td>
                    <td className="py-1 pr-2 text-right">7 %</td>
                    <td className="py-1 pr-0 text-right">3 %</td>
                  </tr>
                  <tr>
                    <td className="py-1 pr-2 text-red-400 font-medium">Bear</td>
                    <td className="py-1 pr-2 text-right">25 %</td>
                    <td className="py-1 pr-2 text-right">50 %</td>
                    <td className="py-1 pr-2 text-right">5 %</td>
                    <td className="py-1 pr-0 text-right">20 %</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11px] text-zinc-500">
              Ces ratios sont appliqués périodiquement, au-delà d’un seuil de
              réallocation (ex. 5 k€), pour éviter le sur-trading.
            </p>
          </Card>
        </div>

        {/* Colonne 2 : Moteurs de décision */}
        <div className="flex flex-col gap-3">
          <Card title="Moteurs de décision (Signals & Scoring)">
            <ul className="text-xs text-zinc-200 space-y-1.5 list-disc list-inside">
              <li>
                <span className="font-semibold">Momentum scoring</span> :
                variation 15/60 min, volatilité vs moyenne 24h, distance MA20,
                proximité des plus hauts récents.
              </li>
              <li>
                <span className="font-semibold">Sentiment & flux</span> :
                Telegram, Twitter, Reddit, early pump score, qualité des
                sources.
              </li>
              <li>
                <span className="font-semibold">Whales & KOLs</span> :
                comportements des wallets clés et signaux “smart money”.
              </li>
              <li>
                <span className="font-semibold">
                  Worst trades & blacklist
                </span>{" "}
                : les pires trades simulés alimentent des listes de risques pour
                éviter de répéter les mêmes erreurs.
              </li>
            </ul>
          </Card>

          <Card title="Gestion des positions (Position Manager)">
            <ul className="text-xs text-zinc-200 space-y-1.5 list-disc list-inside">
              <li>
                Ventes progressives : prises partielles de profit (paliers
                +15&nbsp;% / +30&nbsp;%, etc.).
              </li>
              <li>
                Trailing stop basé sur{" "}
                <span className="font-mono">ATR(14)</span>, avec min / max
                (ex. 6–18&nbsp;%) et mode adaptatif en cas de spike de
                volatilité.
              </li>
              <li>
                Logique de{" "}
                <span className="font-semibold">kill-switch</span> et pauses en
                cas de drawdown anormal ou d’anomalies marché.
              </li>
            </ul>
          </Card>

          <Card title="Sélecteur de stratégie (Strategy Selector)">
            <p className="text-xs text-zinc-300">
              Un module de sélection (V2.5+) compare les performances récentes
              des différentes approches ({'"'}Sniper{'"'}, {"'"}Whales{'"'},
              {" "}
              {"'"}Momentum{'"'}) sur une fenêtre glissante (ex. 30 jours).
            </p>
            <p className="mt-2 text-[11px] text-zinc-400">
              L’objectif est d’augmenter la pondération des stratégies qui
              fonctionnent dans le régime actuel, tout en plafonnant le risque
              par stratégie.
            </p>
          </Card>
        </div>

        {/* Colonne 3 : Poches & Long Terme */}
        <div className="flex flex-col gap-3">
          <Card title="Poches internes du bot">
            <ul className="text-xs text-zinc-200 space-y-1.5 list-disc list-inside">
              <li>
                <span className="font-semibold">Scalp / Momentum</span> :
                exploitation des mouvements courts, forte réactivité, taille
                de position maîtrisée.
              </li>
              <li>
                <span className="font-semibold">Swing / Tendance</span> :
                positions de quelques jours à quelques semaines, basées sur
                trend + sentiment.
              </li>
              <li>
                <span className="font-semibold">Long Terme</span> :
                réinvestissement automatisé dans un panier de cryptos majeures.
              </li>
              <li>
                <span className="font-semibold">Sécurité & BFR</span> :
                réserve de cash / stablecoins pour absorber les chocs et saisir
                les opportunités.
              </li>
            </ul>
          </Card>

          <Card title="Poche long terme (rappel de la répartition)">
            <p className="text-[11px] text-zinc-300 mb-2">
              Exemple de répartition de la poche long terme (37&nbsp;% des
              gains nets, à adapter au fil du temps) :
            </p>
            <ul className="text-[11px] text-zinc-200 space-y-1.5 list-disc list-inside">
              <li>40 % — Bitcoin (BTC)</li>
              <li>25 % — Ethereum (ETH)</li>
              <li>15 % — Solana (SOL)</li>
              <li>7 % — BNB</li>
              <li>5 % — XRP</li>
              <li>5 % — Avalanche (AVAX)</li>
              <li>3 % — Polygon (MATIC)</li>
            </ul>
          </Card>

          <Card title="Évolution future (V3+)">
            <p className="text-[11px] text-zinc-400">
              Les prochaines versions étendront cette logique aux{" "}
              <span className="font-semibold">actions offensives</span> et aux{" "}
              <span className="font-semibold">options US</span> (Nasdaq, S&amp;P
              500), avec des poches dédiées et des règles similaires de
              réallocation dynamique.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
