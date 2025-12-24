# 🧠 Bot Crypto Ultra

Bot Crypto Ultra est un bot d’analyse et de simulation de trades sur des cryptomonnaies détectées à partir de données sociales (Telegram, Reddit). Il utilise une stratégie pondérée combinant score + sentiment, et effectue des simulations automatiques pour détecter les meilleurs signaux.

---

## ⚙️ Fonctionnalités V1

- Scraping de groupes Telegram et subreddits crypto
- Détection des tokens les plus mentionnés
- Analyse de sentiment via mots-clés
- Classement des tokens par score et sentiment
- Simulation de trades en mode fictif :
  - Pondération des investissements
  - Stop-loss / Take-profit
  - Calcul des profits journaliers
- Envoi automatique :
  - Alertes de trades simulés (Telegram uniquement)
  - Rapport global quotidien (Telegram + Email)
- Interface Streamlit de visualisation
- Exécution continue via `run_forever.sh`
- Rapport récapitulatif journalier à 20h (via cron)

---

## 🗂️ Structure du projet

```bash
Bot_crypto_ultra/
│
├── data/                         # Données sociales, simulations, historiques
│   ├── social/
│   ├── trades/
│   ├── simulation/
│   └── groups/
│
├── src/
│   ├── social/                   # Analyse, scoring, sentiment
│   ├── trading/                 # Simulation, logique d’investissement
│   ├── utils/                   # Utilitaires (fichiers, tokens, volumes)
│   └── scripts/                 # Scripts d’exécution (simulation, envoi)
│
├── scripts/                     # Scripts shell de lancement
├── archive/                     # Fichiers obsolètes ou de test
├── run_forever.sh              # Lancement continu toutes les 30 min
└── README.md                   # Ce fichier
```

---

## 🚀 Utilisation

### 🔹 Lancement manuel (simulation quotidienne)

```bash
PYTHONPATH=src python3 src/trading/generate_trade_simulation.py
```

### 🔹 Lancement du rapport

```bash
PYTHONPATH=src python3 src/scripts/send_report.py
```

### 🔹 Lancement continu

```bash
bash run_forever.sh
```

---

## ⏰ Automatisation

### Service Linux (redémarrage automatique)

Fichier : `/etc/systemd/system/botcrypto.service`

```ini
[Unit]
Description=Bot Crypto Ultra - Simulation Continue
After=network.target

[Service]
ExecStart=/bin/bash /root/Bot_crypto_ultra/run_forever.sh
WorkingDirectory=/root/Bot_crypto_ultra
Restart=always

[Install]
WantedBy=multi-user.target
```

> Commande d’activation :
```bash
sudo systemctl enable botcrypto.service
sudo systemctl start botcrypto.service
```

---

### Cron – Rapport quotidien à 20h

```bash
0 20 * * * cd /root/Bot_crypto_ultra && /root/Bot_crypto_ultra/venv310/bin/python3 -m src.scripts.send_report >> /root/Bot_crypto_ultra/logs/send_report.log 2>&1
```

---

## 🧭 Roadmap V2 (prochaine version)

- Exécution en temps réel sur fonds réels
- Nouvelle interface Web (mode plateforme)
- Détection des rug pulls / airdrops / whales
- Adaptation ML en continu
- Optimisation stratégique avec backtests
- Intégration API Bitpanda
- Suivi des pires trades (analyse erreurs)
- Pondération dynamique sentiment/score
- Société dédiée (SASU) pour gestion légale

---

## 👤 Auteur

> Adolf Allotey – 2025  
> Version V1 terminée – Passage à la V2 en cours