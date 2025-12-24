# src/v2/interface/user_dashboard.py

import streamlit as st
import pandas as pd
import os

def display_dashboard(data):
    st.set_page_config(page_title="User Dashboard", layout="wide")
    st.title("📊 Tableau de bord utilisateur")

    if not data:
        st.warning("Aucune donnée à afficher.")
        return

    df = pd.DataFrame(data)

    # Mapping visuel pour le score éthique
    color_map = {
        "green": "🟢 Green",
        "neutral": "🟡 Neutral",
        "red": "🔴 Red Flag"
    }

    if "status" in df.columns:
        df["Éthique"] = df["status"].map(color_map)

    # Tri automatique si colonne 'score' présente
    if "score" in df.columns:
        df = df.sort_values("score", ascending=False)

    # Affichage du tableau final
    st.dataframe(df, use_container_width=True)

    # Sauvegarde facultative de l’export
    if st.button("💾 Exporter en CSV"):
        output_path = "data/v2/exports/user_dashboard_export.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        st.success(f"Fichier exporté : {output_path}")

# Exemple d’appel local pour test
if __name__ == "__main__":
    sample_data = [
        {"token": "BTC", "score": 92, "sentiment": 0.84, "status": "green"},
        {"token": "ETH", "score": 88, "sentiment": 0.75, "status": "green"},
        {"token": "AVAX", "score": 71, "sentiment": 0.52, "status": "neutral"},
        {"token": "RUG", "score": 45, "sentiment": 0.2, "status": "red"},
    ]
    display_dashboard(sample_data)