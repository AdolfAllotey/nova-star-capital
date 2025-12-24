# 📈 Bot Crypto Ultra – V2 (Production)

## 🎯 Objectif
Version de production du bot avec :
- Exécution 24/7 en réel (via Binance & Kucoin)
- IA embarquée pour l’analyse
- Répartition dynamique du capital
- Interface WebAccess pro
- Intégration fiscale via SASU
- Modules avancés inspirés de Axiom & Paal.ai

---

## 🔁 1. Réorganisation & base technique

- Nettoyage / archivage des fichiers V1
- Dossier `src/v2/` dédié
- Nouveau `README.md` V2
- Nouveau `config_v2.json` centralisé

---

## ⚙️ 2. Pipeline de trading 24/7

- Boucle continue (`run_forever.sh`) avec systemd
- Simulation live enregistrée
- Passage en trading réel via API KuCoin + Binance
- Ajout du module d’exécution avec seuils d’allocation

---

## 🧮 3. Règles de capital & fiscalité SASU

- Structure SASU à l’IS
- Revenu réinvesti (pas de salaire/dividendes)
- Règle fiscale automatique :
  - 25% gains nets → sous-compte “Impôt”
- Répartition dynamique :
  - < X € : 100% réinvesti
  - > X € : 70% croissance / 20% sécurité / 10% impôts
- Interface affichant les sous-comptes

---

## 💻 4. Interface WebAccess Trading

- Dashboard pro (Flask/FastAPI)
- Solde, performances, paramètres dynamiques
- Visualisation capital sécurisé / impôts
- Authentification simple
- Version VPS déployée
- Courbes d’évolution & filtres dynamiques
- Historique, journal, export CSV

---

## 🐋 5. Whale Tracker & Wallet Analysis

- Whale Alert API
- Wallet watcher (Win Rate, PnL)
- Analyse tokens accumulés par whales
- Liste noire (dumpers réguliers)
- Détection de wallets influents / développeurs
- Suivi comportemental (hold, vente rapide, % détenu)

---

## 🧠 6. Intelligence Artificielle & Stratégies

- GPT-4o ou LLM local (VPS) :
  - Résumé signaux
  - Justification trades
  - Rapport lisible (`txt`, `html`)
- Stratégies programmables :
  - Seuils personnalisés de score/sentiment
  - Conditions par secteur ou token
  - Fichiers JSON de stratégie
- Résumés Telegram ou hebdomadaires

---

## 🌐 7. Intégrations externes

- API Bitpanda Trends
- DEX Screener (listings)
- CoinMarketCap, GeckoTerminal
- Airdrops.io
- Rugpull checker
- Préparation Paal.ai / Arkham

---

## 📩 8. Reporting & Alerting

- Rapport 20h Telegram
- Rapport 24h simulation continue
- Rapport fiscalité / capital sécurisé
- Export CSV fiscal mensuel (IS)

---

## 🛠️ 9. Modules avancés inspirés d’Axiom (initialement prévus V3)

- 🧠 LLM embarqué (résumé, justification, alertes, interface lisible)
- 🛰️ Sniper trading (listing instantané + revente automatisée)
- 🕵️ Détection de wallets influents (bulle de réseau, pattern d’achat/vente)
- 🔁 Copy-trading de wallets gagnants
- 🧩 Stratégies programmables (logique modulaire par JSON)
- 🎁 Détection airdrop communautaire intelligente (Twitter, Discord, Reddit)

---

## 🏛️ 10. SASU & Projection

- Création SASU
- Wallets sous-comptes Binance/Kucoin
- Préparation déclaration IS
- Planification cashout / trésorerie