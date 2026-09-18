from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"

OUTPUT = DATA / "audits" / "long_term_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "lt_portfolio": Path(
        "/opt/nsc/data/preprod/long_term/state/crypto_positions.json"
    ),
    "long_term_positions": Path(
        "/opt/nsc/data/preprod/long_term/state/equity_positions.json"
    ),
    "valuation": Path(
        "/opt/nsc/data/preprod/long_term/state/valuation.json"
    ),
    "transfer_instructions": Path(
        "/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl"
    ),
    "capital_flow_policy": DATA / "portfolio/capital_flow_policy.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "family_office_bundle": DATA / "capital/family_office_bundle.json",
}

EXPECTED_CRYPTO_LT = {
    "BTC": 0.50,
    "ETH": 0.30,
    "SOL": 0.20,
}

EXPECTED_LT_SHARE = 0.37


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "__error__": str(exc),
            "__path__": str(path),
        }


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
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

            payload = json.loads(line)

            if isinstance(payload, dict):
                rows.append(payload)

    except Exception as exc:
        return [{
            "__error__": str(exc),
            "__path__": str(path),
        }]

    return rows


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        for key in (
            "positions",
            "holdings",
            "assets",
            "items",
            "data",
        ):
            if isinstance(value.get(key), list):
                return value.get(key) or []

    return []


def check(
    name: str,
    ok: bool,
    severity: str,
    detail: str,
    evidence: Any = None,
) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def status_from_checks(
    checks: List[Dict[str, Any]],
) -> str:
    if any(
        (not row["ok"])
        and row["severity"] == "critical"
        for row in checks
    ):
        return "critical"

    if any(
        (not row["ok"])
        and row["severity"] == "warning"
        for row in checks
    ):
        return "warning"

    return "ok"


def extract_allocations(
    lt_portfolio: Any,
) -> Dict[str, float]:
    if not isinstance(
        lt_portfolio,
        dict,
    ):
        return {}

    allocations = (
        lt_portfolio.get("allocation")
        or lt_portfolio.get("target_allocation")
        or {}
    )

    if isinstance(
        allocations,
        dict,
    ) and allocations:
        return {
            str(symbol).upper(): float(weight)
            for symbol, weight
            in allocations.items()
        }

    positions = lt_portfolio.get(
        "positions",
        {},
    )

    if not isinstance(
        positions,
        dict,
    ):
        return {}

    result = {}

    for symbol, payload in positions.items():
        if not isinstance(
            payload,
            dict,
        ):
            continue

        weight = payload.get("weight")

        if weight is not None:
            result[
                str(symbol).upper()
            ] = float(weight)

    return result


def approved_lt_transfers(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    approved = []

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

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

    return approved


def main() -> None:
    docs = {
        key: (
            read_json(path, {})
            if key != "transfer_instructions"
            else read_jsonl(path)
        )
        for key, path in PATHS.items()
    }

    context = docs["capital_context"] or {}
    lt_portfolio = docs["lt_portfolio"] or {}
    lt_positions = as_list(
        docs["long_term_positions"]
    )
    valuation = docs["valuation"] or {}
    transfers = docs["transfer_instructions"] or []
    capital_flow = docs["capital_flow_policy"] or {}
    funding_plan = docs["funding_plan"] or {}
    family_office = docs["family_office_bundle"] or {}

    allocations = extract_allocations(
        lt_portfolio
    )

    allocation_sum = round(
        sum(
            float(value)
            for value in allocations.values()
        ),
        6,
    ) if allocations else 0.0

    crypto_positions = (
        lt_portfolio.get("positions", {})
        if isinstance(
            lt_portfolio,
            dict,
        )
        else {}
    )

    crypto_count = (
        len(crypto_positions)
        if isinstance(
            crypto_positions,
            dict,
        )
        else 0
    )

    equity_count = len(
        lt_positions
    )

    total_positions = (
        crypto_count
        + equity_count
    )

    approved = approved_lt_transfers(
        transfers
    )

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
                0.0,
            )
            or 0.0
        )
        == 0.0
        and float(
            totals.get(
                "cost_basis_eur",
                0.0,
            )
            or 0.0
        )
        == 0.0
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

    ready_empty = (
        total_positions == 0
        and len(approved) == 0
        and valuation_zero
        and valuation_healthy
        and manual_only
    )

    funded_state = (
        total_positions > 0
        or len(approved) > 0
    )

    allocation_exists_ok = (
        ready_empty
        or (
            isinstance(
                allocations,
                dict,
            )
            and len(
                allocations
            )
            > 0
        )
    )

    allocation_sum_ok = (
        ready_empty
        or abs(
            allocation_sum
            - 1.0
        )
        <= 0.01
    )

    master_assets_ok = (
        ready_empty
        or set(
            EXPECTED_CRYPTO_LT.keys()
        ).issubset(
            set(
                allocations.keys()
            )
        )
    )

    checks = [
        check(
            "preprod_virtual_mode",
            context.get("environment")
            == "PREPROD"
            and context.get(
                "real_money_enabled"
            )
            is False,
            "critical",
            "Long Term must remain PREPROD simulated.",
            context,
        ),
        check(
            "valuation_authority_healthy",
            valuation_healthy,
            "critical",
            "Canonical Long Term valuation must be healthy and fail-closed.",
            {
                "status": valuation.get("status"),
                "engine": valuation.get("engine"),
                "environment": valuation.get(
                    "environment"
                ),
                "execution_mode": valuation.get(
                    "execution_mode"
                ),
                "data_quality": quality,
            },
        ),
        check(
            "manual_funding_only",
            manual_only,
            "critical",
            "Long Term funding must remain governed/manual.",
            guardrails,
        ),
        check(
            "zero_state_governed",
            (
                not ready_empty
                or len(approved) == 0
            ),
            "critical",
            "An empty Long Term pocket is valid only without approved pending LT transfers.",
            {
                "ready_empty": ready_empty,
                "approved_lt_transfers": len(
                    approved
                ),
            },
        ),
        check(
            "lt_allocation_exists",
            allocation_exists_ok,
            "critical",
            (
                "Long Term crypto allocation must exist "
                "once the pocket is funded."
            ),
            {
                "allocation_count": len(
                    allocations
                ),
                "ready_empty": ready_empty,
            },
        ),
        check(
            "lt_allocation_sum_valid",
            allocation_sum_ok,
            "warning",
            (
                "Funded Long Term crypto allocation "
                "should sum near 100%."
            ),
            {
                "sum": allocation_sum,
                "ready_empty": ready_empty,
            },
        ),
        check(
            "crypto_lt_matches_master",
            master_assets_ok,
            "critical",
            (
                "Funded Crypto LT must contain "
                "the official BTC/ETH/SOL allocation."
            ),
            {
                "found_assets": sorted(
                    allocations.keys()
                ),
                "ready_empty": ready_empty,
            },
        ),
        check(
            "approved_transfer_not_unfunded",
            not (
                len(approved) > 0
                and total_positions == 0
            ),
            "critical",
            (
                "Approved LT transfer cannot coexist "
                "with an empty LT position registry."
            ),
            {
                "approved_lt_transfers": len(
                    approved
                ),
                "positions_count": total_positions,
            },
        ),
        check(
            "lt_share_policy_respected",
            abs(
                float(
                    capital_flow.get(
                        "long_term_bucket_share",
                        EXPECTED_LT_SHARE,
                    )
                )
                - EXPECTED_LT_SHARE
            )
            <= 0.001,
            "warning",
            "Long Term policy share should remain 37%.",
            capital_flow.get(
                "long_term_bucket_share"
            ),
        ),
        check(
            "family_office_connected",
            isinstance(
                family_office,
                dict,
            )
            and family_office.get(
                "status"
            )
            == "ok",
            "warning",
            "Family Office layer should remain connected.",
            (
                family_office.get(
                    "headline"
                )
                if isinstance(
                    family_office,
                    dict,
                )
                else None
            ),
        ),
    ]

    expected_vs_actual = {
        symbol: {
            "expected": expected_weight,
            "actual": allocations.get(
                symbol
            ),
        }
        for symbol, expected_weight
        in EXPECTED_CRYPTO_LT.items()
    }

    operational_state = (
        "READY_EMPTY"
        if ready_empty
        else (
            "FUNDED"
            if total_positions > 0
            else (
                "APPROVED_PENDING_MATERIALIZATION"
                if len(approved) > 0
                else "UNHEALTHY"
            )
        )
    )

    report = {
        "status": status_from_checks(
            checks
        ),
        "engine": "long_term_master_strategy_audit_v2",
        "mode": "read_only",
        "timestamp": utc_now(),
        "operational_state": operational_state,
        "master_intent": {
            "mission": (
                "Compound profits into resilient "
                "long-term strategic holdings."
            ),
            "official_crypto_lt_allocation":
                EXPECTED_CRYPTO_LT,
            "official_lt_share":
                EXPECTED_LT_SHARE,
            "preprod_mode":
                "virtual / simulated only",
        },
        "summary": {
            "allocation_count": len(
                allocations
            ),
            "allocation_sum":
                allocation_sum,
            "crypto_positions_count":
                crypto_count,
            "equity_positions_count":
                equity_count,
            "lt_positions_count":
                total_positions,
            "approved_lt_transfers":
                len(approved),
            "ready_empty":
                ready_empty,
            "funded_state":
                funded_state,
            "allocations":
                allocations,
            "expected_vs_actual":
                expected_vs_actual,
        },
        "checks": checks,
        "failed_checks": [
            row
            for row in checks
            if not row["ok"]
        ],
        "files": {
            key: str(path)
            for key, path
            in PATHS.items()
        },
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status":
                    report["status"],
                "operational_state":
                    operational_state,
                "summary":
                    report["summary"],
                "failed_checks":
                    report["failed_checks"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
