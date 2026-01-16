import time
from src.v2.core.account_manager import get_capital_allocation
from src.v2.integrations.binance_api import transfer_to_subaccount

def execute_transfers():
    print("🔄 Démarrage du transfert automatique des fonds...")

    # Récupérer la répartition du capital
    allocation = get_capital_allocation()

    # Transferts vers les sous-comptes Binance
    for purpose, amount in allocation.items():
        try:
            transfer_to_subaccount(subaccount_label=purpose, amount=amount)
            print(f"✅ {amount} USDT transférés vers le sous-compte '{purpose}'")
        except Exception as e:
            print(f"❌ Erreur lors du transfert vers '{purpose}': {e}")

    print("✅ Tous les transferts ont été traités.")

if __name__ == "__main__":
    while True:
        execute_transfers()
        time.sleep(3600 * 6)  # Par défaut : exécuter toutes les 6h (modifiable)