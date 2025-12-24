import os
import json

STRATEGY_FOLDER = "data/v2/strategies"

def list_strategy_files():
    """
    Liste les fichiers JSON disponibles dans le dossier stratégies.
    """
    if not os.path.exists(STRATEGY_FOLDER):
        return []
    return [f for f in os.listdir(STRATEGY_FOLDER) if f.endswith(".json")]

def load_strategy(file_name):
    """
    Charge une stratégie JSON par nom de fichier.
    """
    file_path = os.path.join(STRATEGY_FOLDER, file_name)
    if not os.path.exists(file_path):
        print(f"⚠️ Fichier stratégie non trouvé : {file_path}")
        return None
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON dans {file_path} : {e}")
            return None

def save_strategy(strategy_data, file_name):
    """
    Sauvegarde une stratégie dans un fichier JSON.
    """
    os.makedirs(STRATEGY_FOLDER, exist_ok=True)
    file_path = os.path.join(STRATEGY_FOLDER, file_name)
    with open(file_path, "w") as f:
        json.dump(strategy_data, f, indent=2)
    print(f"✅ Stratégie sauvegardée dans : {file_path}")

if __name__ == "__main__":
    print("Fichiers stratégies disponibles :", list_strategy_files())
    # Exemple de chargement
    strategy = load_strategy("strategy.json")
    print("Stratégie chargée :", strategy)