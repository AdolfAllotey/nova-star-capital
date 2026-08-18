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



def score_candidate(
    symbol: str,
    rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    RC2 Discovery Execution Coherence V1.

    Separates:

    1. observed market intelligence
       - strongest move seen across discovery sources;

    2. executable market state
       - state seen on a confirmed NSC execution venue;

    3. cross-source coherence
       - observation sources may strengthen discovery;
       - they must never lend their directional momentum
         to another execution venue.

    This preserves external intelligence while preventing
    synthetic execution signals such as:

        Bitpanda: +20%
        Binance : -37%

    from becoming:

        "tradable +20% on Binance".
    """

    sources = sorted({
        str(r.get("source"))
        for r in rows
        if r.get("source")
    })

    # Bitpanda API supersedes historical manual feed.
    if (
        "bitpanda" in sources
        and "bitpanda_manual" in sources
    ):
        sources = [
            source
            for source in sources
            if source != "bitpanda_manual"
        ]

    exchanges = sorted({
        str(r.get("exchange"))
        for r in rows
        if r.get("exchange")
    })

    def _f(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    clean_rows = [
        r for r in rows
        if isinstance(r, dict)
    ]

    if not clean_rows:
        return {
            "symbol": symbol,
            "pair": None,
            "category": "watchlist",
            "discovery_score": 0.0,
            "chg_24h": 0.0,
            "sources_count": 0,
            "discovery_sources": [],
            "exchanges": [],
            "tradable": False,
            "observation_only": True,
            "execution_confirmed": False,
            "execution_pair": None,
            "execution_chg_24h": None,
            "execution_price": None,
            "execution_source": None,
            "execution_sources": [],
            "observed_pair": None,
            "observed_chg_24h": None,
            "observed_source": None,
            "cross_source_direction_conflict": False,
            "cross_source_conflict_details": {},
            "reason": "no usable discovery rows",
            "raw_candidates": [],
        }

    observed_best = max(
        clean_rows,
        key=lambda r: _f(
            r.get("chg_24h"),
            0.0,
        ),
    )

    observed_chg = _f(
        observed_best.get("chg_24h"),
        0.0,
    )

    observed_pair = (
        observed_best.get("pair")
    )

    observed_source = (
        observed_best.get("source")
        or observed_best.get("exchange")
    )

    best_gain = max(
        _f(r.get("chg_24h"), 0.0)
        for r in clean_rows
    )

    worst_drop = min(
        _f(r.get("chg_24h"), 0.0)
        for r in clean_rows
    )

    # Confirmed execution venues for current NSC crypto
    # trading architecture.
    execution_venues = {
        "binance",
        "mexc",
    }

    execution_rows = []

    for row in clean_rows:
        source = str(
            row.get("exchange")
            or row.get("source")
            or ""
        ).lower().strip()

        pair = str(
            row.get("pair")
            or ""
        ).upper().strip()

        tradable = bool(
            row.get("tradable", False)
        )

        observation_only = bool(
            row.get(
                "observation_only",
                False,
            )
        )

        if source not in execution_venues:
            continue

        if not tradable:
            continue

        if observation_only:
            continue

        if not pair.endswith("USDT"):
            continue

        execution_rows.append(row)

    # Deduplicate equivalent records emitted through
    # combined + venue-specific sources.
    dedup_execution = {}

    for row in execution_rows:
        key = (
            str(
                row.get("exchange")
                or row.get("source")
                or ""
            ).lower(),
            str(
                row.get("pair")
                or ""
            ).upper(),
            round(
                _f(
                    row.get("chg_24h"),
                    0.0,
                ),
                8,
            ),
        )

        dedup_execution[key] = row

    execution_rows = list(
        dedup_execution.values()
    )

    execution_confirmed = bool(
        execution_rows
    )

    execution_best = None

    if execution_rows:
        # For long momentum execution, use the strongest
        # state observed among actual execution venues.
        execution_best = max(
            execution_rows,
            key=lambda r: _f(
                r.get("chg_24h"),
                0.0,
            ),
        )

    execution_pair = (
        execution_best.get("pair")
        if execution_best
        else None
    )

    execution_chg = (
        _f(
            execution_best.get("chg_24h"),
            0.0,
        )
        if execution_best
        else None
    )

    execution_price = (
        _f(
            execution_best.get("price"),
            0.0,
        )
        if execution_best
        and execution_best.get("price")
        is not None
        else None
    )

    execution_source = (
        str(
            execution_best.get("exchange")
            or execution_best.get("source")
            or ""
        ).lower()
        if execution_best
        else None
    )

    execution_sources = sorted({
        str(
            r.get("exchange")
            or r.get("source")
            or ""
        ).lower()
        for r in execution_rows
        if (
            r.get("exchange")
            or r.get("source")
        )
    })

    direction_conflict = False

    if (
        execution_confirmed
        and execution_chg is not None
    ):
        direction_conflict = (
            (
                observed_chg > 0
                and execution_chg < 0
            )
            or (
                observed_chg < 0
                and execution_chg > 0
            )
        )

    source_score = min(
        30.0,
        len(sources) * 10.0,
    )

    exchange_score = min(
        20.0,
        len(exchanges) * 10.0,
    )

    momentum_score = 0.0

    if best_gain >= MIN_GAINER_24H:
        momentum_score = min(
            35.0,
            best_gain * 0.7,
        )

    penalty = 0.0

    if best_gain > MAX_GAINER_24H:
        penalty += 20.0

    if worst_drop <= MIN_LOSER_24H:
        penalty += 10.0

    # A true direction disagreement between the discovery
    # observation and the actual execution venue is a major
    # strategic warning.
    if direction_conflict:
        penalty += 25.0

    score = max(
        0.0,
        min(
            100.0,
            35.0
            + source_score
            + exchange_score
            + momentum_score
            - penalty,
        ),
    )

    # Preserve legacy aggregate semantics for chg_24h/pair
    # for intelligence consumers, but publish explicit
    # execution semantics alongside them.
    aggregate_pair = observed_pair

    aggregate_observation_only = all(
        bool(
            r.get(
                "observation_only",
                False,
            )
        )
        for r in clean_rows
    )

    return {
        "symbol": symbol,

        # Legacy / intelligence view
        "pair": aggregate_pair,
        "category": (
            "top_gainer"
            if best_gain >= MIN_GAINER_24H
            else "watchlist"
        ),
        "discovery_score": round(
            score,
            2,
        ),
        "chg_24h": round(
            best_gain,
            4,
        ),

        "sources_count": len(sources),
        "discovery_sources": sources,
        "exchanges": exchanges,

        # Important:
        # tradable now means confirmed on an NSC execution
        # venue, not merely tradable somewhere upstream.
        "tradable": execution_confirmed,

        # Observation-only means no confirmed execution
        # venue is available.
        "observation_only": (
            not execution_confirmed
        ),

        # Explicit observation lineage
        "observed_pair": observed_pair,
        "observed_chg_24h": round(
            observed_chg,
            4,
        ),
        "observed_source": (
            observed_source
        ),

        # Explicit execution lineage
        "execution_confirmed": (
            execution_confirmed
        ),
        "execution_pair": (
            execution_pair
        ),
        "execution_chg_24h": (
            round(execution_chg, 4)
            if execution_chg
            is not None
            else None
        ),
        "execution_price": (
            execution_price
        ),
        "execution_source": (
            execution_source
        ),
        "execution_sources": (
            execution_sources
        ),

        # Cross-source coherence
        "cross_source_direction_conflict": (
            direction_conflict
        ),
        "cross_source_conflict_details": {
            "observed_chg_24h": round(
                observed_chg,
                4,
            ),
            "observed_source": (
                observed_source
            ),
            "observed_pair": (
                observed_pair
            ),
            "execution_chg_24h": (
                round(
                    execution_chg,
                    4,
                )
                if execution_chg
                is not None
                else None
            ),
            "execution_source": (
                execution_source
            ),
            "execution_pair": (
                execution_pair
            ),
        },

        "reason": (
            f"discovery_score={score:.2f}, "
            f"sources={len(sources)}, "
            f"best_gain_24h={best_gain:.2f}%, "
            f"execution_confirmed="
            f"{execution_confirmed}, "
            f"direction_conflict="
            f"{direction_conflict}"
        ),

        "raw_candidates": clean_rows,
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
