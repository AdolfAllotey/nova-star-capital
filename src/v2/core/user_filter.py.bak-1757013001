
# src/v2/core/user_filter.py

def filter_signals_by_preferences(user_prefs, signals):
    """
    Filtre les signaux en fonction des préférences utilisateur.

    Args:
        user_prefs (dict): Préférences de l'utilisateur.
        signals (list): Liste de signaux (dictionnaires avec token, score, etc.)

    Returns:
        list: Signaux filtrés
    """
    preferred_tokens = set(user_prefs.get("preferred_tokens", []))
    blacklisted_tokens = set(user_prefs.get("blacklist_tokens", []))
    min_sentiment = user_prefs.get("min_sentiment", 0.0)
    max_volatility = user_prefs.get("max_volatility", 1.0)

    filtered = []
    for signal in signals:
        token = signal.get("token")
        sentiment = signal.get("sentiment", 0)
        volatility = signal.get("volatility", 0)

        if token in blacklisted_tokens:
            continue
        if sentiment < min_sentiment:
            continue
        if volatility > max_volatility:
            continue
        if preferred_tokens and token not in preferred_tokens:
            continue

        filtered.append(signal)

    return filtered
