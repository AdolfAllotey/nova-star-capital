import pandas as pd

# === Pondération des sources sociales
SOURCE_WEIGHTS = {
    "twitter": 0.5,
    "telegram": 0.3,
    "reddit": 0.2
}

# === Seuils d'investissement
MIN_SCORE_THRESHOLD = 0.7
MIN_VOLUME_USD = 50000
MIN_PERCENT_PUMP = 20


def compute_token_score(social_mentions):
    """
    Calcule un score pondéré basé sur les mentions sociales.
    social_mentions: dict du type {"PEPE": {"twitter": 120, "telegram": 40, "reddit": 15}, ...}
    """
    scores = {}
    for token, sources in social_mentions.items():
        score = 0
        for source, count in sources.items():
            weight = SOURCE_WEIGHTS.get(source, 0)
            normalized = min(count / 100, 1)  # Limiter à 1
            score += weight * normalized
        scores[token] = round(score, 3)
    return scores


def is_token_eligible(score, volume_usd, percent_change_1h):
    """
    Applique les règles intelligentes : score + volume + pump
    """
    return (
        score >= MIN_SCORE_THRESHOLD
        and volume_usd >= MIN_VOLUME_USD
        and percent_change_1h >= MIN_PERCENT_PUMP
    )


def decide_investments(social_mentions, dex_metrics):
    """
    Combine données sociales + metrics DEX pour identifier les tokens prometteurs.
    Retourne un DataFrame avec les tokens à acheter.
    """
    token_scores = compute_token_score(social_mentions)
    selected = []

    for token, score in token_scores.items():
        dex = dex_metrics.get(token)
        if not dex:
            continue

        volume = dex.get("volume", 0)
        pct = dex.get("pct_change_1h", 0)
        if is_token_eligible(score, volume, pct):
            selected.append({
                "token": token,
                "score": score,
                "volume_24h": volume,
                "pct_change_1h": pct
            })

    return pd.DataFrame(selected).sort_values("score", ascending=False)