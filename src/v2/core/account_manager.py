import os
import json
from decimal import Decimal

CONFIG_PATH = "src/v2/config/capital_allocation_config.json"

class CapitalAllocator:
    def __init__(self, initial_balance: float, sasu_mode: bool = True):
        self.total_balance = Decimal(initial_balance)
        self.sasu_mode = sasu_mode
        self.allocations = {
            "trading": Decimal("1.0"),
            "taxes": Decimal("0.0"),
            "security": Decimal("0.0"),
        }
        self.thresholds = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            print(f"⚠️ Fichier config non trouvé: {CONFIG_PATH}. Utilisation valeurs par défaut.")
            return [
                {"min_balance": 0, "allocations": {"trading": 1.0, "taxes": 0.0, "security": 0.0}},
                {"min_balance": 10000, "allocations": {"trading": 0.9, "taxes": 0.05, "security": 0.05}},
                {"min_balance": 20000, "allocations": {"trading": 0.8, "taxes": 0.1, "security": 0.1}},
                {"min_balance": 50000, "allocations": {"trading": 0.7, "taxes": 0.15, "security": 0.15}},
            ]
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)["thresholds"]

    def update_total_balance(self, new_balance: float):
        self.total_balance = Decimal(new_balance)

    def apply_allocation_rules(self):
        if not self.sasu_mode:
            return self.allocations

        applicable = None
        for threshold in sorted(self.thresholds, key=lambda x: x["min_balance"]):
            if self.total_balance >= Decimal(threshold["min_balance"]):
                applicable = threshold["allocations"]

        if applicable:
            self.allocations = {k: Decimal(str(v)) for k, v in applicable.items()}

        return self.allocations

    def get_allocation_amounts(self):
        self.apply_allocation_rules()
        return {
            "trading": self.total_balance * self.allocations["trading"],
            "taxes": self.total_balance * self.allocations["taxes"],
            "security": self.total_balance * self.allocations["security"],
        }

if __name__ == "__main__":
    manager = CapitalAllocator(initial_balance=15000)
    amounts = manager.get_allocation_amounts()
    print("Répartition du capital :", amounts)