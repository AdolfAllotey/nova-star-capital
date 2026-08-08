from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


PORTFOLIO_STATE_PATH = Path("data/capital/portfolio_state.json")
OUTPUT_PATH = Path("data/capital/portfolio_state_normalized.json")

BUCKET_MAP = {
    "crypto": "crypto_trading",
    "crypto_trading": "crypto_trading",
    "crypto_lt": "crypto_lt",

    "equities_offensive": "equities_offensive",
    "equities_defensive": "equities_defensive",
    "equities_lt": "equities_lt",

    "bonds": "bonds",
    "precious_metals": "gold",
    "metals": "gold",
    "gold": "gold",

    "options": "options",
    "options_us": "options",

    "cash": "cash",
    "tax_reserve": "tax_reserve",
    "bfr_reserve": "bfr_reserve",
    "security_reserve": "security_reserve"
}

OFFICIAL_BUCKETS = [
    "crypto_trading",
    "crypto_lt",
    "equities_offensive",
    "equities_defensive",
    "equities_lt",
    "bonds",
    "gold",
    "options",
    "cash",
    "tax_reserve",
    "bfr_reserve",
    "security_reserve"
]


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def normalize_bucket(name: str) -> str:
    return BUCKET_MAP.get(str(name), str(name))


def normalize_amounts(raw: Dict[str, Any]) -> Dict[str, float]:
    out = {k: 0.0 for k in OFFICIAL_BUCKETS}

    for key, value in raw.items():
        bucket = normalize_bucket(key)
        if bucket not in out:
            out[bucket] = 0.0
        out[bucket] += safe_float(value)

    return {k: round(v, 2) for k, v in out.items()}


def normalize_weights_from_amounts(amounts: Dict[str, float], nav: float) -> Dict[str, float]:
    return {
        k: round(v / nav, 6) if nav > 0 else 0.0
        for k, v in amounts.items()
    }


def run() -> Dict[str, Any]:
    state = read_json(PORTFOLIO_STATE_PATH, default={}) or {}

    nav = safe_float(state.get("nav_eur", 0.0))
    raw_target_amounts = state.get("target_amounts_eur", {}) or {}
    raw_current_values = state.get("current_values_eur", {}) or {}

    target_amounts = normalize_amounts(raw_target_amounts)
    current_values = normalize_amounts(raw_current_values)

    target_weights = normalize_weights_from_amounts(target_amounts, nav)
    current_weights = normalize_weights_from_amounts(current_values, nav)

    drift = {
        k: round(current_weights.get(k, 0.0) - target_weights.get(k, 0.0), 6)
        for k in sorted(set(target_weights) | set(current_weights))
    }

    out = {
        "status": "ok",
        "engine": "capital_bucket_mapper_v1",
        "currency": state.get("currency", "EUR"),
        "nav_eur": nav,
        "official_buckets": OFFICIAL_BUCKETS,
        "bucket_map": BUCKET_MAP,
        "target_amounts_eur": target_amounts,
        "current_values_eur": current_values,
        "target_weights": target_weights,
        "current_weights": current_weights,
        "drift": drift,
        "source": str(PORTFOLIO_STATE_PATH),
        "notes": [
            "Normalizes portfolio target/current bucket names before rebalance/funding.",
            "Prevents false drift caused by crypto vs crypto_trading, precious_metals vs gold, options_us vs options."
        ]
    }

    write_json(OUTPUT_PATH, out)
    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
