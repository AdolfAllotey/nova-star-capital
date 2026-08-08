# NSC — ROADMAP MASTER

## Priorité 1

Finaliser le Capital Brain :
- Portfolio Governor
- Policy Layer
- Funding Engine
- Rebalance Plan
- Capital State réel

## Priorité 2

Aligner la préprod globale avec la future production :
- crypto en simulation réaliste
- actions offensives en simulation réaliste
- toutes les briques raccordées au Portfolio Engine

## Priorité 3

Formaliser les policy files :
- allocation_policy.json
- funding_policy.json
- long_term_policy.json
- risk_policy.json
- broker_policy.json

## Priorité 4

Stress tests :
- crash crypto
- krach actions
- stress cross-asset
- API down
- stale data
- mauvais execution plan

## Priorité 5

Explainability Layer :
- pourquoi NSC agit
- pourquoi NSC n’agit pas
- quels risques sont actifs
- quels vetos sont déclenchés

---

# MISE À JOUR MASTER NSC – JUIN 2026 – RISK / GOVERNANCE / CRYPTO

## Synthèse

Refonte et alignement réalisés sur :
- Risk Console
- Protection
- Governance
- Dashboard / Risk / Protection / Governance
- Brique Crypto
- Daily Review
- Suivi manuel Bitpanda

Objectif : rendre NSC plus institutionnel, cohérent et fidèle aux artefacts réels de préproduction.

## Risk Console / Protection / Governance

La Risk Console a été corrigée pour éviter les faux niveaux HIGH / CRITICAL lorsque :
- aucun hard block n’est actif ;
- le kill switch est OFF ;
- la gouvernance est saine ;
- l’exécution est en SIMULATED_ONLY.

Nouvelle séparation :
- risque portefeuille : drift, allocation, exposition ;
- risque gouvernance : hard block, kill switch, blocage d’exécution.

CRITICAL est désormais réservé aux vrais blocages.

Les pages Protection et Governance ont été refondues en cockpits institutionnels :
- Protection Command Center ;
- Governance Command Center ;
- états lisibles : PROTECTED, CONTROLLED, SIMULATED_ONLY.

## Cohérence UI globale

Lecture actuelle attendue :
- Dashboard : RISK_ON ;
- Risk Console : WATCH si drift crypto élevé ;
- Protection : PROTECTED ;
- Governance : CONTROLLED ;
- Execution : SIMULATED_ONLY ;
- Kill Switch : OFF.

## Audit Crypto

La principale source de drift venait de la sous-exposition crypto.

Constat initial :
- cible crypto : environ 37 % ;
- exposition réelle observée : environ 11,6 % ;
- drift : environ 25 %.

Conclusion : le problème venait surtout d’un manque de signaux exploitables et d’un sizing trop prudent, pas de la gouvernance.

## Sizing Crypto Préproduction

Ajustement progressif :
- budget crypto simulé : 4 000 € ;
- max positions réduit de 10 à 6 ;
- capital par trade augmenté de 400 € à 666,67 €.

But :
- remonter progressivement l’exposition crypto ;
- éviter un saut brutal vers la cible complète ;
- rester en PREPROD / SIMULATED_ONLY.

## Corrections techniques Crypto

Corrections réalisées :
- `notional_eur` devient la source de vérité en PREPROD ;
- suppression de l’inflation EUR → USDT dans le notional simulé ;
- synchronisation des champs `notional`, `notional_eur`, `qty`, `price_ref` ;
- correction du `position_manager` pour préférer `notional_eur` ;
- réalignement des positions papier avec le sizing réel ;
- downscale automatique des positions simulées trop élevées ;
- ajout du stop-loss cooldown 12h ;
- exclusion des `stale_plan_cleanup` des statistiques réelles de performance ;
- amélioration du `nsc-daily-review`.

## Social Momentum Fallback

Ajout d’un fallback social contrôlé lorsque moins de 3 signaux market momentum sont disponibles.

Règles :
- score social minimum : 60 ;
- source_count minimum : 2 ;
- pas de cooldown stop-loss actif ;
- complète uniquement les places manquantes.

Premier résultat :
- CREAM ;
- LINK ;
- PNT.

Exposition crypto remontée autour de 20 %.

## Bitpanda

Suivi manuel démarré :
- Top Gainers ;
- Top Losers ;
- comparaison avec les signaux NSC.

Statut :
- pas encore automatisé ;
- pas encore intégré aux scores ;
- pas encore intégré à l’interface.

## Règles structurantes confirmées

- Aucun transfert automatique Crypto ↔ IBKR.
- Funding manuel obligatoire.
- Préproduction en SIMULATED_ONLY.
- Gouvernance comme source de vérité.
- Hard block réservé aux vrais cas critiques.

## Prochaines priorités

1. Surveiller CREAM / LINK / PNT.
2. Valider la stabilité du fallback social.
3. Suivre la remontée crypto vers 25 %, puis 30 %, puis 37 %.
4. Comparer market momentum pur vs social fallback.
5. Reprendre ensuite la brique Actions Offensives.

