#!/bin/bash

echo "🚀 Lancement de Nova Star Capital V2..."

# Se placer à la racine du projet
cd "$(dirname "$0")/../.."

# Activer l’environnement virtuel
source venv310/bin/activate

# Lancer le main.py de la V2
python3 -m src.v2.main

echo "✅ Exécution terminée."