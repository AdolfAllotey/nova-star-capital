from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"

OUTPUT = DATA / "audits" / "long_term_global_master_strategy_audit.json"

PATHS = {
    "lt_portfolio": DATA / "portfolio/lt_portfolio.json",
    "lt_positions": DATA / "portfolio/long_term_positions.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "capital_policy": DATA / "portfolio/capital_flow_policy.json",
}

EXPECTED_CRYPTO_LT = {
    "BTC": 0.50,
    "ETH": 0.30,
    "SOL": 0.20,
}

EXPECTED_LT_BUCKETS = {
    "crypto_lt",
    "equities_lt",
}

EXPECTED_LT_SHARE = 0.37


COUNTRY_MAPPER_PATH = ROOT / "src/v2/config/lt_country_mapper.json"


def load_country_mapper():
    try:
        with COUNTRY_MAPPER_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        reverse = {}

        for region, symbols in raw.items():
            for symbol in symbols:
                reverse[symbol.upper()] = region

        return reverse

    except Exception:
        return {}


COUNTRY_MAPPER = load_country_mapper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default=None):
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def approx_equal(a: float, b: float, tol: float = 0.03) -> bool:
    return abs(a - b) <= tol


lt_portfolio = read_json(PATHS["lt_portfolio"], {})
lt_positions = read_json(PATHS["lt_positions"], {})
funding_plan = read_json(PATHS["funding_plan"], {})
capital_policy = read_json(PATHS["capital_policy"], {})

failed_checks = []

# =========================================================
# CRYPTO LT ALLOCATION
# =========================================================

crypto_alloc = {}

if isinstance(lt_portfolio, dict):
    positions = lt_portfolio.get("positions", {})

    if isinstance(positions, dict):
        for symbol, data in positions.items():
            if isinstance(data, dict):
                crypto_alloc[symbol] = data.get("weight", 0)

allocation_sum = round(sum(crypto_alloc.values()), 4)

# =========================================================
# LT POSITIONS
# =========================================================

positions = []

if isinstance(lt_positions, dict):
    positions = lt_positions.get("positions", []) or []

bucket_counter = Counter()
asset_class_counter = Counter()
source_brick_counter = Counter()
region_counter = Counter()

for pos in positions:
    if not isinstance(pos, dict):
        continue

    bucket_counter[pos.get("bucket", "unknown")] += 1
    asset_class_counter[pos.get("asset_class", "unknown")] += 1
    source_brick_counter[pos.get("source_brick", "unknown")] += 1

    symbol = str(pos.get("symbol", "")).upper()

    region = COUNTRY_MAPPER.get(symbol, "UNKNOWN")
    region_counter[region] += 1

# =========================================================
# CHECKS
# =========================================================

if not crypto_alloc:
    failed_checks.append({
        "check": "crypto_lt_exists",
        "ok": False,
        "severity": "critical",
        "detail": "Crypto LT allocation must exist.",
        "evidence": {}
    })

if not approx_equal(allocation_sum, 1.0):
    failed_checks.append({
        "check": "crypto_lt_sum_valid",
        "ok": False,
        "severity": "warning",
        "detail": "Crypto LT allocation should sum near 100%.",
        "evidence": {
            "allocation_sum": allocation_sum
        }
    })

missing_assets = sorted(
    set(EXPECTED_CRYPTO_LT.keys()) - set(crypto_alloc.keys())
)

if missing_assets:
    failed_checks.append({
        "check": "crypto_lt_assets_present",
        "ok": False,
        "severity": "critical",
        "detail": "Official LT crypto assets missing.",
        "evidence": {
            "missing_assets": missing_assets
        }
    })

for asset, expected_weight in EXPECTED_CRYPTO_LT.items():
    actual = crypto_alloc.get(asset)

    if actual is None or not approx_equal(actual, expected_weight):
        failed_checks.append({
            "check": f"{asset}_lt_weight",
            "ok": False,
            "severity": "warning",
            "detail": f"{asset} LT weight deviates from master allocation.",
            "evidence": {
                "expected": expected_weight,
                "actual": actual
            }
        })

if len(positions) == 0:
    failed_checks.append({
        "check": "lt_positions_exist",
        "ok": False,
        "severity": "critical",
        "detail": "Long-term positions registry must not be empty.",
        "evidence": {}
    })

if not EXPECTED_LT_BUCKETS.intersection(set(bucket_counter.keys())):
    failed_checks.append({
        "check": "lt_buckets_present",
        "ok": False,
        "severity": "warning",
        "detail": "Expected LT buckets not found.",
        "evidence": dict(bucket_counter)
    })

# =========================================================
# STATUS
# =========================================================

status = "ok"

if any(x["severity"] == "critical" for x in failed_checks):
    status = "critical"
elif failed_checks:
    status = "warning"

summary = {
    "crypto_lt_allocations": crypto_alloc,
    "crypto_lt_sum": allocation_sum,
    "lt_positions_count": len(positions),
    "bucket_distribution": dict(bucket_counter),
    "asset_class_distribution": dict(asset_class_counter),
    "source_brick_distribution": dict(source_brick_counter),
    "region_distribution": dict(region_counter),
    "official_lt_share": EXPECTED_LT_SHARE,
}

result = {
    "generated_at": utc_now(),
    "status": status,
    "master_intent": {
        "mission": "Compound profits into resilient multi-asset long-term strategic holdings.",
        "official_crypto_lt_allocation": EXPECTED_CRYPTO_LT,
        "official_lt_share": EXPECTED_LT_SHARE,
        "expected_buckets": sorted(EXPECTED_LT_BUCKETS),
        "preprod_mode": "virtual / simulated only",
    },
    "summary": summary,
    "failed_checks": failed_checks,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

print(json.dumps({
    "status": status,
    "summary": summary,
    "failed_checks": failed_checks,
}, indent=2))
