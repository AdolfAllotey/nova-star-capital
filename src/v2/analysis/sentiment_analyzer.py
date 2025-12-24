# src/v2/analysis/sentiment_analyzer.py
from __future__ import annotations

import os
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

logger = get_logger("sentiment_analyzer")

# --- Paths / env ---
DATA_DIR = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_ROOT") or "data"
STATE_DIR = os.path.join(DATA_DIR, "state")
CONFIG_DIR = os.path.join(DATA_DIR, "config")

SOCIAL_FEED_PATH = os.path.join(DATA_DIR, "social_feed.json")
TG_PATH = os.path.join(DATA_DIR, "telegram_data.json")
TW_PATH = os.path.join(DATA_DIR, "twitter_data.json")
RD_PATH = os.path.join(DATA_DIR, "reddit_data.json")

OUT_PATH = os.path.join(DATA_DIR, "sentiment_overview.json")
STATE_PATH = os.path.join(STATE_DIR, "sentiment_state.json")

# --- Config ---
SENTIMENT_ENABLED = os.getenv("SENTIMENT_ENABLED", "1").lower() in ("1", "true", "yes", "on")
MAX_ITEMS = int(os.getenv("SENTIMENT_MAX_ITEMS", "4000"))
TOP_N_TOKENS = int(os.getenv("SENTIMENT_TOP_TOKENS", "50"))

# token extraction tuning
MIN_TOKEN_LEN = int(os.getenv("SENTIMENT_MIN_TOKEN_LEN", "2"))
MAX_TOKEN_LEN = int(os.getenv("SENTIMENT_MAX_TOKEN_LEN", "10"))
ALLOW_NUMERIC_TOKENS = os.getenv("SENTIMENT_ALLOW_NUMERIC_TOKENS", "0").lower() in ("1", "true", "yes", "on")

# --- Lexicon (simple + efficace) ---
POS_WORDS = {
    "bull", "bullish", "buy", "long", "moon", "pump", "breakout", "support",
    "accumulate", "accumulation", "win", "profit", "profits", "gain", "gains",
    "good", "great", "strong", "up", "green", "rebound", "recover", "recovery",
    "target", "targets", "tp", "takeprofit", "take-profit",
}
NEG_WORDS = {
    "bear", "bearish", "sell", "short", "dump", "crash", "breakdown", "resistance",
    "loss", "losses", "bad", "weak", "down", "red", "rug", "scam", "rekt",
    "stop", "sl", "stoploss", "stop-loss", "liquidation", "liquidated",
}

# --- Anti-noise filters (très important pour virer HTTPS/COM/HREF/etc.) ---
NOISE_TOKENS = {
    # URL/HTML
    "HTTP", "HTTPS", "WWW", "COM", "ORG", "NET", "IO", "GG", "APP",
    "HREF", "HTML", "BODY", "TITLE", "DIV", "SPAN", "IMG", "SRC",
    # reddit / markup
    "REDDIT", "SUBREDDIT", "SUBMITTED", "COMMENTS", "COMMENT", "POST", "THREAD",
    "UPVOTE", "DOWNVOTE",
    # generic english junk
    "THE", "AND", "FOR", "WITH", "THIS", "THAT", "FROM", "WHAT", "WHEN", "WHERE",
    "HERE", "THERE", "YOUR", "YOU", "ARE", "WAS", "WERE", "HAVE", "HAS", "HAD",
    "CAN", "COULD", "SHOULD", "WOULD", "WILL", "NOW", "ALL", "ANY", "NOT",
    "IN", "ON", "AT", "BY", "TO", "OF", "AS", "IS", "IT", "OR",
    # trading generic words (pas des tokens)
    "SIGNAL", "SIGNALS", "ENTRY", "ENTRIES", "TARGET", "TARGETS",
    "TAKE", "PROFIT", "FUTURES", "MARKET", "CRYPTO",
    "VIP", "PREMIUM", "JOIN",
}

# majors fallback (quand selected_tokens.json est absent)
MAJOR_TOKENS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "MATIC", "DOGE", "SHIB",
    "LINK", "NEAR", "DOT", "ATOM", "LTC", "ARB", "OP", "APT", "SUI", "INJ",
    "PEPE", "TRX", "UNI", "AAVE", "FTM",
    "USDT", "USDC", "DAI",
}

RE_WORD = re.compile(r"[A-Za-z0-9$]{2,}")
RE_DOLLAR_TICKER = re.compile(r"\$([A-Za-z]{2,10})\b")
RE_UPPER = re.compile(r"\b([A-Z]{2,10})\b")


def _now_ts() -> int:
    return int(time.time())


def _bucket(score: float) -> str:
    if score >= 0.25:
        return "positive"
    if score <= -0.25:
        return "negative"
    return "neutral"


def _safe_get_text(item: Any) -> str:
    if isinstance(item, dict):
        # normalisé
        if isinstance(item.get("text"), str):
            return item.get("text") or ""
        # twitter raw v2 (au cas où)
        if isinstance(item.get("data"), dict) and isinstance(item["data"].get("text"), str):
            return item["data"]["text"] or ""
        # reddit fallback
        for k in ("title", "selftext", "body", "message"):
            if isinstance(item.get(k), str):
                return item.get(k) or ""
    if isinstance(item, str):
        return item
    return ""


def _safe_get_source(item: Any, default: str = "unknown") -> str:
    if isinstance(item, dict):
        s = item.get("source")
        if isinstance(s, str) and s:
            return s
    return default


def _load_selected_tokens() -> List[str]:
    """
    Supporte:
      - data/selected_tokens.json
      - data/config/selected_tokens.json
    Formats acceptés:
      - ["BTC","ETH",...]
      - {"tokens":[...]}
      - {"selected_tokens":[...]}
    """
    candidates = [
        os.path.join(DATA_DIR, "selected_tokens.json"),
        os.path.join(CONFIG_DIR, "selected_tokens.json"),
    ]
    for p in candidates:
        obj = load_json_file(p, default=None)
        if not obj:
            continue
        if isinstance(obj, list):
            return [str(x).upper().strip() for x in obj if str(x).strip()]
        if isinstance(obj, dict):
            for k in ("tokens", "selected_tokens"):
                if isinstance(obj.get(k), list):
                    return [str(x).upper().strip() for x in obj[k] if str(x).strip()]
    return []


def _is_valid_token(tok: str) -> bool:
    if not tok:
        return False
    tok = tok.strip().upper()
    if len(tok) < MIN_TOKEN_LEN or len(tok) > MAX_TOKEN_LEN:
        return False
    if not ALLOW_NUMERIC_TOKENS and any(ch.isdigit() for ch in tok):
        return False
    if tok in NOISE_TOKENS:
        return False
    # reject obvious url-ish fragments
    if tok.startswith("HTTP") or tok in {"WWW", "COM", "ORG", "NET"}:
        return False
    # reject pure numbers
    if tok.isdigit():
        return False
    return True


def _extract_tokens(text: str, selected_set: Optional[set] = None) -> List[str]:
    """
    Extraction propre:
      1) $TICKER
      2) si selected_set: match exact (BTC, ETH...) en word boundary
      3) fallback: tokens UPPER filtrés + majors
    """
    if not text:
        return []

    text = text.replace("\n", " ").replace("\r", " ")
    out: List[str] = []

    # 1) $TICKER
    for m in RE_DOLLAR_TICKER.findall(text):
        t = m.upper().strip()
        if _is_valid_token(t):
            out.append(t)

    # 2) selected tokens (si disponibles)
    if selected_set:
        # scan rapide via UPPER words
        for m in RE_UPPER.findall(text):
            t = m.upper().strip()
            if t in selected_set and _is_valid_token(t):
                out.append(t)

    # 3) fallback UPPER + majors
    for m in RE_UPPER.findall(text):
        t = m.upper().strip()
        if _is_valid_token(t):
            # on évite de compter “LONG/SHORT/TP/SL” etc. via NOISE_TOKENS
            out.append(t)

    # petit boost: si le texte contient un major en minuscule, on le capte aussi
    lower = text.lower()
    for t in MAJOR_TOKENS:
        if t.lower() in lower:
            if _is_valid_token(t):
                out.append(t)

    # dédup locale
    if not out:
        return []
    # garder l'ordre (stable)
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _score_sentiment(text: str) -> float:
    """
    Score dans [-1..+1] approx, basé sur lexique.
    Simple mais stable pour PREPROD.
    """
    if not text:
        return 0.0

    words = [w.lower() for w in RE_WORD.findall(text)]
    if not words:
        return 0.0

    pos = 0
    neg = 0
    for w in words:
        if w in POS_WORDS:
            pos += 1
        elif w in NEG_WORDS:
            neg += 1

    if pos == 0 and neg == 0:
        return 0.0

    raw = (pos - neg) / max(1, (pos + neg))
    # clamp
    if raw > 1:
        raw = 1.0
    if raw < -1:
        raw = -1.0
    return float(raw)


def _load_items() -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Retourne (items_normalisés, counts_by_source)
    items: [{source, ts, text, ...}]
    """
    # 1) social_feed.json
    sf = load_json_file(SOCIAL_FEED_PATH, default=None)
    if isinstance(sf, dict) and isinstance(sf.get("items"), list):
        items = sf["items"]
        norm: List[Dict[str, Any]] = []
        counts = {"telegram": 0, "twitter": 0, "reddit": 0, "unknown": 0}
        for it in items[:MAX_ITEMS]:
            if not isinstance(it, dict):
                continue
            src = _safe_get_source(it)
            text = _safe_get_text(it)
            ts = it.get("ts")
            try:
                ts_i = int(ts) if ts is not None else None
            except Exception:
                ts_i = None
            if not text:
                continue
            norm.append({
                "source": src,
                "ts": ts_i,
                "text": text,
                "chat_id": it.get("chat_id"),
                "chat_title": it.get("chat_title"),
                "message_id": it.get("message_id"),
                "url": it.get("url"),
                "id": it.get("id"),
            })
            if src in counts:
                counts[src] += 1
            else:
                counts["unknown"] += 1
        return norm, counts

    # 2) fallback: raw files
    norm: List[Dict[str, Any]] = []
    counts = {"telegram": 0, "twitter": 0, "reddit": 0, "unknown": 0}

    for src, path in (("telegram", TG_PATH), ("twitter", TW_PATH), ("reddit", RD_PATH)):
        obj = load_json_file(path, default=[])
        items: List[Any] = []
        if isinstance(obj, list):
            items = obj
        elif isinstance(obj, dict):
            # parfois: {"data":[...]} ou {"items":[...]}
            for k in ("items", "data", "results"):
                if isinstance(obj.get(k), list):
                    items = obj[k]
                    break
        for it in items[:MAX_ITEMS]:
            text = _safe_get_text(it)
            if not text:
                continue
            norm.append({"source": src, "ts": None, "text": text})
            counts[src] += 1

    return norm, counts


def analyze_sentiment() -> Dict[str, Any]:
    if not SENTIMENT_ENABLED:
        logger.info("Sentiment: disabled (SENTIMENT_ENABLED=0)")
        return {}

    ensure_dir(DATA_DIR)
    ensure_dir(STATE_DIR)

    items, counts_by_source = _load_items()
    total = len(items)

    selected = _load_selected_tokens()
    selected_set = set([t for t in selected if _is_valid_token(t)])

    token_counter: Counter = Counter()
    bucket_counter: Counter = Counter()

    sum_score = 0.0
    scored = 0

    # optionnel: top examples
    examples_pos: List[Dict[str, Any]] = []
    examples_neg: List[Dict[str, Any]] = []

    for it in items:
        text = it.get("text") or ""
        score = _score_sentiment(text)
        b = _bucket(score)
        bucket_counter[b] += 1

        sum_score += score
        scored += 1

        toks = _extract_tokens(text, selected_set=selected_set if selected_set else None)
        for t in toks:
            if _is_valid_token(t):
                # si selected_set existe, on privilégie les tokens du set (sinon on garde la heuristique)
                if selected_set and t not in selected_set:
                    # autorise quand même les majors
                    if t not in MAJOR_TOKENS:
                        continue
                token_counter[t] += 1

        # mini exemples (best effort)
        if score >= 0.6 and len(examples_pos) < 5:
            examples_pos.append({"source": it.get("source"), "score": round(score, 3), "text": text[:300]})
        if score <= -0.6 and len(examples_neg) < 5:
            examples_neg.append({"source": it.get("source"), "score": round(score, 3), "text": text[:300]})

    avg = (sum_score / scored) if scored > 0 else 0.0
    avg_bucket = _bucket(avg)

    top_tokens = [
        {"token": tok, "mentions": int(cnt)}
        for tok, cnt in token_counter.most_common(TOP_N_TOKENS)
    ]

    overview = {
        "generated_at": _now_ts(),
        "counts": {
            "total": total,
            "by_source": counts_by_source,
            "by_bucket": {
                "positive": int(bucket_counter.get("positive", 0)),
                "neutral": int(bucket_counter.get("neutral", 0)),
                "negative": int(bucket_counter.get("negative", 0)),
            },
        },
        "sentiment": {
            "avg_score": round(float(avg), 3),
            "bucket": avg_bucket,
        },
        "top_tokens": top_tokens,
        "debug": {
            "selected_tokens_loaded": len(selected_set),
            "max_items": MAX_ITEMS,
            "examples_positive": examples_pos,
            "examples_negative": examples_neg,
        },
    }

    state = {
        "updated_at": _now_ts(),
        "total": total,
        "avg_score": round(float(avg), 3),
        "bucket": avg_bucket,
    }

    save_json_file(OUT_PATH, overview)
    save_json_file(STATE_PATH, state)

    logger.info(
        "Sentiment OK: total=%d avg=%.3f bucket=%s (tg=%d tw=%d rd=%d) -> %s",
        total,
        float(avg),
        avg_bucket,
        counts_by_source.get("telegram", 0),
        counts_by_source.get("twitter", 0),
        counts_by_source.get("reddit", 0),
        OUT_PATH,
    )

    return overview


def main() -> None:
    analyze_sentiment()


if __name__ == "__main__":
    main()
