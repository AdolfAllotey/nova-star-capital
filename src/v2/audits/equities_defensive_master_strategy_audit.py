from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "equities_defensive_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "portfolio_input": ROOT / "src/v2/data/portfolio/inputs/equities_defensive_portfolio_input.json",
    "defensive_signal": ROOT / "data/defensive/defensive_signal.json",
    "allocator_output": ROOT / "data/defensive/defensive_allocations.json",
    "quality_scores": ROOT / "data/defensive/quality_scores.json",
    "low_vol_scores": ROOT / "data/defensive/low_volatility_scores.json",
    "dividend_scores": ROOT / "data/defensive/dividend_scores.json",
    "market_regime": ROOT / "src/v2/data/defensive/market_regime_snapshot.json",
    "capital_flow_policy": DATA / "portfolio/capital_flow_policy.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "family_office_bundle": DATA / "capital/family_office_bundle.json",
}

EXPECTED_ROLE = "stabilization"
EXPECTED_POOL = "ibkr_pool"

EXPECTED_DEFENSIVE_TYPES = {
    "quality",
    "low_volatility",
    "dividend",
    "defensive",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def as_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for key in ("positions", "assets", "holdings", "signals", "data", "items", "scores"):
            if isinstance(x.get(key), list):
                return x.get(key)
    return []


def check(name: str, ok: bool, severity: str, detail: str, evidence: Any = None) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def status_from_checks(checks: List[Dict[str, Any]]) -> str:
    if any((not c["ok"]) and c["severity"] == "critical" for c in checks):
        return "critical"
    if any((not c["ok"]) and c["severity"] == "warning" for c in checks):
        return "warning"
    return "ok"


def get_symbol(row: Dict[str, Any]) -> str:
    return str(
        row.get("symbol")
        or row.get("ticker")
        or row.get("asset")
        or row.get("name")
        or ""
    ).upper().strip()


def main() -> None:
    docs = {k: read_json(v, {}) for k, v in PATHS.items()}

    context = docs["capital_context"]
    portfolio_input = docs["portfolio_input"]
    defensive_signal = docs["defensive_signal"]
    allocator_output = docs["allocator_output"]

    quality_scores = as_list(docs["quality_scores"])
    low_vol_scores = as_list(docs["low_vol_scores"])
    dividend_scores = as_list(docs["dividend_scores"])

    allocations = allocator_output.get("proposed_assets", allocator_output.get("allocations", []))
    allocations = allocations if isinstance(allocations, list) else []

    allocation_symbols = [
        get_symbol(x) for x in allocations
        if isinstance(x, dict) and get_symbol(x)
    ]

    allocation_sectors = [
        str(x.get("sector", "unknown"))
        for x in allocations
        if isinstance(x, dict)
    ]

    score_universe = (
        len(quality_scores)
        + len(low_vol_scores)
        + len(dividend_scores)
    )

    checks = [
        check(
            "preprod_virtual_mode",
            context.get("environment") == "PREPROD"
            and context.get("capital_mode") == "virtual",
            "critical",
            "Defensive equities must run in virtual PREPROD mode.",
            context,
        ),

        check(
            "portfolio_role_defensive",
            portfolio_input.get("portfolio_role") == EXPECTED_ROLE,
            "critical",
            "Defensive equities role must be stabilization_equity.",
            portfolio_input.get("portfolio_role"),
        ),

        check(
            "funding_pool_ibkr",
            portfolio_input.get("funding_pool") == EXPECTED_POOL,
            "critical",
            "Defensive equities must use IBKR funding pool.",
            portfolio_input.get("funding_pool"),
        ),

        check(
            "defensive_signal_present",
            isinstance(defensive_signal, dict)
            and bool(defensive_signal),
            "critical",
            "Defensive signal output must exist.",
            defensive_signal.get("target_exposure"),
        ),

        check(
            "allocator_output_present",
            isinstance(allocator_output, dict)
            and len(allocations) > 0,
            "critical",
            "Defensive allocator output must contain allocations.",
            {
                "allocations": len(allocations),
            },
        ),

        check(
            "constraints_respected",
            (allocator_output.get("constraints", {}) or {}).get("constraints_respected") is True or (allocator_output.get("summary", {}) or {}).get("constraints_respected") is True or (defensive_signal.get("score_summary", {}) or {}).get("constraints_respected") is True,
            "critical",
            "Defensive allocator constraints must be respected.",
            allocator_output.get("constraints_respected") or (allocator_output.get("summary", {}) or {}).get("constraints_respected") or (defensive_signal.get("score_summary", {}) or {}).get("constraints_respected"),
        ),

        check(
            "beta_reasonable",
            float((allocator_output.get("summary", {}) or {}).get("portfolio_beta_estimate", (defensive_signal.get("score_summary", {}) or {}).get("portfolio_beta_estimate", 99))) < 0.9,
            "warning",
            "Defensive beta should remain below offensive profile.",
            (allocator_output.get("summary", {}) or {}).get("portfolio_beta_estimate") or (defensive_signal.get("score_summary", {}) or {}).get("portfolio_beta_estimate"),
        ),

        check(
            "quality_engines_present",
            score_universe > 0,
            "critical",
            "Quality / low vol / dividend engines should provide scores.",
            {
                "quality_scores": len(quality_scores),
                "low_vol_scores": len(low_vol_scores),
                "dividend_scores": len(dividend_scores),
            },
        ),

        check(
            "market_regime_visible",
            portfolio_input.get("regime") in {"risk_on", "balanced", "risk_off", "stabilization_active"}
            or defensive_signal.get("market_regime") in {"risk_on", "balanced", "risk_off", "stabilization_active"},
            "warning",
            "Defensive layer should consume market regime.",
            {
                "portfolio_regime": portfolio_input.get("regime"),
                "signal_regime": defensive_signal.get("market_regime"),
            },
        ),

        check(
            "manual_funding_only",
            (docs["funding_plan"].get("guardrails") or {}).get("automatic_transfers_allowed") is False,
            "critical",
            "Funding into IBKR must remain governed/manual.",
            docs["funding_plan"].get("guardrails"),
        ),

        check(
            "family_office_connected",
            isinstance(docs["family_office_bundle"], dict)
            and docs["family_office_bundle"].get("status") == "ok",
            "warning",
            "Family office layer should be connected.",
            docs["family_office_bundle"].get("headline"),
        ),
    ]

    report = {
        "status": status_from_checks(checks),
        "engine": "equities_defensive_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),

        "master_intent": {
            "mission": "Provide equity stabilization, lower volatility exposure, quality/dividend resilience and portfolio cushioning.",
            "portfolio_role": EXPECTED_ROLE,
            "funding_pool": EXPECTED_POOL,
            "preprod_mode": "virtual / simulated only",
        },

        "summary": {
            "portfolio_target_weight": portfolio_input.get("target_weight"),
            "portfolio_role": portfolio_input.get("portfolio_role"),
            "funding_pool": portfolio_input.get("funding_pool"),
            "regime": portfolio_input.get("regime"),
            "confidence": portfolio_input.get("confidence"),

            "target_exposure": defensive_signal.get("target_exposure"),
            "selected_assets_count": defensive_signal.get("selected_assets_count") or (defensive_signal.get("score_summary", {}) or {}).get("selected_assets_count"),

            "constraints_respected": allocator_output.get("constraints_respected") or (allocator_output.get("summary", {}) or {}).get("constraints_respected") or (defensive_signal.get("score_summary", {}) or {}).get("constraints_respected"),
            "portfolio_beta_estimate": (allocator_output.get("summary", {}) or {}).get("portfolio_beta_estimate") or (defensive_signal.get("score_summary", {}) or {}).get("portfolio_beta_estimate"),

            "allocation_symbols": dict(Counter(allocation_symbols)),
            "allocation_sectors": dict(Counter(allocation_sectors)),

            "quality_scores": len(quality_scores),
            "low_vol_scores": len(low_vol_scores),
            "dividend_scores": len(dividend_scores),
        },

        "checks": checks,
        "failed_checks": [c for c in checks if not c["ok"]],
        "files": {k: str(v) for k, v in PATHS.items()},
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "failed_checks": report["failed_checks"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
