
# src/v2/analysis/ethical_scorer.py

import random

def evaluate_ethical_score(token_address: str) -> dict:
    """
    Calcule un score éthique simulé pour un token donné.
    À terme, cette fonction utilisera des données réelles (on-chain, APIs, etc.).

    Args:
        token_address (str): Adresse du contrat du token.

    Returns:
        dict: Score éthique et détails.
    """
    # Simulation de données
    score = random.randint(40, 95)
    dominant_holder = round(random.uniform(2.0, 10.0), 2)
    verified_contract = random.choice([True, False])
    holders_count = random.randint(30, 500)
    multisig_enabled = random.choice([True, False])

    note = []
    if dominant_holder > 5.0:
        note.append("⚠️ Wallet dominant (>5%)")
    if not verified_contract:
        note.append("⚠️ Contrat non vérifié")
    if holders_count < 50:
        note.append("⚠️ Peu de détenteurs")
    if multisig_enabled:
        note.append("✅ Multisig actif")
    if score > 85:
        note.append("✅ Très bon comportement")

    return {
        "score": score,
        "dominant_holder_pct": dominant_holder,
        "verified_contract": verified_contract,
        "holders_count": holders_count,
        "multisig_enabled": multisig_enabled,
        "note": note
    }

# Exemple
if __name__ == "__main__":
    test = evaluate_ethical_score("0x1234567890abcdef")
    print(test)
