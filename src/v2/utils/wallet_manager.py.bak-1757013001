
import os
import json

class WalletManager:
    def __init__(self, wallet_file='data/wallets.json'):
        self.wallet_file = wallet_file
        self.wallets = self._load_wallets()

    def _load_wallets(self):
        if os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'r') as f:
                return json.load(f)
        return {
            "global_balance": 10000.0,
            "safu_wallet": 0.0,
            "tax_wallet": 0.0,
            "active_wallet": 10000.0
        }

    def _save_wallets(self):
        with open(self.wallet_file, 'w') as f:
            json.dump(self.wallets, f, indent=2)

    def update_balances(self, profit, tax_rate=0.15, safu_trigger=20000, safu_rate=0.1):
        self.wallets["global_balance"] += profit
        self.wallets["active_wallet"] += profit

        # Transfert automatique vers le portefeuille impôt
        if profit > 0:
            tax_amount = profit * tax_rate
            self.wallets["tax_wallet"] += tax_amount
            self.wallets["active_wallet"] -= tax_amount

        # Si le solde dépasse un seuil, on transfère vers le SAFU
        if self.wallets["global_balance"] >= safu_trigger:
            safu_amount = self.wallets["active_wallet"] * safu_rate
            self.wallets["safu_wallet"] += safu_amount
            self.wallets["active_wallet"] -= safu_amount

        self._save_wallets()

    def get_wallets(self):
        return self.wallets
