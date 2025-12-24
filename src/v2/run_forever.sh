#!/bin/bash

echo "🔁 Démarrage du bot Nova Star Capital (mode 24/7)"

while true; do
    echo "🕒 Nouvelle exécution : $(date '+%Y-%m-%d %H:%M:%S')"

    # ✅ main.py est dans le même dossier
    python3 main.py

    echo "✅ Exécution terminée. Prochaine dans 24h."
    echo "------------------------------------------"

    sleep 86400
done