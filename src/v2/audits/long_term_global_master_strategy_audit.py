from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"

OUTPUT = (
    DATA
    / "audits"
    / "long_term_global_master_strategy_audit.json"
)

CRYPTO_PATH = Path(
    "/opt/nsc/data/preprod/long_term/state/crypto_positions.json"
)

EQUITY_PATH = Path(
    "/opt/nsc/data/preprod/long_term/state/equity_positions.json"
)

VALUATION_PATH = Path(
    "/opt/nsc/data/preprod/long_term/state/valuation.json"
)

TRANSFER_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl"
)

FUNDING_PLAN_PATH = (
    DATA
    / "capital"
    / "funding_plan.json"
)

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

COUNTRY_MAPPER_PATH = (
    ROOT
    / "src/v2/config/lt_country_mapper.json"
)


def utc_now():
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path, default=None):
    try:
        if not path.exists():
            return default

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return default


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []

    try:
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines():
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            if isinstance(item, dict):
                rows.append(item)

    except Exception:
        return []

    return rows


def load_country_mapper():
    raw = read_json(
        COUNTRY_MAPPER_PATH,
        {},
    ) or {}

    reverse = {}

    if isinstance(raw, dict):
        for region, symbols in raw.items():
            for symbol in symbols or []:
                reverse[
                    str(symbol).upper()
                ] = region

    return reverse


def approx_equal(
    left,
    right,
    tol=0.03,
):
    return (
        abs(
            float(left)
            - float(right)
        )
        <= tol
    )


COUNTRY_MAPPER = load_country_mapper()

lt_portfolio = read_json(
    CRYPTO_PATH,
    {},
) or {}

lt_positions_doc = read_json(
    EQUITY_PATH,
    {},
) or {}

valuation = read_json(
    VALUATION_PATH,
    {},
) or {}

funding_plan = read_json(
    FUNDING_PLAN_PATH,
    {},
) or {}

transfer_rows = read_jsonl(
    TRANSFER_PATH
)

crypto_positions = (
    lt_portfolio.get(
        "positions",
        {},
    )
    if isinstance(
        lt_portfolio,
        dict,
    )
    else {}
)

crypto_alloc = {}

if isinstance(
    crypto_positions,
    dict,
):
    for symbol, data in crypto_positions.items():
        if not isinstance(
            data,
            dict,
        ):
            continue

        weight = data.get("weight")

        if weight is not None:
            crypto_alloc[
                str(symbol).upper()
            ] = float(weight)

allocation_sum = round(
    sum(
        crypto_alloc.values()
    ),
    6,
)

equity_positions = (
    lt_positions_doc.get(
        "positions",
        [],
    )
    if isinstance(
        lt_positions_doc,
        dict,
    )
    else []
)

if not isinstance(
    equity_positions,
    list,
):
    equity_positions = []

crypto_count = (
    len(crypto_positions)
    if isinstance(
        crypto_positions,
        dict,
    )
    else 0
)

equity_count = len(
    equity_positions
)

total_positions = (
    crypto_count
    + equity_count
)

approved = []

for row in transfer_rows:
    status = str(
        row.get("status") or ""
    ).lower()

    target = str(
        row.get(
            "to_pocket",
            row.get("to", ""),
        )
        or ""
    ).lower()

    if (
        status == "approved"
        and target
        in {
            "lt",
            "long_term",
            "crypto_lt",
            "equities_lt",
        }
    ):
        approved.append(row)

quality = (
    valuation.get(
        "data_quality",
        {},
    )
    if isinstance(
        valuation,
        dict,
    )
    else {}
)

totals = (
    valuation.get(
        "totals",
        {},
    )
    if isinstance(
        valuation,
        dict,
    )
    else {}
)

guardrails = (
    funding_plan.get(
        "guardrails",
        {},
    )
    if isinstance(
        funding_plan,
        dict,
    )
    else {}
)

valuation_healthy = (
    valuation.get("status") == "ok"
    and valuation.get("engine")
    == "long_term_consolidator_v2"
    and valuation.get("environment")
    == "PREPROD"
    and valuation.get("execution_mode")
    == "SIMULATED_ONLY"
    and quality.get("complete") is True
    and int(
        quality.get(
            "fallback_count",
            0,
        )
        or 0
    )
    == 0
    and len(
        quality.get(
            "provider_errors",
            [],
        )
        or []
    )
    == 0
)

manual_only = (
    guardrails.get(
        "automatic_transfers_allowed"
    )
    is False
    and guardrails.get(
        "requires_governance_approval"
    )
    is True
)

valuation_zero = (
    int(
        totals.get(
            "positions",
            0,
        )
        or 0
    )
    == 0
    and float(
        totals.get(
            "market_value_eur",
            0,
        )
        or 0
    )
    == 0.0
    and float(
        totals.get(
            "cost_basis_eur",
            0,
        )
        or 0
    )
    == 0.0
)

ready_empty = (
    total_positions == 0
    and len(approved) == 0
    and valuation_zero
    and valuation_healthy
    and manual_only
)

bucket_counter = Counter()
asset_class_counter = Counter()
source_brick_counter = Counter()
region_counter = Counter()

for pos in equity_positions:
    if not isinstance(
        pos,
        dict,
    ):
        continue

    bucket_counter[
        pos.get(
            "bucket",
            "unknown",
        )
    ] += 1

    asset_class_counter[
        pos.get(
            "asset_class",
            "unknown",
        )
    ] += 1

    source_brick_counter[
        pos.get(
            "source_brick",
            "unknown",
        )
    ] += 1

    symbol = str(
        pos.get(
            "symbol",
            "",
        )
    ).upper()

    region_counter[
        COUNTRY_MAPPER.get(
            symbol,
            "UNKNOWN",
        )
    ] += 1

if crypto_count:
    bucket_counter[
        "crypto_lt"
    ] += crypto_count

    asset_class_counter[
        "crypto"
    ] += crypto_count

    source_brick_counter[
        "crypto"
    ] += crypto_count

failed_checks = []

if not valuation_healthy:
    failed_checks.append({
        "check":
            "valuation_authority_healthy",
        "ok": False,
        "severity": "critical",
        "detail":
            "Canonical Long Term valuation is unhealthy.",
        "evidence": quality,
    })

if not manual_only:
    failed_checks.append({
        "check":
            "manual_funding_only",
        "ok": False,
        "severity": "critical",
        "detail":
            "Long Term funding must remain governed/manual.",
        "evidence": guardrails,
    })

if (
    len(approved) > 0
    and total_positions == 0
):
    failed_checks.append({
        "check":
            "approved_transfer_not_unfunded",
        "ok": False,
        "severity": "critical",
        "detail":
            "Approved LT transfer exists but no LT positions are materialized.",
        "evidence": {
            "approved_lt_transfers":
                len(approved),
            "positions_count":
                total_positions,
        },
    })

if not ready_empty:
    if not crypto_alloc:
        failed_checks.append({
            "check":
                "crypto_lt_exists",
            "ok": False,
            "severity": "critical",
            "detail":
                "Funded Crypto LT allocation must exist.",
            "evidence": {},
        })

    if not approx_equal(
        allocation_sum,
        1.0,
    ):
        failed_checks.append({
            "check":
                "crypto_lt_sum_valid",
            "ok": False,
            "severity": "warning",
            "detail":
                "Funded Crypto LT allocation should sum near 100%.",
            "evidence": {
                "allocation_sum":
                    allocation_sum,
            },
        })

    missing_assets = sorted(
        set(
            EXPECTED_CRYPTO_LT
        )
        - set(
            crypto_alloc
        )
    )

    if missing_assets:
        failed_checks.append({
            "check":
                "crypto_lt_assets_present",
            "ok": False,
            "severity": "critical",
            "detail":
                "Official LT crypto assets are missing from funded portfolio.",
            "evidence": {
                "missing_assets":
                    missing_assets,
            },
        })

    for asset, expected_weight in (
        EXPECTED_CRYPTO_LT.items()
    ):
        actual = crypto_alloc.get(
            asset
        )

        if (
            actual is None
            or not approx_equal(
                actual,
                expected_weight,
            )
        ):
            failed_checks.append({
                "check":
                    f"{asset}_lt_weight",
                "ok": False,
                "severity": "warning",
                "detail":
                    f"{asset} LT weight deviates from master allocation.",
                "evidence": {
                    "expected":
                        expected_weight,
                    "actual":
                        actual,
                },
            })

    if total_positions == 0:
        failed_checks.append({
            "check":
                "lt_positions_exist",
            "ok": False,
            "severity": "critical",
            "detail":
                "Funded Long Term portfolio must contain positions.",
            "evidence": {},
        })

    if not (
        EXPECTED_LT_BUCKETS
        .intersection(
            set(
                bucket_counter.keys()
            )
        )
    ):
        failed_checks.append({
            "check":
                "lt_buckets_present",
            "ok": False,
            "severity": "warning",
            "detail":
                "Expected funded LT buckets were not found.",
            "evidence":
                dict(
                    bucket_counter
                ),
        })

status = "ok"

if any(
    row["severity"] == "critical"
    for row in failed_checks
):
    status = "critical"

elif failed_checks:
    status = "warning"

operational_state = (
    "READY_EMPTY"
    if ready_empty
    else (
        "FUNDED"
        if total_positions > 0
        else (
            "APPROVED_PENDING_MATERIALIZATION"
            if approved
            else "UNHEALTHY"
        )
    )
)

summary = {
    "operational_state":
        operational_state,
    "ready_empty":
        ready_empty,
    "crypto_lt_allocations":
        crypto_alloc,
    "crypto_lt_sum":
        allocation_sum,
    "crypto_positions_count":
        crypto_count,
    "equity_positions_count":
        equity_count,
    "lt_positions_count":
        total_positions,
    "approved_lt_transfers":
        len(approved),
    "bucket_distribution":
        dict(bucket_counter),
    "asset_class_distribution":
        dict(asset_class_counter),
    "source_brick_distribution":
        dict(source_brick_counter),
    "region_distribution":
        dict(region_counter),
    "official_lt_share":
        EXPECTED_LT_SHARE,
}

result = {
    "generated_at":
        utc_now(),
    "status":
        status,
    "operational_state":
        operational_state,
    "master_intent": {
        "mission": (
            "Compound profits into resilient "
            "multi-asset long-term strategic holdings."
        ),
        "official_crypto_lt_allocation":
            EXPECTED_CRYPTO_LT,
        "official_lt_share":
            EXPECTED_LT_SHARE,
        "expected_buckets":
            sorted(
                EXPECTED_LT_BUCKETS
            ),
        "preprod_mode":
            "virtual / simulated only",
    },
    "summary":
        summary,
    "failed_checks":
        failed_checks,
}

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "status":
                status,
            "operational_state":
                operational_state,
            "summary":
                summary,
            "failed_checks":
                failed_checks,
        },
        ensure_ascii=False,
        indent=2,
    )
)
