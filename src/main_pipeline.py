import os
import subprocess
from src.pipeline.merge_and_decide import merge_results_and_decide

print("🚀 Lancement de la pipeline complète du bot...")

# Étape 1 - Scraping et agrégation
print("\n🔹 Étape 1 : Scraping & agrégation des données sociales")
subprocess.run(["python", "src/social/social_token_discovery_pipeline.py"])

# Étape 2 - Détection des tokens
print("\n🔹 Étape 2 : Détection des tokens")
subprocess.run(["python", "src/social/save_detected_tokens.py"])

# Étape 3 - Scoring des tokens
print("\n🔹 Étape 3 : Scoring des tokens")
subprocess.run(["python", "src/social/score_tokens.py"])

# Étape 4 - Analyse de sentiment
print("\n🔹 Étape 4 : Analyse de sentiment")
subprocess.run(["python", "src/social/analyze_social_sentiment.py"])

# Étape 5 - Fusion et sélection des meilleurs
print("\n🔹 Étape 5 : Fusion des résultats et sélection des top tokens")
df_sorted, top_tokens = merge_results_and_decide()

# Étape 6 - Envoi (prochaine étape)
print("\n✅ Pipeline terminée jusqu'à l'étape de sélection.\n")