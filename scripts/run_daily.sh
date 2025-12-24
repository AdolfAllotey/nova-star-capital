#!/bin/bash
# Lancer le pipeline principal

# Se placer dans le dossier du script (optionnel mais recommandé)
cd "$(dirname "$0")"

# Créer le dossier logs s’il n'existe pas
mkdir -p logs

# Démarrer le log et afficher dans le terminal ET le log
echo "🚀 Début run_daily.sh à $(date)" | tee -a logs/cron.log

# Activer l’environnement virtuel
source venv310/bin/activate

# Lancer le script principal et afficher dans les deux
PYTHONPATH=src python main.py 2>&1 | tee -a logs/cron.log

# Fin d’exécution
echo "✅ run_daily.sh terminé à $(date)" | tee -a logs/cron.log