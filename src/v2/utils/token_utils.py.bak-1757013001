import re

def extract_token_symbols(text):
    """
    Extrait les symboles de tokens d’un texte donné.
    Exemple : détecter les symboles type 'BTC', 'ETH', 'SOL', souvent en majuscules.

    Args:
        text (str): texte brut à analyser

    Returns:
        list[str]: liste unique de tokens détectés en majuscules
    """
    if not text or not isinstance(text, str):
        return []

    # Expression régulière pour tokens de 2 à 5 lettres majuscules (ex : BTC, ETH)
    pattern = r'\b[A-Z]{2,5}\b'

    tokens = re.findall(pattern, text)
    # Retourne les tokens uniques
    return list(set(tokens))

def clean_token_symbol(token):
    """
    Nettoie un symbole de token en supprimant espaces, caractères non alphanumériques.

    Args:
        token (str): symbole brut

    Returns:
        str: symbole nettoyé en majuscules
    """
    if not token or not isinstance(token, str):
        return ""

    cleaned = re.sub(r'[^A-Za-z0-9]', '', token).upper()
    return cleaned