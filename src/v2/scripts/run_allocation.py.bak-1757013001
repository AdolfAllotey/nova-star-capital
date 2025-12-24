import os
import json
from src.v2.core.capital_allocator import allocate_gains

SIMULATED_RESULTS_PATH = "data/v2/simulation/simulated_results.json"

def load_gain_from_simulation():
    if not os.path.exists(SIMULATED_RESULTS_PATH):
        print("❌ Fichier de simulation introuvable.")
        return 0

    with open(SIMULATED_RESULTS_PATH, "r") as f:
        data = json.load(f)

    return round(data.get("gain_of_the_day", 0), 2)

if __name__ == "__main__":
    gain = load_gain_from_simulation()
    if gain <= 0:
        print(f"⚠️ Aucun gain à réaffecter aujourd’hui (gain = {gain} €).")
    else:
        print(f"📈 Gain du jour détecté : {gain} €")
        allocate_gains(gain)