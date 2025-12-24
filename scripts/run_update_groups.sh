#!/bin/bash
# Mettre à jour les groupes Telegram

cd "$(dirname "$0")"
mkdir -p logs

echo "🔄 Début run_update_groups.sh à $(date)" | tee -a logs/update_groups.log

# Activer l’environnement virtuel
source venv310/bin/activate

# Lancer la mise à jour des groupes et afficher le log
PYTHONPATH=src python src/social/scrapers/scrape_telegram_groups.py 2>&1 | tee -a logs/update_groups.log

echo "✅ run_update_groups.sh terminé à $(date)" | tee -a logs/update_groups.log