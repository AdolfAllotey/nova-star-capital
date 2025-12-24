import os
import pandas as pd
from datetime import datetime
from utils.file_utils import save_dataframe_with_timestamp

# Répertoire d'entrée et sortie
SOCIAL_DATA_DIR = "data/social"
OUTPUT_FILENAME = "combined_social_data.csv"

def combine_social_data():
    print("🔀 Fusion des données sociales...")

    all_dataframes = []
    for filename in os.listdir(SOCIAL_DATA_DIR):
        if filename.endswith(".csv") and "telegram" in filename or "reddit" in filename or "twitter" in filename:
            filepath = os.path.join(SOCIAL_DATA_DIR, filename)
            try:
                df = pd.read_csv(filepath)
                df["source_file"] = filename
                all_dataframes.append(df)
            except Exception as e:
                print(f"❌ Erreur lecture fichier {filename} : {e}")

    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        combined_df.drop_duplicates(inplace=True)
        save_dataframe_with_timestamp(combined_df, folder=SOCIAL_DATA_DIR, base_filename="combined_social_data")
        print(f"✅ Données combinées enregistrées dans : {os.path.join(SOCIAL_DATA_DIR, OUTPUT_FILENAME)}")
    else:
        print("⚠️ Aucun fichier de données sociales trouvé pour fusion.")