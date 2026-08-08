from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

import os

DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")
OUTPUT_PATH = DATA_DIR / "trading" / "selected_tokens.dynamic.json"
DISCOVERY_CANDIDATES_PATH = DATA_DIR / "discovery" / "discovery_candidates.json"
TRADABLE_OPPORTUNITIES_PATH = DATA_DIR / "discovery" / "tradable_opportunities.json"

MARKET_MOVERS_PATHS = [
    DATA_DIR / "market" / "top_movers_combined.json",
    DATA_DIR / "market" / "top_movers.json",
    DATA_DIR / "market" / "coingecko_top_movers.json",
    DATA_DIR / "market" / "coinmarketcap_top_movers.json",
    DATA_DIR / "market" / "bitpanda_top_movers.json",
]

TELEGRAM_SCORED_PATH = DATA_DIR / "monitoring_scored" / "telegram_data_scored.json"
TWITTER_SCORED_PATH = DATA_DIR / "monitoring_scored" / "twitter_data_scored.json"
REDDIT_SCORED_PATH = DATA_DIR / "monitoring_scored" / "reddit_data_scored.json"

TOKEN_MAP_PATHS = [
    Path("/opt/nsc/app/src/v2/data/token_exchange_map.json"),
    Path("/opt/nsc/app/src/v2/config/token_exchange_map.json"),
]

EXCLUDED_STABLES = {
    "USDT", "USDC", "DAI", "EUR", "USD", "FDUSD", "TUSD", "USDE"
}

EXCLUDED_LT = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "AVAX", "MATIC"
}

TOP_N = 8
MIN_MENTIONS = 15

MARKET_MOVERS_PATH = DATA_DIR / "market" / "top_movers_combined.json"
MARKET_GAINER_THRESHOLD_24H = 15.0
MARKET_LOSER_THRESHOLD_24H = -15.0

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






def load_tradable_opportunities() -> list[dict]:
    raw = load_json(TRADABLE_OPPORTUNITIES_PATH, default={}) or {}
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []

    out = []
    for row in items:
        symbol = str(row.get("symbol") or "").upper().strip()
        pair = str(row.get("pair") or f"{symbol}USDT").upper().strip()
        score = float(row.get("opportunity_score") or 0.0)
        chg_24h = float(row.get("chg_24h") or 0.0)

        if not symbol or not pair.endswith("USDT"):
            continue

        out.append({
            "token": symbol,
            "pair": pair,
            "market_momentum": True,
            "chg_24h": chg_24h,
            "score": round(score, 2),
            "opportunity_score": round(score, 2),
            "source": "tradable_opportunity_v1",
            "sources": row.get("tradable_sources") or row.get("sources") or [],
        })

    return out


def load_discovery_candidates() -> list[dict]:
    raw = load_json(DISCOVERY_CANDIDATES_PATH, default={}) or {}
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []

    out = []
    tradable_sources = {"binance", "mexc"}

    for row in items:
        try:
            symbol = str(row.get("symbol", "")).upper().strip()
            chg_24h = float(row.get("chg_24h") or 0.0)
            discovery_score = float(row.get("discovery_score") or 0.0)
            pair = str(row.get("pair") or "").upper().strip()
            sources = set(row.get("discovery_sources") or row.get("sources") or [])

            if not symbol:
                continue
            if chg_24h < 30.0 or chg_24h > 60.0:
                continue
            if not pair.endswith("USDT"):
                continue
            if not sources.intersection(tradable_sources):
                continue

            out.append({
                "token": symbol,
                "pair": pair,
                "market_momentum": True,
                "chg_24h": chg_24h,
                "score": round(discovery_score, 2),
                "discovery_score": round(discovery_score, 2),
                "source": "market_discovery_v1",
            })
        except Exception:
            continue

    out.sort(key=lambda x: float(x.get("discovery_score") or 0.0), reverse=True)
    return out


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



def load_market_movers_overlay(allowed_tokens: Set[str]) -> Dict[str, Any]:
    raw = load_json(MARKET_MOVERS_PATH, default={}) or {}

    if isinstance(raw, dict):
        items = raw.get("items") or raw.get("gainers") or []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    gainers = []
    losers = []

    for it in items:
        if not isinstance(it, dict):
            continue

        token = normalize_token(it.get("symbol") or it.get("token") or it.get("id"))
        if not token:
            continue
        if token in EXCLUDED_STABLES or token in EXCLUDED_LT or token in NOISE_TERMS:
            continue
        # Market movers come from exchange-validated data.
        # Do not require presence in token_exchange_map if the mover is explicitly tradable.
        if allowed_tokens and token not in allowed_tokens and not bool(it.get("tradable", False)):
            continue

        try:
            chg_24h = float(it.get("chg_24h") or 0.0)
        except Exception:
            chg_24h = 0.0

        pair = it.get("pair") or f"{token}USDT"
        price = it.get("price")
        tradable = bool(it.get("tradable", True))
        observation_only = bool(it.get("observation_only", False))

        row = {
            "token": token,
            "symbol": token,
            "pair": pair,
            "chg_24h": chg_24h,
            "price": price,
            "source": it.get("source"),
            "tradable": tradable,
            "observation_only": observation_only,
        }

        if chg_24h >= MARKET_GAINER_THRESHOLD_24H and tradable and not observation_only:
            gainers.append(row)
        elif chg_24h <= MARKET_LOSER_THRESHOLD_24H:
            losers.append(row)

    gainers.sort(key=lambda x: x.get("chg_24h", 0.0), reverse=True)
    losers.sort(key=lambda x: x.get("chg_24h", 0.0))

    return {
        "source_file": str(MARKET_MOVERS_PATH),
        "gainers": gainers,
        "losers": losers,
    }


def load_market_movers() -> Dict[str, Any]:
    gainers = []
    losers = []
    source_files = []

    for path in MARKET_MOVERS_PATHS:
        raw = load_json(path, default=None)
        if raw is None:
            continue

        source_files.append(str(path))

        if isinstance(raw, dict):
            items = raw.get("items") or raw.get("gainers") or raw.get("top_movers") or []
        elif isinstance(raw, list):
            items = raw
        else:
            items = []

        if not isinstance(items, list):
            continue

        for row in items:
            if not isinstance(row, dict):
                continue

            token = normalize_token(row.get("symbol") or row.get("token") or row.get("id") or "")
            pair = row.get("pair") or (f"{token}USDT" if token else None)

            try:
                chg = float(row.get("chg_24h") or row.get("change_24h") or row.get("price_change_percent_24h") or 0.0)
            except Exception:
                chg = 0.0

            if not token or token in EXCLUDED_STABLES or token in EXCLUDED_LT:
                continue

            item = {
                "token": token,
                "symbol": token,
                "pair": pair,
                "chg_24h": chg,
                "price": row.get("price"),
                "source": row.get("source") or path.stem,
                "tradable": row.get("tradable", True),
                "observation_only": row.get("observation_only", False),
            }

            if chg >= 15 and item["tradable"] and not item["observation_only"]:
                gainers.append(item)
            elif chg <= -15:
                losers.append(item)

    gainers.sort(key=lambda x: x["chg_24h"], reverse=True)
    losers.sort(key=lambda x: x["chg_24h"])

    return {
        "source_files": source_files,
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

    top_candidates = filtered[:TOP_N]
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
            "source": "scored_social_feeds_v2_2",
        })

    market_overlay = load_market_movers_overlay(allowed_tokens)

    existing = {x.get("token") for x in selected}
    for m in market_overlay.get("gainers", []):
        token = m.get("token")
        if not token or token in existing:
            continue

        selected.insert(0, {
            "token": token,
            "mentions": 0,
            "score": 21.67,
            "relative_strength": 0.0,
            "avg_sentiment": 0.0,
            "source_count": 1,
            "sources": ["market_movers"],
            "source_mentions": {"market_movers": 1},
            "score_breakdown": {
                "mentions_score": 0.0,
                "sentiment_score": 50.0,
                "source_diversity_score": 33.33,
            },
            "source": "market_momentum",
            "market_momentum": True,
            "chg_24h": m.get("chg_24h"),
            "pair": m.get("pair"),
            "price": m.get("price"),
        })
        existing.add(token)

    market = load_market_movers()

    market_selected = []
    existing_tokens = {x["token"] for x in selected}

    for m in market["gainers"]:
        token = m["token"]
        if token in existing_tokens:
            continue

        market_selected.append({
            "token": token,
            "mentions": 0,
            "score": 21.67,
            "relative_strength": 0.0,
            "avg_sentiment": 0.0,
            "source_count": 1,
            "sources": ["market_movers"],
            "source_mentions": {"market_movers": 1},
            "score_breakdown": {
                "mentions_score": 0.0,
                "sentiment_score": 50.0,
                "source_diversity_score": 33.33,
            },
            "source": "market_momentum",
            "market_momentum": True,
            "chg_24h": m["chg_24h"],
            "pair": m["pair"],
        })
        existing_tokens.add(token)

    selected = market_selected + selected


    tradable_items = load_tradable_opportunities()
    if tradable_items:
        existing = {x.get("token") for x in selected}
        for item in tradable_items[:8]:
            token = item.get("token")
            if token and token not in existing:
                selected.insert(0, item)
                existing.add(token)

    discovery_items = load_discovery_candidates()
    if discovery_items:
        existing = {x.get("token") for x in selected}
        for item in discovery_items[:12]:
            token = item.get("token")
            if token and token not in existing:
                selected.insert(0, item)
                existing.add(token)

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
            "min_mentions": MIN_MENTIONS,
            "market_movers_overlay": {
                "enabled": True,
                "source": str(MARKET_MOVERS_PATH),
                "gainer_threshold_24h_pct": MARKET_GAINER_THRESHOLD_24H,
                "loser_threshold_24h_pct": MARKET_LOSER_THRESHOLD_24H,
                "losers_policy": "watchlist_risk_only",
            },
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
                    "sources": market["source_files"],
                    "gainer_threshold_24h_pct": 15.0,
                    "loser_threshold_24h_pct": -15.0,
                    "losers_policy": "watchlist_risk_only",
                },
        },
        "debug": {
            "allowed_tokens_count": len(allowed_tokens),
            "source_input_counts": source_input_counts,
            "source_hit_counts": source_hit_counts,
            "candidate_count_before_top_n": len(filtered),
            "market_gainers_count": len(market["gainers"]),
            "market_losers_count": len(market["losers"]),
            "market_gainers_count": len(market_overlay.get("gainers", [])),
            "market_losers_count": len(market_overlay.get("losers", [])),
        },
        "count": len(selected),
        "items": selected,
        "market_movers": market,
        "market_movers": market_overlay,
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
        "scores": {x.get("token"): x.get("score", x.get("discovery_score", 0)) for x in payload["items"]},
        "debug": payload.get("debug", {}),
    }, indent=2))


if __name__ == "__main__":
    main()
