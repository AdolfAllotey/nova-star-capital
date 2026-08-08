from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict


SRC_PORTFOLIO_DIR = Path("/opt/nsc/app/src/v2/data/portfolio")
SRC_STATE_DIR = SRC_PORTFOLIO_DIR / "state"
SRC_REBALANCE_DIR = SRC_PORTFOLIO_DIR / "rebalance"

PREPROD_ANALYSIS_DIR = Path("/opt/nsc/data/preprod/analysis")
PREPROD_PORTFOLIO_DIR = Path("/opt/nsc/data/preprod/portfolio")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def copy_json_if_exists(src: Path, dst: Path) -> bool:
    data = read_json(src, default=None)
    if data is None:
        return False
    write_json(dst, data)
    return True


def build_legacy_portfolio_view(portfolio_target: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
    final_weights = portfolio_target.get("final_brick_weights", {}) or {}
    confidences = portfolio_target.get("brick_confidence", {}) or {}
    bricks_state = portfolio_state.get("bricks", {}) or {}

    all_bricks = {
        "crypto",
        "equities_offensive",
        "equities_defensive",
        "bonds",
        "precious_metals",
        "long_term",
        "options_us",
    }

    portfolio_view: Dict[str, Any] = {}

    for brick in sorted(all_bricks):
        state_entry = bricks_state.get(brick, {}) or {}
        target_weight = float(final_weights.get(brick, 0.0) or 0.0)
        confidence = float(confidences.get(brick, 0.0) or 0.0)

        status = state_entry.get("status")
        if not status:
            status = "ACTIVE" if target_weight > 0 else "INACTIVE"

        exposure = state_entry.get("target_weight_snapshot", target_weight)
        try:
            exposure = float(exposure or 0.0)
        except Exception:
            exposure = 0.0

        entry: Dict[str, Any] = {
            "target_weight": target_weight,
            "status": status,
        }

        if target_weight > 0 or brick in bricks_state:
            entry["exposure"] = exposure
            entry["confidence"] = confidence

        portfolio_view[brick] = entry

    total_weight = round(sum(float(v.get("target_weight", 0.0) or 0.0) for v in portfolio_view.values()), 6)

    return {
        "portfolio": portfolio_view,
        "total_weight": total_weight,
    }


def build_enriched_portfolio_state(
    portfolio_target: Dict[str, Any],
    portfolio_state: Dict[str, Any],
) -> Dict[str, Any]:
    legacy = build_legacy_portfolio_view(portfolio_target, portfolio_state)

    enriched = {
        **legacy,
        "status": portfolio_state.get("status", "ok"),
        "engine": "preprod_portfolio_sync_v1",
        "source_engine": portfolio_state.get("engine", "portfolio_state_builder_v1"),
        "bricks": portfolio_state.get("bricks", {}) or {},
        "funding_pools": portfolio_state.get("funding_pools", {}) or {},
        "portfolio_regime": portfolio_target.get("portfolio_regime", "unknown"),
        "cash_buffer": portfolio_target.get("cash_buffer"),
        "timestamp": now_iso(),
    }
    return enriched


def main() -> None:
    src_target = SRC_PORTFOLIO_DIR / "portfolio_target.json"
    src_state = SRC_STATE_DIR / "portfolio_state.json"
    src_rebalance = SRC_REBALANCE_DIR / "rebalance_plan.json"
    src_funding = SRC_REBALANCE_DIR / "funding_plan.json"

    portfolio_target = read_json(src_target, default={}) or {}
    portfolio_state = read_json(src_state, default={}) or {}
    rebalance_plan = read_json(src_rebalance, default={}) or {}
    funding_plan = read_json(src_funding, default={}) or {}

    if not portfolio_target:
        raise FileNotFoundError(f"Missing source file: {src_target}")
    if not portfolio_state:
        raise FileNotFoundError(f"Missing source file: {src_state}")

    enriched_state = build_enriched_portfolio_state(portfolio_target, portfolio_state)

    analysis_state_dst = PREPROD_ANALYSIS_DIR / "portfolio_state.json"
    target_dst = PREPROD_PORTFOLIO_DIR / "portfolio_target.json"
    rebalance_dst = PREPROD_PORTFOLIO_DIR / "rebalance_plan.json"
    funding_dst = PREPROD_PORTFOLIO_DIR / "funding_plan.json"

    write_json(analysis_state_dst, enriched_state)
    write_json(target_dst, portfolio_target)

    if rebalance_plan:
        write_json(rebalance_dst, rebalance_plan)
    if funding_plan:
        write_json(funding_dst, funding_plan)

    summary = {
        "status": "ok",
        "engine": "preprod_portfolio_sync_v1",
        "written": {
            "portfolio_state": str(analysis_state_dst),
            "portfolio_target": str(target_dst),
            "rebalance_plan": str(rebalance_dst) if rebalance_plan else None,
            "funding_plan": str(funding_dst) if funding_plan else None,
        },
        "timestamp": now_iso(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
