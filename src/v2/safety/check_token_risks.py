import os
from src.v2.utils.file_utils import (
    load_selected_tokens,
    load_token_blacklist,
    save_json
)
from src.v2.utils.telegram_bot import send_telegram_message

RISK_OUTPUT_FILE = "src/v2/data/risk/token_risks.json"

def check_token_risks():
    """
    Analyse des risques des tokens sélectionnés.
    Applique plusieurs règles de filtrage pour identifier les tokens risqués.
    """
    try:
        selected_tokens = load_selected_tokens()
        blacklist = load_token_blacklist()
        risky_tokens = []

        for token in selected_tokens:
            reasons = []

            # Règle 1 : Score trop faible
            if token.get("score", 0) < 30:
                reasons.append("Score très faible")

            # Règle 2 : Sentiment très bas
            if token.get("sentiment", 1) < 0.1:
                reasons.append("Sentiment très négatif")

            # Règle 3 : Token blacklisté
            if token.get("symbol") in blacklist:
                reasons.append("Token présent dans la blacklist")

            # Règle 4 : Volume trop faible (optionnelle)
            if token.get("volume", 1000000) < 10000:
                reasons.append("Volume trop faible")

            if reasons:
                token["risk_reasons"] = reasons
                risky_tokens.append(token)

        save_json(risky_tokens, RISK_OUTPUT_FILE)

        if risky_tokens:
            send_telegram_message(f"⚠️ {len(risky_tokens)} token(s) à risque détectés. Détails enregistrés dans token_risks.json.")
        else:
            send_telegram_message("✅ Aucun risque détecté parmi les tokens sélectionnés.")

    except Exception as e:
        print("❌ Erreur dans check_token_risks :", e)
        send_telegram_message(f"❌ Erreur dans check_token_risks : {e}")