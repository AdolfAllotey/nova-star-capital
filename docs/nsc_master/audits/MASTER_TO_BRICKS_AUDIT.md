# NSC — Audit Master vers Briques

Objectif : vérifier que chaque brique respecte le Master NSC avant préprod globale production-like.

## Briques à auditer

- Crypto
- Actions offensives
- Actions défensives
- Obligations
- Métaux précieux
- Options US
- Long Terme
- Portfolio Engine
- Capital / Funding
- Risk / Governance
- API / UI

## Critères par brique

1. Rôle conforme au Master
2. Régime marché pris en compte
3. Allocation dynamique
4. Sortie standardisée vers Portfolio Engine
5. Capital flow conforme
6. Impôts / BFR / sécurité / LT respectés
7. Mode PREPROD simulé clair
8. Aucun ordre réel
9. Logs présents
10. Artefacts JSON propres
11. API/UI branchées
12. Prête pour préprod globale

## Règle préprod

La préprod doit être aussi proche que possible de la production, sauf :
- comptes brokers non raccordés réellement ;
- capital virtuel ;
- exécution réelle désactivée ;
- transferts inter-brokers simulés ou manuels.
