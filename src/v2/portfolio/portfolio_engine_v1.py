from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.portfolio.load_portfolio_inputs import (
    load_portfolio_inputs,
)
from src.v2.portfolio.portfolio_rules import (
    get_caps_for_regime,
    get_family_for_brick,
)
from src.v2.portfolio.portfolio_utils import (
    round_dict,
    safe_float,
    save_json,
)


INPUT_DIR = Path(
    "/opt/nsc/data/preprod/portfolio/inputs"
)

OUTPUT_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/"
    "portfolio_target.json"
)

POLICY_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/"
    "policy/allocation_policy.json"
)


SOURCE_MAX_AGE_HOURS = {
    "crypto": 12.0,
    "equities_offensive": 96.0,
    "equities_defensive": 96.0,
    "bonds": 96.0,
    "precious_metals": 96.0,
    "options_us": 72.0,
}


def load_json(
    path: Path,
    default: Any,
) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


def source_freshness(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    brick = str(
        payload.get("brick", "unknown")
    )

    source_raw = payload.get("source_file")
    max_age_hours = SOURCE_MAX_AGE_HOURS.get(
        brick,
        96.0,
    )

    result = {
        "brick": brick,
        "source_file": source_raw,
        "exists": False,
        "age_hours": None,
        "max_age_hours": max_age_hours,
        "stale": True,
        "reason": "source_file_missing",
    }

    if not source_raw:
        return result

    source_path = Path(str(source_raw))

    if not source_path.exists():
        result["reason"] = "source_file_not_found"
        return result

    modified = datetime.fromtimestamp(
        source_path.stat().st_mtime,
        tz=timezone.utc,
    )

    age_hours = max(
        0.0,
        (
            datetime.now(timezone.utc) - modified
        ).total_seconds() / 3600.0,
    )

    stale = age_hours > max_age_hours

    result.update({
        "exists": True,
        "modified_at": modified.isoformat(),
        "age_hours": round(age_hours, 4),
        "stale": stale,
        "reason": (
            "source_too_old"
            if stale
            else "source_fresh"
        ),
    })

    return result


def allowed_bricks_from_policy(
    policy: Dict[str, Any],
) -> set[str]:
    allowed = set()

    pools = policy.get("funding_pools", {})

    if not isinstance(pools, dict):
        return allowed

    for pool in pools.values():
        if not isinstance(pool, dict):
            continue

        for brick in pool.get(
            "allowed_bricks",
            [],
        ) or []:
            allowed.add(str(brick))

    return allowed


def is_shadow_payload(
    payload: Dict[str, Any],
) -> bool:
    return bool(
        payload.get("portfolio_role")
        == "shadow_overlay"
        or payload.get("execution_mode")
        == "shadow_only"
        or payload.get("signal_type")
        == "shadow_observation"
    )


def classify_payloads(
    payloads: List[Dict[str, Any]],
    policy: Dict[str, Any],
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    allowed_bricks = allowed_bricks_from_policy(
        policy
    )

    deployable = []
    excluded = []
    stale = []

    for payload in payloads:
        brick = str(
            payload.get("brick", "unknown")
        )

        if payload.get("enabled") is not True:
            excluded.append({
                "brick": brick,
                "reason": "disabled",
            })
            continue

        if is_shadow_payload(payload):
            excluded.append({
                "brick": brick,
                "reason": "shadow_observation_only",
            })
            continue

        if (
            allowed_bricks
            and brick not in allowed_bricks
        ):
            excluded.append({
                "brick": brick,
                "reason": "not_allowed_by_master_policy",
            })
            continue

        freshness = source_freshness(payload)

        if freshness["stale"]:
            stale.append(freshness)
            continue

        enriched = dict(payload)
        enriched["_source_freshness"] = freshness
        deployable.append(enriched)

    return deployable, excluded, stale


def detect_portfolio_regime(
    enabled_payloads: List[Dict[str, Any]],
) -> str:
    offensive_weight = 0.0
    macro_def_weight = 0.0
    hedge_weight = 0.0

    offensive_conf = []
    defensive_conf = []

    for item in enabled_payloads:
        brick = item.get("brick", "unknown")
        family = get_family_for_brick(brick)

        weight = safe_float(
            item.get("target_weight", 0.0)
        )
        confidence = safe_float(
            item.get("confidence", 0.0)
        )
        regime = item.get("regime", "")

        if family == "offensive":
            offensive_weight += weight
            offensive_conf.append(confidence)

        elif family == "macro_defensive":
            macro_def_weight += weight
            defensive_conf.append(confidence)

        elif family == "systemic_hedge":
            hedge_weight += weight
            defensive_conf.append(confidence)

        if regime in {
            "strong_macro_defensive",
            "macro_defensive",
        }:
            defensive_conf.append(confidence)

    avg_off_conf = (
        sum(offensive_conf) / len(offensive_conf)
        if offensive_conf
        else 0.0
    )

    avg_def_conf = (
        sum(defensive_conf) / len(defensive_conf)
        if defensive_conf
        else 0.0
    )

    if (
        macro_def_weight + hedge_weight >= 0.25
        or (
            avg_def_conf >= 0.75
            and offensive_weight < 0.35
        )
    ):
        return "risk_off"

    if (
        offensive_weight >= 0.40
        and avg_off_conf >= 0.70
        and macro_def_weight < 0.20
    ):
        return "risk_on"

    return "balanced"


def apply_family_caps(
    raw_brick_weights: Dict[str, float],
    family_caps: Dict[str, float],
):
    family_to_bricks = defaultdict(list)
    family_raw_weights = defaultdict(float)

    for brick, weight in raw_brick_weights.items():
        family = get_family_for_brick(brick)
        family_to_bricks[family].append(brick)
        family_raw_weights[family] += weight

    final_brick_weights = dict(
        raw_brick_weights
    )
    cap_adjustments = {}

    for family, raw_weight in (
        family_raw_weights.items()
    ):
        cap = family_caps.get(family, 1.0)

        if raw_weight > cap and raw_weight > 0:
            factor = cap / raw_weight

            for brick in family_to_bricks[family]:
                final_brick_weights[brick] *= factor

            cap_adjustments[family] = {
                "raw": round(raw_weight, 6),
                "capped": round(cap, 6),
                "applied": True,
                "reduction_factor": round(
                    factor,
                    6,
                ),
            }

        else:
            cap_adjustments[family] = {
                "raw": round(raw_weight, 6),
                "capped": round(raw_weight, 6),
                "applied": False,
                "reduction_factor": 1.0,
            }

    return (
        final_brick_weights,
        dict(family_raw_weights),
        cap_adjustments,
    )


def normalize_to_investable_limit(
    weights: Dict[str, float],
    investable_limit: float,
):
    total = sum(weights.values())

    if total > investable_limit and total > 0:
        factor = investable_limit / total

        normalized = {
            key: value * factor
            for key, value in weights.items()
        }

        return (
            normalized,
            True,
            round(factor, 6),
        )

    return weights, False, 1.0


def build_family_weights(
    brick_weights: Dict[str, float],
):
    family_weights = defaultdict(float)

    for brick, weight in brick_weights.items():
        family = get_family_for_brick(brick)
        family_weights[family] += weight

    return dict(family_weights)


def run_portfolio_engine_v1():
    payloads = load_portfolio_inputs(
        str(INPUT_DIR)
    )

    policy = load_json(
        POLICY_PATH,
        {},
    )

    if not policy:
        raise RuntimeError(
            "Master allocation policy missing or unreadable: "
            f"{POLICY_PATH}"
        )

    if policy.get("source_of_truth") is not True:
        raise RuntimeError(
            "Master allocation policy is not marked "
            "source_of_truth=true"
        )

    deployable_payloads, excluded_inputs, stale_inputs = (
        classify_payloads(
            payloads,
            policy,
        )
    )

    if stale_inputs:
        raise RuntimeError(
            "Stale Portfolio input sources detected: "
            + json.dumps(
                stale_inputs,
                ensure_ascii=False,
            )
        )

    if not deployable_payloads:
        raise RuntimeError(
            "No fresh deployable Portfolio inputs available"
        )

    raw_brick_weights = {}
    brick_confidence = {}
    brick_regimes = {}
    brick_roles = {}
    brick_allocations = {}
    brick_families = {}
    input_freshness = {}

    for item in deployable_payloads:
        brick = item.get("brick", "unknown")

        raw_brick_weights[brick] = safe_float(
            item.get("target_weight", 0.0)
        )

        brick_confidence[brick] = safe_float(
            item.get("confidence", 0.0)
        )

        brick_regimes[brick] = item.get(
            "regime",
            "unknown",
        )

        brick_roles[brick] = item.get(
            "portfolio_role",
            "unknown",
        )

        brick_allocations[brick] = item.get(
            "allocation",
            {},
        )

        brick_families[brick] = (
            get_family_for_brick(brick)
        )

        input_freshness[brick] = item.get(
            "_source_freshness",
            {},
        )

    portfolio_regime = detect_portfolio_regime(
        deployable_payloads
    )

    family_caps = get_caps_for_regime(
        portfolio_regime
    )

    capped_brick_weights, raw_family_weights, cap_adjustments = (
        apply_family_caps(
            raw_brick_weights,
            family_caps,
        )
    )

    cash_buffer_min_pct = safe_float(
        policy.get(
            "cash_buffer_min_pct",
            0.10,
        )
    )

    cash_buffer_min_pct = max(
        0.0,
        min(1.0, cash_buffer_min_pct),
    )

    investable_limit = round(
        1.0 - cash_buffer_min_pct,
        6,
    )

    total_after_caps = sum(
        capped_brick_weights.values()
    )

    (
        final_brick_weights,
        normalization_applied,
        normalization_factor,
    ) = normalize_to_investable_limit(
        capped_brick_weights,
        investable_limit,
    )

    final_total_weight = sum(
        final_brick_weights.values()
    )

    cash_buffer = max(
        cash_buffer_min_pct,
        1.0 - final_total_weight,
    )

    final_family_weights = build_family_weights(
        final_brick_weights
    )

    portfolio_target = {
        "status": "ok",
        "engine": "portfolio_engine_v1_1",
        "portfolio_regime": portfolio_regime,
        "policy_source": str(POLICY_PATH),
        "policy_source_of_truth": True,
        "inputs_loaded": len(payloads),
        "inputs_deployable": len(
            deployable_payloads
        ),
        "inputs_excluded": excluded_inputs,
        "stale_inputs": stale_inputs,
        "input_freshness": input_freshness,
        "raw_brick_weights": round_dict(
            raw_brick_weights
        ),
        "final_brick_weights": round_dict(
            final_brick_weights
        ),
        "brick_families": brick_families,
        "raw_family_weights": round_dict(
            raw_family_weights
        ),
        "final_family_weights": round_dict(
            final_family_weights
        ),
        "family_caps": family_caps,
        "cap_adjustments": cap_adjustments,
        "cash_buffer_min_pct": round(
            cash_buffer_min_pct,
            6,
        ),
        "investable_limit": investable_limit,
        "total_raw_weight": round(
            sum(raw_brick_weights.values()),
            6,
        ),
        "total_after_caps": round(
            total_after_caps,
            6,
        ),
        "total_final_weight": round(
            final_total_weight,
            6,
        ),
        "normalization_applied": (
            normalization_applied
        ),
        "normalization_factor": (
            normalization_factor
        ),
        "cash_buffer": round(
            cash_buffer,
            6,
        ),
        "brick_confidence": round_dict(
            brick_confidence
        ),
        "brick_regimes": brick_regimes,
        "brick_roles": brick_roles,
        "brick_allocations": brick_allocations,
    }

    save_json(
        portfolio_target,
        str(OUTPUT_PATH),
    )

    return portfolio_target


if __name__ == "__main__":
    result = run_portfolio_engine_v1()

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
