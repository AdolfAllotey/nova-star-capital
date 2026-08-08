# NSC — COMMERCIALIZATION ROADMAP

## Statut

Ce document décrit une orientation stratégique future.  
Il ne fait pas partie du cœur opérationnel actuel de NSC.

Le système actuel reste prioritairement un core patrimonial privé / proprietary family office.

## Vision future

NSC pourra évoluer vers une plateforme commerciale permettant de proposer :

- des signaux ;
- des alertes ;
- des analyses ;
- des dashboards ;
- puis, plus tard, un accès plus complet à la plateforme après obtention des autorisations réglementaires nécessaires.

## Séparation fondamentale

Deux couches doivent rester séparées :

### NSC Internal Core

Usage :
- capital propre ;
- family office ;
- trading propriétaire ;
- allocation patrimoniale ;
- gouvernance privée ;
- exécution interne.

Cette couche doit rester isolée, sécurisée et non exposée directement aux clients.

### NSC Commercial Platform

Usage futur :
- utilisateurs ;
- abonnements ;
- signaux ;
- alertes ;
- dashboards clients ;
- analytics ;
- éventuellement accès plateforme sous réserve d’autorisations.

Cette couche doit consommer uniquement des outputs contrôlés du core.

## Phase 1 — Signal Platform

Objectif :
proposer un service d’abonnement aux signaux et analytics.

Fonctionnalités possibles :

- alertes Telegram ;
- alertes email ;
- dashboard signaux ;
- watchlists ;
- scoring ;
- market regime ;
- top opportunities ;
- explainability simplifiée.

Restrictions :

- pas d’exécution client ;
- pas de mandat ;
- pas de gestion de fonds tiers ;
- pas de routage d’ordres clients ;
- pas d’accès direct au core NSC.

## Phase 2 — Assisted Platform

Objectif :
proposer une plateforme analytique plus personnalisée.

Fonctionnalités possibles :

- compte utilisateur ;
- profil de risque ;
- préférences d’alertes ;
- portefeuilles simulés ;
- analytics personnalisés ;
- historique des signaux ;
- dashboards premium.

Restrictions :

- exécution toujours désactivée ;
- séparation stricte client/core ;
- disclaimers ;
- conformité renforcée.

## Phase 3 — Licensed Execution Platform

Objectif futur uniquement après validation réglementaire.

Pré-requis :

- autorisations AMF nécessaires ;
- cadre juridique ;
- conformité ;
- KYC / AML ;
- assurance ;
- gouvernance ;
- audit ;
- sécurité ;
- conditions générales ;
- monitoring client ;
- séparation des fonds et données.

Fonctionnalités possibles :

- accès plateforme complet ;
- stratégies encadrées ;
- exécution ou copy trading ;
- allocation guidée ;
- reporting client.

## Contraintes d’architecture à prévoir dès maintenant

Même si la commercialisation n’est pas active, l’architecture doit anticiper :

- multi-tenant ;
- RBAC ;
- séparation données internes / clients ;
- API publique séparée ;
- outputs filtrés ;
- logs d’audit ;
- MFA ;
- segmentation réseau ;
- feature flags ;
- client kill-switch ;
- rate limits ;
- monitoring sécurité.

## Règle critique

Aucun client ne doit accéder directement :

- aux clés brokers ;
- au core execution ;
- au Capital Brain interne ;
- aux positions internes détaillées ;
- aux secrets ;
- aux mécanismes de décision non filtrés.

## Principe officiel

La commercialisation doit être construite comme une couche externe sécurisée.

Elle ne doit jamais compromettre :

- la sécurité du family office core ;
- la confidentialité du capital propre ;
- la stabilité opérationnelle ;
- la conformité réglementaire.
