import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("sentiment_scorer_offline")

DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")

# Inputs "vivants" (constatés chez toi)
APP_DATA_DIR = Path("/opt/nsc/app/data")
INPUTS = [
    APP_DATA_DIR / "telegram_data.json",
    APP_DATA_DIR / "twitter_data.json",
    APP_DATA_DIR / "reddit_data.json",
]

OUT_DIR = Path(DATA_DIR) / "monitoring_scored"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Garde-fous perf (reddit peut être énorme)
MAX_FILE_MB = 25         # au-delà: on skip pour éviter de charger des JSON massifs
MAX_ITEMS_PER_FILE = 15000  # si list: on score seulement les N derniers

# Lexique simple (tu pourras l’affiner ensuite)
POS_WORDS = {
    "bull", "bullish", "pump", "pumping", "breakout", "moon", "mooning", "uptrend",
    "buy", "long", "accumulate", "strong", "support", "rebound", "rally", "green",
    "ATH", "up", "winner", "good", "great", "excellent", "profit"
}
NEG_WORDS = {
    "bear", "bearish", "dump", "dumping", "breakdown", "crash", "downtrend",
    "sell", "short", "weak", "resistance", "rejection", "rug", "scam", "red",
    "down", "loser", "bad", "terrible", "panic", "liquidation"
}

POS_EMOJI = {"🚀", "🟢", "✅", "📈", "🔥", "💎", "🤑"}
NEG_EMOJI = {"🔻", "🔴", "❌", "📉", "💀", "😱", "🧨"}

WORD_RE = re.compile(r"[A-Za-z]{2,}")

def score_text(txt: str) -> float:
    if not txt:
        return 0.0
    t = txt.lower()

    words = WORD_RE.findall(t)
    if not words:
        # emojis only / symbols only
        pos_e = sum(e in txt for e in POS_EMOJI)
        neg_e = sum(e in txt for e in NEG_EMOJI)
        if pos_e == 0 and neg_e == 0:
            return 0.0
        raw = pos_e - neg_e
        return max(-1.0, min(1.0, raw / 3.0))

    pos = sum(w in POS_WORDS for w in words)
    neg = sum(w in NEG_WORDS for w in words)

    # emojis weight
    pos += sum(e in txt for e in POS_EMOJI)
    neg += sum(e in txt for e in NEG_EMOJI)

    if pos == 0 and neg == 0:
        return 0.0

    raw = pos - neg
    denom = max(3.0, pos + neg)  # normalisation
    s = raw / denom
    return max(-1.0, min(1.0, float(s)))

def _iter_messages(obj):
    # support: list[dict], dict{"messages":[...]} etc.
    if isinstance(obj, list):
        for it in obj:
            yield it
    elif isinstance(obj, dict):
        if isinstance(obj.get("messages"), list):
            for it in obj["messages"]:
                yield it
        elif isinstance(obj.get("data"), list):
            for it in obj["data"]:
                yield it
        else:
            yield obj

def run():
    ts = datetime.now(timezone.utc).isoformat()
    results = {"generated_at": ts, "files": [], "skipped": []}

    for inp in INPUTS:
        if not inp.exists():
            results["skipped"].append({"file": str(inp), "reason": "missing"})
            continue

        size_mb = inp.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_MB:
            results["skipped"].append({"file": str(inp), "reason": f"too_large_mb>{MAX_FILE_MB}", "size_mb": round(size_mb, 2)})
            continue

        data = load_json_file(str(inp), default=None)
        if data is None:
            results["skipped"].append({"file": str(inp), "reason": "load_failed"})
            continue

        # Collect messages
        items = list(_iter_messages(data))

        # On prend les N derniers si gros
        if len(items) > MAX_ITEMS_PER_FILE:
            items = items[-MAX_ITEMS_PER_FILE:]

        scored = []
        n_scored = 0
        for m in items:
            if not isinstance(m, dict):
                continue
            txt = m.get("text") or m.get("content") or m.get("message")
            s = score_text(txt if isinstance(txt, str) else "")
            mm = dict(m)
            mm["sentiment"] = s
            scored.append(mm)
            n_scored += 1

        out = OUT_DIR / inp.name.replace(".json", "_scored.json")
        save_json_file(str(out), scored)

        results["files"].append({
            "input": str(inp),
            "output": str(out),
            "n_scored": n_scored,
            "size_mb": round(size_mb, 2),
        })
        logger.info(f"✅ scored {n_scored} msgs -> {out}")

    save_json_file(str(OUT_DIR / "sentiment_scoring_run.json"), results)
    logger.info(f"✅ sentiment scoring done: files={len(results['files'])} skipped={len(results['skipped'])}")
    return results

if __name__ == "__main__":
    run()
