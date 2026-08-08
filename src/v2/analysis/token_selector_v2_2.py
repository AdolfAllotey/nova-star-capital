from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

DATA_DIR = Path("/opt/nsc/data/preprod")
OUTPUT_PATH = DATA_DIR / "trading" / "selected_tokens.dynamic.json"

TELEGRAM_SCORED_PATH = DATA_DIR / "monitoring_scored" / "telegram_data_scored.json"
TWITTER_SCORED_PATH = DATA_DIR / "monitoring_scored" / "twitter_data_scored.json"
REDDIT_SCORED_PATH = DATA_DIR / "monitoring_scored" / "reddit_data_scored.json"
TOP_MOVERS_PATH = DATA_DIR / "market" / "top_movers_combined.json"

TOKEN_MAP_PATHS = [
    DATA_DIR / "config" / "token_exchange_map.json",
    Path("/opt/nsc/app/src/v2/data/token_exchange_map.json"),
    Path("/opt/nsc/app/src/v2/config/token_exchange_map.json"),
]

EXCLUDED_STABLES = {
    "USDT", "USDC", "DAI", "EUR", "USD", "FDUSD", "TUSD", "USDE"
}

EXCLUDED_LT = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "AVAX", "MATIC"
}

TOP_N = int(__import__("os").getenv("NSC_TOKEN_SELECTOR_TOP_N", "0"))  # 0 = unlimited
MIN_MENTIONS = 15

W_MENTIONS = 0.50
W_SENTIMENT = 0.30
W_SOURCE_DIVERSITY = 0.20

ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "POLYGON": "MATIC",
    "CHAINLINK": "LINK",
    "OPTIMISM": "OP",
}

NOISE_TERMS = {
    "HTTPS", "HTTP", "WWW", "COM", "USER", "USERS", "COMMENT", "COMMENTS",
    "REDDIT", "TELEGRAM", "TWITTER", "POST", "POSTS", "TITLE",
    "SUBMITTED", "CRYPTOCURRENCY", "HTML", "DIV", "TABLE", "SPAN", "A",
    "IMG", "TRUE", "FALSE", "NONE", "AND", "THE", "FOR", "WITH", "THIS",
    "THAT", "FROM", "YOUR", "YOU", "ARE", "BUT", "NOT", "ALL", "CAN",
    "HAS", "HAVE", "WILL", "MORE", "LESS", "VERY", "JUST", "ABOUT", "BY"
}

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HTML_RE = re.compile(r"<[^>]+>")
NON_ALNUM_RE = re.compile(r"[^A-Z0-9\s]")
MULTISPACE_RE = re.compile(r"\s+")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_token(token: str) -> str:
    t = str(token or "").strip().upper()
    t = ALIASES.get(t, t)
    if t.endswith("USDT") and len(t) > 4:
        t = t[:-4]
    return t


def load_allowed_tokens() -> Set[str]:
    allowed: Set[str] = set()

    for path in TOKEN_MAP_PATHS:
        data = load_json(path, default={}) or {}
        if not isinstance(data, dict):
            continue

        for key in data.keys():
            token = normalize_token(str(key))
            if not token:
                continue
            if token in EXCLUDED_STABLES:
                continue
            if token in EXCLUDED_LT:
                continue
            if token in NOISE_TERMS:
                continue
            if len(token) < 2 or len(token) > 10:
                continue
            allowed.add(token)

    return allowed


def clean_text(text: str) -> str:
    s = str(text or "")
    s = URL_RE.sub(" ", s)
    s = HTML_RE.sub(" ", s)
    s = s.upper()

    for raw, norm in ALIASES.items():
        s = s.replace(raw, f" {norm} ")

    s = NON_ALNUM_RE.sub(" ", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s


def extract_tokens_from_text(text: str, allowed_tokens: Set[str]) -> Set[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return set()

    words = set(cleaned.split())
    out = set()

    for word in words:
        token = normalize_token(word)
        if token in NOISE_TERMS:
            continue
        if token in allowed_tokens:
            out.add(token)

    return out


def iter_scored_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for source_name, path in (
        ("telegram", TELEGRAM_SCORED_PATH),
        ("twitter", TWITTER_SCORED_PATH),
        ("reddit", REDDIT_SCORED_PATH),
    ):
        data = load_json(path, default=[]) or []
        if not isinstance(data, list):
            continue

        for row in data:
            if not isinstance(row, dict):
                continue

            text_parts = [
                row.get("title"),
                row.get("text"),
                row.get("message"),
                row.get("content"),
            ]
            text = " ".join(str(x) for x in text_parts if x)

            if not text.strip():
                continue

            try:
                sentiment = float(row.get("sentiment", 0.0) or 0.0)
            except Exception:
                sentiment = 0.0

            rows.append({
                "source": source_name,
                "text": text,
                "sentiment": max(-1.0, min(1.0, sentiment)),
            })

    return rows




def load_market_movers() -> Dict[str, Any]:
    data = load_json(TOP_MOVERS_PATH, default={}) or {}
    items = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []

    gainers = []
    losers = []

    for it in items:
        if not isinstance(it, dict):
            continue
        # Market momentum must only use tradable NSC assets.
        # External / observation-only movers remain useful for review,
        # but must not create synthetic executable pairs.
        if it.get("observation_only") is True:
            continue
        if it.get("tradable") is False:
            continue
        if not it.get("pair"):
            continue

        token = normalize_token(it.get("symbol", ""))
        if not token or token in EXCLUDED_STABLES or token in EXCLUDED_LT:
            continue
        if not token.isascii() or not token.replace("_", "").isalnum():
            continue

        try:
            chg_24h = float(it.get("chg_24h") or 0.0)
        except Exception:
            chg_24h = 0.0

        row = {
            "token": token,
            "symbol": token,
            "pair": it.get("pair") or f"{token}USDT",
            "chg_24h": chg_24h,
            "price": it.get("price"),
            "source": it.get("source", "market_movers"),
        }

        if chg_24h >= 15.0:
            gainers.append(row)
        elif chg_24h <= -15.0:
            losers.append(row)

    gainers.sort(key=lambda x: x["chg_24h"], reverse=True)
    losers.sort(key=lambda x: x["chg_24h"])

    return {
        "updated_at": data.get("updated_at") if isinstance(data, dict) else None,
        "source_file": str(TOP_MOVERS_PATH),
        "gainers": gainers,
        "losers": losers,
    }


def build_selection() -> Dict[str, Any]:
    rows = iter_scored_rows()
    allowed_tokens = load_allowed_tokens()

    token_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "mentions": 0,
        "sentiment_sum": 0.0,
        "sources": set(),
        "source_mentions": defaultdict(int),
    })

    source_input_counts = {"telegram": 0, "twitter": 0, "reddit": 0}
    source_hit_counts = {"telegram": 0, "twitter": 0, "reddit": 0}

    for row in rows:
        source = row["source"]
        source_input_counts[source] += 1

        tokens = extract_tokens_from_text(row["text"], allowed_tokens=allowed_tokens)
        if not tokens:
            continue

        source_hit_counts[source] += 1
        sentiment = row["sentiment"]

        for token in tokens:
            token_stats[token]["mentions"] += 1
            token_stats[token]["sentiment_sum"] += sentiment
            token_stats[token]["sources"].add(source)
            token_stats[token]["source_mentions"][source] += 1

    filtered: List[Dict[str, Any]] = []

    for token, stats in token_stats.items():
        mentions = int(stats["mentions"])
        if mentions < MIN_MENTIONS:
            continue

        avg_sentiment = stats["sentiment_sum"] / mentions if mentions > 0 else 0.0
        source_count = len(stats["sources"])

        filtered.append({
            "token": token,
            "mentions": mentions,
            "avg_sentiment": round(avg_sentiment, 4),
            "source_count": source_count,
            "sources": sorted(stats["sources"]),
            "source_mentions": dict(stats["source_mentions"]),
        })

    filtered.sort(
        key=lambda x: (x["mentions"], x["avg_sentiment"], x["source_count"]),
        reverse=True
    )

    market_movers = load_market_movers()
    market_gainers = market_movers.get("gainers", [])
    market_losers = market_movers.get("losers", [])

    # Add market momentum candidates even when social mentions are low/missing.
    existing_tokens = {x["token"] for x in filtered if isinstance(x, dict) and x.get("token")}
    for mover in market_gainers:
        token = mover.get("token")
        if not token or token in existing_tokens:
            continue
        filtered.append({
            "token": token,
            "mentions": 0,
            "avg_sentiment": 0.0,
            "source_count": 1,
            "sources": ["market_movers"],
            "source_mentions": {"market_movers": 1},
            "market_momentum": True,
            "chg_24h": mover.get("chg_24h"),
            "pair": mover.get("pair"),
        })
        existing_tokens.add(token)

    filtered.sort(
        key=lambda x: (
            bool(x.get("market_momentum", False)),
            float(x.get("chg_24h") or 0.0),
            x["mentions"],
            x["avg_sentiment"],
            x["source_count"],
        ),
        reverse=True
    )

    top_candidates = filtered if TOP_N <= 0 else filtered[:TOP_N]
    max_mentions = max((x["mentions"] for x in top_candidates), default=1)

    selected: List[Dict[str, Any]] = []

    for row in top_candidates:
        mentions = int(row["mentions"])
        avg_sentiment = float(row["avg_sentiment"])
        source_count = int(row["source_count"])

        mentions_score = (mentions / max_mentions) * 100.0 if max_mentions > 0 else 0.0
        sentiment_score = ((avg_sentiment + 1.0) / 2.0) * 100.0
        source_diversity_score = (source_count / 3.0) * 100.0

        final_score = (
            W_MENTIONS * mentions_score
            + W_SENTIMENT * sentiment_score
            + W_SOURCE_DIVERSITY * source_diversity_score
        )

        selected.append({
            "token": row["token"],
            "mentions": mentions,
            "score": round(max(1.0, min(100.0, final_score)), 2),
            "relative_strength": round(mentions / max_mentions, 4) if max_mentions > 0 else 0.0,
            "avg_sentiment": round(avg_sentiment, 4),
            "source_count": source_count,
            "sources": row["sources"],
            "source_mentions": row["source_mentions"],
            "score_breakdown": {
                "mentions_score": round(mentions_score, 2),
                "sentiment_score": round(sentiment_score, 2),
                "source_diversity_score": round(source_diversity_score, 2),
            },
            "source": "market_momentum" if row.get("market_momentum") else "scored_social_feeds_v2_2",
            "market_momentum": bool(row.get("market_momentum", False)),
            "chg_24h": row.get("chg_24h"),
            "pair": row.get("pair"),
        })

    payload = {
        "status": "ok",
        "engine": "token_selector_v2_2",
        "source_files": [
            str(TELEGRAM_SCORED_PATH),
            str(TWITTER_SCORED_PATH),
            str(REDDIT_SCORED_PATH),
        ],
        "rules": {
            "top_n": TOP_N,
            "top_n_mode": "unlimited" if TOP_N <= 0 else "limited",
            "min_mentions": MIN_MENTIONS,
            "excluded_stables": sorted(EXCLUDED_STABLES),
            "excluded_lt": sorted(EXCLUDED_LT),
            "weights": {
                "mentions": W_MENTIONS,
                "sentiment": W_SENTIMENT,
                "source_diversity": W_SOURCE_DIVERSITY,
            },
            "score_formula": "0.50*mentions_score + 0.30*sentiment_score + 0.20*source_diversity_score + market_momentum_overlay",
            "market_movers_overlay": {
                "enabled": True,
                "source": str(TOP_MOVERS_PATH),
                "gainer_threshold_24h_pct": 15.0,
                "loser_threshold_24h_pct": -15.0,
                "losers_policy": "watchlist_risk_only"
            },
        },
        "debug": {
            "allowed_tokens_count": len(allowed_tokens),
            "source_input_counts": source_input_counts,
            "source_hit_counts": source_hit_counts,
            "candidate_count_before_top_n": len(filtered),
            "market_gainers_count": len(market_gainers),
            "market_losers_count": len(market_losers),
        },
        "count": len(selected),
        "items": selected,
        "market_movers": market_movers,
    }

    return payload


def main() -> None:
    payload = build_selection()
    save_json(OUTPUT_PATH, payload)

    print(json.dumps({
        "output": str(OUTPUT_PATH),
        "engine": payload["engine"],
        "count": payload["count"],
        "tokens": [x["token"] for x in payload["items"]],
        "scores": {x["token"]: x["score"] for x in payload["items"]},
        "debug": payload.get("debug", {}),
    }, indent=2))


if __name__ == "__main__":
    main()
