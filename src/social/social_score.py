
import pandas as pd

def compute_social_score(tokens, telegram_csv, reddit_csv, poids_tg=1.0, poids_rd=2.0):
    # Charger les fichiers
    df_tg = pd.read_csv(telegram_csv)
    df_rd = pd.read_csv(reddit_csv)

    # Compter les mentions Telegram
    tg_counts = df_tg['token'].value_counts().to_dict()

    # Compter les mentions Reddit
    rd_counts = df_rd['token'].value_counts().to_dict()

    # Calculer le score combiné
    scores = []
    for token in tokens:
        tg_mentions = tg_counts.get(token, 0)
        rd_mentions = rd_counts.get(token, 0)
        score = (tg_mentions * poids_tg) + (rd_mentions * poids_rd)

        scores.append({
            "token": token,
            "mentions_telegram": tg_mentions,
            "mentions_reddit": rd_mentions,
            "score_social": score
        })

    return sorted(scores, key=lambda x: x["score_social"], reverse=True)
