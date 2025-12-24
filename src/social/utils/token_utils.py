import re

def extract_and_clean_tokens(text):
    """
    Nettoie un message texte pour extraire des tokens sous forme de symboles.
    Se base sur une regex de symboles en majuscule.
    """
    if not text:
        return []

    potential_tokens = re.findall(r'\b[A-Z]{2,6}\b', text)
    cleaned_tokens = list(set(token.strip() for token in potential_tokens if token.isupper()))
    return cleaned_tokens

def extract_token_symbols(text):
    """
    Extrait uniquement les symboles potentiels de tokens du texte.
    Moins de traitement que extract_and_clean_tokens.
    """
    if not text:
        return []

    return re.findall(r'\b[A-Z]{2,6}\b', text)