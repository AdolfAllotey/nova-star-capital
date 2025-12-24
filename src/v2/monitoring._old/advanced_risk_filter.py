
# src/v2/monitoring/advanced_risk_filter.py

import os
import json

BLACKLIST_FILE = "src/v2/config/rugpull_blacklist.json"

def load_rugpull_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    return []

def apply_advanced_risk_checks(tokens, portfolio_state, risk_config):
    """
    Applique des règles de risk management avancées.

    Args:
        tokens (list): Liste de tokens filtrés.
        portfolio_state (dict): Contient les soldes ou drawdowns.
        risk_config (dict): Règles à appliquer.

    Returns:
        tuple: (tokens_validés, alertes)
    """
    blacklist = load_rugpull_blacklist()
    max_drawdown_pct = risk_config.get("max_drawdown_pct", 0.1)
    max_token_exposure = risk_config.get("max_token_exposure_pct", 0.3)

    alerts = []
    safe_tokens = []

    # Vérification du drawdown global
    starting = portfolio_state.get("start", 10000)
    current = portfolio_state.get("current", 9500)
    drawdown = (starting - current) / starting

    if drawdown >= max_drawdown_pct:
        alerts.append(f"❌ Drawdown global de {drawdown*100:.1f}% dépassé (seuil: {max_drawdown_pct*100:.1f}%)")
        return [], alerts  # Blocage complet

    # Vérification token par token
    for token in tokens:
        symbol = token.get("token")
        if symbol in blacklist:
            alerts.append(f"🚫 {symbol} blacklisté (rug pull/suspect)")
            continue

        if token.get("allocation_pct", 0) > max_token_exposure:
            alerts.append(f"⚠️ {symbol} dépasse le seuil max de {max_token_exposure*100:.1f}%")
            continue

        safe_tokens.append(token)

    return safe_tokens, alerts

# Exemple d'utilisation
if __name__ == "__main__":
    tokens = [
        {"token": "BTC", "allocation_pct": 0.2},
        {"token": "XYZ", "allocation_pct": 0.5},
    ]
    portfolio_state = {"start": 10000, "current": 9000}
    config = {"max_drawdown_pct": 0.1, "max_token_exposure_pct": 0.3}
    valid, alerts = apply_advanced_risk_checks(tokens, portfolio_state, config)
    print("Validés:", valid)
    print("Alertes:", alerts)
