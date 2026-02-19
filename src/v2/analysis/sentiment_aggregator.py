import os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("sentiment_aggregator")

DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")

# Canonical + compat API (reports/)
PRIMARY_OUT = Path(DATA_DIR) / "average_sentiment.json"
REPORTS_OUT = Path(DATA_DIR) / "reports" / "average_sentiment.json"
REPORTS_OUT.parent.mkdir(parents=True, exist_ok=True)

# Inputs possibles (à élargir ensuite)
INPUT_CANDIDATES = [

    # Scored outputs (offline scorer)
    Path(DATA_DIR) / "monitoring_scored" / "telegram_data_scored.json",
    Path(DATA_DIR) / "monitoring_scored" / "twitter_data_scored.json",
    Path(DATA_DIR) / "monitoring_scored" / "reddit_data_scored.json",

    Path(DATA_DIR) / "monitoring" / "telegram_data.json",
    Path(DATA_DIR) / "monitoring" / "twitter_data.json",
    Path(DATA_DIR) / "monitoring" / "reddit_data.json",
    Path(DATA_DIR) / "reports" / "telegram_data.json",
    Path(DATA_DIR) / "reports" / "twitter_data.json",
    Path(DATA_DIR) / "reports" / "reddit_data.json",
    Path(DATA_DIR) / "telegram_data.json",
    Path(DATA_DIR) / "twitter_data.json",
    Path(DATA_DIR) / "reddit_data.json",
]

def _extract_scores(obj):
    """
    Cherche des scores de sentiment dans une structure arbitraire.
    On supporte:
      - list[dict] avec sentiment/score/polarity
      - dict avec key 'messages' (list)
      - dict direct contenant sentiment/score/polarity
    """
    scores = []
    if isinstance(obj, dict):
        if any(k in obj for k in ("sentiment", "score", "polarity")):
            v = obj.get("sentiment", obj.get("score", obj.get("polarity")))
            if isinstance(v, (int, float)):
                scores.append(float(v))
        if isinstance(obj.get("messages"), list):
            for m in obj["messages"]:
                scores.extend(_extract_scores(m))
        if isinstance(obj.get("data"), list):
            for m in obj["data"]:
                scores.extend(_extract_scores(m))
    elif isinstance(obj, list):
        for it in obj:
            scores.extend(_extract_scores(it))
    return scores

def build_average_sentiment():
    used_inputs = []
    by_source = {}
    all_scores = []

    # --- Config (simple & robuste) ---
    # Clamp Telegram to reduce hype/noise
    TELEGRAM_CLAMP = (-0.6, 0.6)

    # Weight sources (institutional-ish): reddit slightly higher, telegram lower
    SOURCE_WEIGHTS = {
        "telegram_scored": 0.30,
        "twitter_scored": 0.30,
        "reddit_scored": 0.40,
    }

    def _clamp(v: float, lo: float, hi: float) -> float:
        return lo if v < lo else hi if v > hi else v

    per_source_avgs = {}

    for pth in INPUT_CANDIDATES:
        if not pth.exists():
            continue
        data = load_json_file(str(pth), default=None)
        scores = _extract_scores(data)
        if not scores:
            continue

        used_inputs.append(str(pth))

        # src = filename sans extension (telegram_data_scored -> telegram_scored)
        src = pth.stem.replace("_data", "").replace("_scored", "_scored")

        # Telegram clamp (only on scored telegram)
        if src.startswith("telegram_scored"):
            lo, hi = TELEGRAM_CLAMP
            scores = [_clamp(float(x), lo, hi) for x in scores]

        avg = sum(scores) / len(scores)
        per_source_avgs[src] = avg
        by_source[src] = avg
        all_scores.extend(scores)

    # Si rien trouvé -> on écrit un payload explicite (pas juste {})
    if not all_scores:
        payload = {
            "overall": 0.0,
            "by_source": {},
            "counts": {"total": 0},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "empty",
            "used_inputs": [],
            "notes": ["No sentiment scores found in inputs; check scrapers/sentiment fields."],
        }
        return payload

    # Weighted overall (fallback to simple mean if weights mismatch)
    wsum = 0.0
    wtot = 0.0
    for src, avg in per_source_avgs.items():
        w = SOURCE_WEIGHTS.get(src)
        if w is None:
            continue
        wsum += w * avg
        wtot += w

    overall = (wsum / wtot) if wtot > 0 else (sum(all_scores) / len(all_scores))

    payload = {
        "overall": overall,
        "by_source": by_source,
        "counts": {"total": len(all_scores)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "used_inputs": used_inputs,
        "method": {
            "overall": "weighted_by_source" if wtot > 0 else "mean_all_scores",
            "telegram_clamp": TELEGRAM_CLAMP,
            "weights": SOURCE_WEIGHTS,
        },
    }
    return payload

    payload = {
        "overall": sum(all_scores) / len(all_scores),
        "by_source": by_source,
        "counts": {"total": len(all_scores)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "used_inputs": used_inputs,
    }
    return payload

def run():
    payload = build_average_sentiment()
    save_json_file(str(PRIMARY_OUT), payload)
    save_json_file(str(REPORTS_OUT), payload)
    logger.info(f"✅ average_sentiment written: primary={PRIMARY_OUT} reports={REPORTS_OUT} status={payload.get('status')}")
    return payload

if __name__ == "__main__":
    run()
