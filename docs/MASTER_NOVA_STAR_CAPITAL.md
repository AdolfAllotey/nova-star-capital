# Nova Star Capital — Master

Document de référence institutionnel du projet.

<!-- BEGIN NSC OFFICIAL RELEASE STATUS -->

# Statut officiel des releases Nova Star Capital

Dernière mise à jour automatique : 2026-07-24T15:06:00.818834+00:00

---

## RC1 — Core Portfolio Engine

### Statut officiel

- **Release :** RC1
- **Composant :** Core Portfolio Engine
- **Décision :** APPROVED
- **Statut de baseline :** FROZEN
- **Certification :** RC1_END_TO_END_CERTIFIED
- **Résultat :** PASS
- **Date d’approbation :** 2026-07-24T14:28:44.097097+00:00
- **Baseline ID :** `RC1-20260724T142844Z`
- **Empreinte globale SHA-256 :** `7c68e7a33bd4c918ce3eb6b2018a93ccaa213189969492ad21da7ea349489e46`

La RC1 du Core Portfolio Engine est officiellement
certifiée, approuvée et gelée.

Elle constitue la baseline institutionnelle de référence
pour les développements, audits de non-régression et
certifications ultérieurs.

Toute évolution fonctionnelle postérieure à cette
certification appartient à la RC2 ou à une release
ultérieure.

### Résultat de certification

- Contrôles exécutés : 38
- Contrôles réussis : 38
- Contrôles en échec : 0
- Warnings : 0
- Blockers : 0
- RC1 blocker : false
- Artefacts archivés : 15

### Périmètre gouverné certifié

- bonds
- crypto
- equities_defensive
- equities_offensive
- precious_metals

### Politique d’allocation certifiée

Le modèle d’allocation RC1 est :

**DYNAMIC_POLICY_DRIVEN**

La RC1 ne certifie pas des poids permanents par classe
d’actifs.

Elle certifie une politique d’allocation dynamique pilotée
par :

- le régime de marché ;
- les signaux des briques ;
- les niveaux de conviction et de confiance ;
- les contraintes de risque ;
- les caps par famille ;
- les conditions cross-asset ;
- les règles de gouvernance ;
- le maintien du buffer de liquidités.

Éléments figés :

- logique d’allocation ;
- règles de normalisation ;
- familles d’actifs ;
- caps et contraintes de risque ;
- politique de cash ;
- exclusions de politique ;
- règles de gouvernance ;
- règles d’autorisation d’exécution.

Poids définitivement figés :

**NON**

Politique figée :

**OUI**

### Photographie du run certifié

| Brique | Pondération |
|---|---:|
| Crypto | 36.3636 % |
| Actions offensives | 18.1818 % |
| Actions défensives | 18.1818 % |
| Obligations | 13.6364 % |
| Métaux précieux | 3.6364 % |
| Cash | 10.0000 % |

Ces pondérations sont une photographie du run certifié.
Elles ne constituent pas des cibles permanentes.

### Gouvernance et sécurité

- Action policy : `SIMULATED_ONLY`
- Execution mode : `SIMULATED`
- Exécution réelle autorisée : false
- Exécution simulée autorisée : true
- Rebalance automatique autorisé : false
- Funding automatique autorisé : false
- Validation manuelle obligatoire : true
- Transfert inter-pools automatique : false

### Executive Decision observée lors de la certification

- Décision : `SIMULATE_INCREASE`
- Brique recommandée : `crypto`
- Montant recommandé : 600.0 EUR
- Confiance : 89.24 %
- Execution posture : `SIMULATED_ONLY`
- Risk posture : `CONTROLLED_RISK_ON_WITH_CORRELATION_WATCH`

Cette décision est une photographie de certification et
non une instruction permanente d’investissement.

### Composants exclus du périmètre gouverné RC1

- **options_us** : `policy_excluded_observation` — not_allowed_by_master_policy
- **options_v2_shadow** : `shadow_observation_only` — shadow_observation_only
- **long_term** : `passive_patrimonial_observation` — outside_active_allocation_target

Ces composants peuvent rester observables, mais ne
participent pas à l’allocation gouvernée RC1.

### Dette technique acceptée

1. Clarify and harmonize options_us shadow and observation semantics.
2. Remove the historical options_us pocket from capital_allocator_v1 or mark it explicitly as non-governed.
3. Replace datetime.utcnow() with timezone-aware UTC datetime generation.
4. Centralize risk_limits.json under NSC_DATA_DIR and remove divergent runtime paths.
5. Populate the governance artifact status field explicitly.
6. Install yfinance or formally document and test the market snapshot fallback.
7. Refresh stale Options status timestamps before RC2 certification.
8. Reconcile Risk Controller runtime parameters with Global Orchestration Audit inputs.

Cette dette est non bloquante pour la RC1 et doit être
suivie pendant le hardening RC2 et la préparation de la
production.

---

## RC2 — Multi-Asset Engine

### Statut

**OUVERTE POUR CADRAGE ET DÉVELOPPEMENT**

### Objectif

Transformer le Core Portfolio Engine RC1 en un moteur
Multi-Asset intégrant les Options US comme classe d’actifs
gouvernée.

### Date cible de démarrage de la préproduction

**Au plus tard le 1er août 2026**

### Durée cible

**30 jours de préproduction**

### Périmètre prévu

- governed_us_options
- options_allocation_policy
- options_greeks
- multi_asset_risk
- portfolio_brain_integration
- rc2_end_to_end_certification
- 30_day_preproduction

### Sous-jacents Options prioritaires

- QQQ
- SPY
- NVDA
- AAPL
- MSFT
- AMZN
- META
- TSLA

### Règles de transition RC1 vers RC2

- la baseline RC1 reste immuable ;
- aucun artefact de la baseline RC1 ne doit être modifié ;
- toute évolution fonctionnelle doit être versionnée RC2 ;
- les tests de non-régression doivent comparer RC2 à RC1 ;
- l’exécution réelle demeure interdite ;
- les Options restent en observation tant que leur
  gouvernance RC2 n’est pas certifiée ;
- le passage en préproduction RC2 exige un Release Gate
  d’entrée dédié ;
- la sortie de RC2 exige une certification End-to-End
  Multi-Asset.

### Livrable attendu

**Multi-Asset Engine Approved**

---

## Roadmap institutionnelle

### RC1 — Core Portfolio Engine

**TERMINÉE — CERTIFIÉE — APPROUVÉE — GELÉE**

### RC2 — Multi-Asset Engine

**OUVERTE**

Objectif principal : intégration gouvernée des Options US
et préproduction Multi-Asset de 30 jours.

### RC3 — Production Readiness

Périmètre principal :

- Dashboard Production Readiness ;
- UI Data Integrity Audit ;
- alignement UI / API / artefacts backend ;
- suppression des données statiques ;
- audit runners et automatisations ;
- audit sécurité, logs, alertes et reprises ;
- audit OpenAI Codex ;
- tests de non-régression ;
- Go/No-Go production.

### RC4 — Controlled Production Launch

Périmètre principal :

- capital réel limité ;
- tailles de positions réduites ;
- validation humaine ;
- limites renforcées ;
- journalisation complète ;
- comparaison préproduction / production ;
- montée en charge progressive.

### RC5 — Institutional Scaling

Périmètre possible :

- multi-broker ;
- nouvelles classes d’actifs ;
- optimisation avancée du budget de risque ;
- stress tests ;
- reporting investisseurs ;
- architecture Family Office ;
- consolidation patrimoniale globale.

---

## Références officielles

- Release Gate JSON :
  `/opt/nsc/data/preprod/releases/RC1/rc1_release_gate.json`

- Baseline courante :
  `/opt/nsc/data/preprod/releases/RC1/current_baseline.json`

- Baseline archivée :
  `/opt/nsc/data/preprod/releases/RC1/baselines/RC1-20260724T142844Z`

- Master machine-readable :
  `/opt/nsc/data/preprod/governance/nsc_master_status.json`

<!-- END NSC OFFICIAL RELEASE STATUS -->
