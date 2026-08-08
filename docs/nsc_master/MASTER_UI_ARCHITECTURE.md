# NSC — MASTER UI ARCHITECTURE

## Rôle de l’interface

L’interface NSC n’est pas une couche cosmétique.  
Elle fait partie intégrante de la gouvernance, du pilotage patrimonial, de l’explainability et du contrôle opérationnel.

NSC doit être vu comme un cockpit de family office algorithmique.

## Principe général

L’UI doit permettre de suivre :

- la vie complète du programme ;
- la performance des briques ;
- la gouvernance ;
- le risque ;
- l’exécution ;
- le capital ;
- la valeur patrimoniale ;
- les flux ;
- le collatéral ;
- la capacité future de financement.

## Architecture UI officielle

L’interface NSC est structurée en couches :

1. Trading Layer
2. Governance Layer
3. Portfolio / Family Office Layer
4. Treasury Layer
5. Explainability Layer
6. Group Consolidation Layer future

## Pages principales

### Dashboard V4

Rôle :
- vue trading globale ;
- suivi des briques ;
- PnL ;
- expositions ;
- signaux ;
- positions ;
- préprod ;
- santé opérationnelle.

Le Dashboard V4 reste la référence visuelle actuelle.

### Control Room

Rôle :
- gouvernance ;
- allocation ;
- capital control ;
- execution alignment ;
- target vs state ;
- risk / blockers ;
- décisions système.

Le Control Room est la salle de pilotage opérationnelle.

### Family Office Dashboard

Nouvelle page stratégique à créer.

Rôle :
- valeur consolidée de NSC ;
- NAV ;
- valeur d’entreprise patrimoniale ;
- actifs détenus ;
- cash ;
- réserves ;
- dette ;
- collatéral ;
- capacité lombard ;
- trajectoire de compound.

Cette page doit répondre à la question :

“Combien vaut réellement l’écosystème NSC ?”

### Portfolio

Rôle :
- allocation détaillée ;
- target allocation ;
- current allocation ;
- drift ;
- expositions par brique ;
- LT ;
- poches.

### Treasury

Rôle :
- cash ;
- réserves ;
- impôts ;
- BFR ;
- sécurité ;
- flux inter-briques ;
- flux inter-brokers ;
- extraction holding future.

### Risk Console

Rôle :
- risque consolidé ;
- drawdown ;
- kill-switch ;
- survival mode ;
- caps ;
- stress ;
- expositions.

### Explainability Center

Rôle :
- expliquer pourquoi NSC agit ;
- expliquer pourquoi NSC n’agit pas ;
- expliquer les vetos ;
- expliquer les arbitrages de capital.

## KPIs UI officiels

### Trading KPIs

- PnL
- realized PnL
- unrealized PnL
- winrate
- drawdown
- exposure
- open positions
- orders
- candidates
- risk flags

### Family Office KPIs

- total NAV
- enterprise value patrimoniale
- cash
- LT value
- crypto LT
- equities LT
- bonds
- gold
- reserves
- collateral value
- debt capacity
- LTV
- CAGR
- compound multiple
- monthly growth
- treasury health
- survival score

## Objets structurants à afficher

- capital_state.json
- portfolio_target.json
- portfolio_state.json
- rebalance_plan.json
- funding_plan.json
- governance_engine_pro.json
- survival_state.json
- capital_metrics.json
- collateral_state.json futur
- enterprise_value.json futur
- treasury_state.json futur

## Principes UX

1. Explainability first
2. Governance visible everywhere
3. No black box
4. Capital protection before performance
5. Long term patrimonial visibility
6. Trading and patrimony separated but connected
7. Family office orientation
8. Clear distinction between internal core and future commercial platform
9. Dashboard must show value creation, not only trading performance
10. Non-actions and vetos are first-class decisions

## Évolution officielle

À terme, le Dashboard V4 pourra devenir le Trading Dashboard.

Le Family Office Dashboard deviendra progressivement l’écran principal de pilotage stratégique NSC.
