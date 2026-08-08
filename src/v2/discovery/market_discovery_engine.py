from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from src.v2.discovery.discovery_utils import (
    get_data_dir,
    load_json,
    save_json,
    normalize_mover,
    utc_now,
)

MIN_GAINER_24H = 15.0
MAX_GAINER_24H = 60.0
MIN_LOSER_24H = -15.0

SOURCE_FILES = {
    "combined": ("market/top_movers_combined.json", "items"),
    "binance": ("market/top_movers.json", "items"),
    "coingecko": ("market/coingecko_top_movers.json", "items"),
    "coinmarketcap": ("market/coinmarketcap_top_movers.json", "items"),
    "bitpanda": ("market/bitpanda_top_movers.json", "items"),
}


def _extract_items(raw: Any, key: str) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        blob = raw.get(key) or raw.get("items") or raw.get("gainers") or []
        if isinstance(blob, list):
            return [x for x in blob if isinstance(x, dict)]
    return []


def collect_source(data_dir: Path, name: str, rel_path: str, key: str) -> Dict[str, Any]:
    path = data_dir / rel_path
    raw = load_json(path, default=None)
    items = _extract_items(raw, key) if raw is not None else []

    candidates = []
    for row in items:
        norm = normalize_mover(row, name)
        if not norm:
            continue
        candidates.append(norm)

    if raw is None:
        status = "missing"
    elif len(candidates) == 0:
        status = "empty"
    else:
        status = "ok"

    out = {
        "status": status,
        "source": name,
        "source_file": str(path),
        "generated_at": utc_now(),
        "count": len(candidates),
        "items": candidates,
    }

    save_json(data_dir / "discovery" / f"{name}_candidates.json", out)
    return out


def score_candidate(symbol: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    sources = sorted({str(r.get("source")) for r in rows if r.get("source")})

    # NSC: Bitpanda API supersedes the historical manual feed.
    # The two labels must never count as independent confirmations.
    if "bitpanda" in sources and "bitpanda_manual" in sources:
        sources = [
            source
            for source in sources
            if source != "bitpanda_manual"
        ]
    exchanges = sorted({str(r.get("exchange")) for r in rows if r.get("exchange")})

    best_gain = max(float(r.get("chg_24h") or 0.0) for r in rows)
    worst_drop = min(float(r.get("chg_24h") or 0.0) for r in rows)

    source_score = min(30.0, len(sources) * 10.0)
    exchange_score = min(20.0, len(exchanges) * 10.0)
    momentum_score = 0.0

    if best_gain >= MIN_GAINER_24H:
        momentum_score = min(35.0, best_gain * 0.7)

    penalty = 0.0
    if best_gain > MAX_GAINER_24H:
        penalty += 20.0
    if worst_drop <= MIN_LOSER_24H:
        penalty += 10.0

    score = max(0.0, min(100.0, 35.0 + source_score + exchange_score + momentum_score - penalty))

    best = sorted(rows, key=lambda x: float(x.get("chg_24h") or 0.0), reverse=True)[0]

    return {
        "symbol": symbol,
        "pair": best.get("pair"),
        "category": "top_gainer" if best_gain >= MIN_GAINER_24H else "watchlist",
        "discovery_score": round(score, 2),
        "chg_24h": round(best_gain, 4),
        "sources_count": len(sources),
        "discovery_sources": sources,
        "exchanges": exchanges,
        "tradable": any(bool(r.get("tradable", True)) for r in rows),
        "observation_only": all(bool(r.get("observation_only", False)) for r in rows),
        "reason": f"discovery_score={score:.2f}, sources={len(sources)}, best_gain_24h={best_gain:.2f}%",
        "raw_candidates": rows,
    }


def run() -> Dict[str, Any]:
    data_dir = get_data_dir()
    discovery_dir = data_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, Any]] = []
    source_states = []

    for name, (rel_path, key) in SOURCE_FILES.items():
        state = collect_source(data_dir, name, rel_path, key)
        source_states.append({
            "source": name,
            "status": state["status"],
            "count": state["count"],
            "source_file": state["source_file"],
        })
        all_rows.extend(state["items"])

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        symbol = row.get("symbol")
        if symbol:
            grouped[symbol].append(row)

    candidates = [score_candidate(symbol, rows) for symbol, rows in grouped.items()]
    candidates.sort(key=lambda x: x.get("discovery_score", 0), reverse=True)

    final = {
        "status": "ok",
        "engine": "market_discovery_engine_v1",
        "generated_at": utc_now(),
        "rules": {
            "min_gainer_24h": MIN_GAINER_24H,
            "max_gainer_24h": MAX_GAINER_24H,
            "min_loser_24h": MIN_LOSER_24H,
        },
        "sources": source_states,
        "count": len(candidates),
        "items": candidates,
    }

    summary = {
        "status": "ok",
        "generated_at": final["generated_at"],
        "engine": final["engine"],
        "sources_active": [s for s in source_states if s["status"] == "ok"],
        "sources_missing": [s for s in source_states if s["status"] != "ok"],
        "candidates_count": len(candidates),
        "top_candidates": [
            {
                "symbol": c["symbol"],
                "score": c["discovery_score"],
                "chg_24h": c["chg_24h"],
                "sources": c["discovery_sources"],
                "reason": c["reason"],
            }
            for c in candidates[:10]
        ],
    }

    save_json(discovery_dir / "discovery_candidates.json", final)
    save_json(discovery_dir / "discovery_summary.json", summary)

    return final


def main() -> None:
    state = run()
    print({
        "output": str(get_data_dir() / "discovery" / "discovery_candidates.json"),
        "engine": state["engine"],
        "count": state["count"],
        "top": [x["symbol"] for x in state["items"][:10]],
    })


if __name__ == "__main__":
    main()
