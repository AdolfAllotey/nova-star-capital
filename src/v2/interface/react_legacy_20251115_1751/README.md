# Nova Star Capital – Crypto Bot Interface (React)

Interface professionnelle développée pour la V2 du bot crypto **Nova Star Capital**, avec visualisation des signaux, résultats simulés, backtests, et synthèse intelligente.

---

## 🚀 Fonctionnalités principales

### 🧠 Dashboard quotidien

* Sélection de la date
* Filtres dynamiques : score minimum, sentiment minimum, winners only
* Tableau des trades simulés (P\&L, buy/sell)
* Graphique de performance cumulée sur 7 jours
* Bloc de résumé intelligent (Signal Summary)
* Mode de visualisation : `Simulation` (Réel à venir)

### 📊 Comparateur de backtests

* Chargement des résultats depuis `/data/backtests/*.json`
* Graphe barres : PnL total par stratégie
* Tableau comparatif : PnL, nombre de trades, win rate

### 💬 Résumé LLM (ChatGPT-ready)

* Lecture des résumés quotidiens depuis `/data/simulation/YYYY-MM-DD_summary.json`
* Prévu pour intégrer OpenAI API (GPT-4o) après création de la SASU

### 🧭 Navigation par onglets

* Dashboard
* Backtests
* LLM Insights

---

## 📁 Structure des fichiers clés

```
src/v2/interface/react/
├── App.jsx                     # Point d’entrée avec navigation
├── dashboard.jsx              # Vue principale quotidienne
├── components/
│   ├── PerformanceChart.jsx   # Graphe PnL 7 jours
│   ├── SignalSummary.jsx      # Résumé signaux du jour
│   ├── BacktestComparison.jsx # Comparatif multi-stratégie
│   └── LLMInsights.jsx        # Résumé généré (fichier ou API)
├── utils/
│   └── dataFetcher.js         # Chargement JSON simulation/backtest
```

---

## 🔧 Dépendances nécessaires

* React
* Tailwind CSS
* Recharts (`npm install recharts`)

---

## 🔜 À venir (V2.1/V3)

* Connexion API OpenAI (GPT-4o) pour génération auto de résumés
* Connexion données réelles (Binance, IBKR, etc.)
* Mode multi-profils (V3 SaaS)
* Uploads / sauvegarde de résultats
* Alertes Telegram/Email depuis l’interface

---

Développé pour **Nova Star Capital** – Automatiser l’analyse et la décision d’investissement crypto
