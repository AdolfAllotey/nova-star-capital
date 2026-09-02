from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

META_PATH = DATA_DIR / "discovery" / "meta_rankings.json"
EXECUTION_PLAN_PATH = DATA_DIR / "trading" / "execution_plan.json"
OUT_PATH = DATA_DIR / "discovery" / "meta_validation.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm_symbol(x: Any) -> str:
    s = str(x or "").upper().strip()
    if s.endswith("USDT"):
        s = s[:-4]
    return s



def main() -> None:
    meta = load_json(META_PATH, default={}) or {}
    plan = load_json(EXECUTION_PLAN_PATH, default={}) or {}

    meta_items = meta.get("items", []) if isinstance(meta.get("items"), list) else []
    orders = plan.get("orders", []) if isinstance(plan.get("orders"), list) else []

    # ========================================================
    # RC2 Meta Validation Temporal Lineage V4
    #
    # Strategic comparison is valid only when the execution
    # plan explicitly proves that it consumed the exact Meta
    # Ranking snapshot currently being validated.
    # ========================================================

    meta_snapshot_generated_at = str(
        meta.get("generated_at") or ""
    ).strip() or None

    plan_meta_snapshot_generated_at = str(
        plan.get("meta_snapshot_generated_at") or ""
    ).strip() or None

    plan_meta_snapshot_lineage_status = str(
        plan.get("meta_snapshot_lineage_status") or ""
    ).strip() or None

    if (
        plan_meta_snapshot_lineage_status == "consistent"
        and meta_snapshot_generated_at
        and plan_meta_snapshot_generated_at
        and meta_snapshot_generated_at
        == plan_meta_snapshot_generated_at
    ):
        validation_state = "comparable"
        temporally_comparable = True
    elif (
        plan_meta_snapshot_lineage_status == "consistent"
        and meta_snapshot_generated_at
        and plan_meta_snapshot_generated_at
        and meta_snapshot_generated_at
        != plan_meta_snapshot_generated_at
    ):
        validation_state = "awaiting_execution_refresh"
        temporally_comparable = False
    else:
        validation_state = "lineage_unavailable"
        temporally_comparable = False

    top10 = meta_items[:10]
    top20 = meta_items[:20]

    top10_symbols = {norm_symbol(x.get("symbol")) for x in top10 if isinstance(x, dict)}
    top20_symbols = {norm_symbol(x.get("symbol")) for x in top20 if isinstance(x, dict)}

    order_symbols = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        sym = norm_symbol(o.get("symbol"))
        if sym:
            order_symbols.append(sym)

    unique_order_symbols = sorted(set(order_symbols))
    orders_count = len(unique_order_symbols)

    matched_top10 = sorted([s for s in unique_order_symbols if s in top10_symbols])
    matched_top20 = sorted([s for s in unique_order_symbols if s in top20_symbols])
    missing_from_top20 = sorted([s for s in unique_order_symbols if s not in top20_symbols])

    # ========================================================
    # RC2 Meta Validation Strategic Semantics V3
    #
    # "Tradable" alone means that an execution venue exists.
    # It does NOT mean that the asset is strategically eligible.
    #
    # The validation universe must therefore match the actual
    # Meta Ranking execution-governance contract.
    # ========================================================

    strategic_allowed_verdicts = {
        "GOOD_CANDIDATE",
        "WATCH_TRADABLE",
    }

    strategic_meta = [
        x for x in meta_items
        if isinstance(x, dict)
        and x.get("execution_eligible") is True
        and str(x.get("verdict") or "") in strategic_allowed_verdicts
    ]

    top_tradable = strategic_meta[:5]

    top_tradable_symbols = {
        norm_symbol(x.get("symbol"))
        for x in top_tradable
    }

    matched_top_tradable = sorted(
        [
            s
            for s in top_tradable_symbols
            if s in unique_order_symbols
        ]
    )

    ignored_top_tradable = [
        {
            "symbol": norm_symbol(x.get("symbol")),
            "meta_rank": x.get("meta_rank"),
            "verdict": x.get("verdict"),
            "chg_24h": x.get("chg_24h"),
        }
        for x in top_tradable
        if norm_symbol(x.get("symbol")) not in unique_order_symbols
    ]

    # High conviction must be a subset of the strategic
    # execution universe. A high numerical rank cannot override
    # execution ineligibility or a blocking Meta Ranking verdict.
    high_conviction = [
        x for x in strategic_meta
        if float(x.get("meta_rank") or 0.0) >= 55
    ]

    missing_high_conviction = [
        {
            "symbol": norm_symbol(x.get("symbol")),
            "meta_rank": x.get("meta_rank"),
            "verdict": x.get("verdict"),
            "chg_24h": x.get("chg_24h"),
        }
        for x in high_conviction
        if norm_symbol(x.get("symbol")) not in unique_order_symbols
    ]

    if orders_count == 0:
        decision_alignment = 100.0 if not high_conviction else 45.0
    else:
        top20_coverage = (len(matched_top20) / orders_count) * 100.0
        top10_bonus = (len(matched_top10) / orders_count) * 10.0
        drift_penalty = min(40.0, len(missing_from_top20) * 20.0)
        high_conviction_penalty = min(50.0, len(missing_high_conviction) * 25.0)

        decision_alignment = max(
            0.0,
            min(
                100.0,
                top20_coverage + top10_bonus - drift_penalty - high_conviction_penalty,
            ),
        )

    if top_tradable:
        opportunity_coverage = (len(matched_top_tradable) / len(top_tradable)) * 100.0
    else:
        opportunity_coverage = 100.0

    raw_strategy_drift = bool(
        missing_from_top20
        or missing_high_conviction
    )

    if not temporally_comparable:
        # Never classify a temporal mismatch as strategic drift.
        strategy_drift = False
        decision_alignment = 0.0
        opportunity_coverage = 0.0
        execution_quality = "not_evaluated"

        if validation_state == "awaiting_execution_refresh":
            pipeline_health = "pending"
            status = "awaiting_execution_refresh"
        else:
            pipeline_health = "warning"
            status = "lineage_unavailable"

    else:
        strategy_drift = raw_strategy_drift

        if strategy_drift:
            pipeline_health = "drift"
            execution_quality = "weak"
        elif decision_alignment >= 90:
            pipeline_health = "healthy"
            execution_quality = "excellent"
        elif decision_alignment >= 70:
            pipeline_health = "watch"
            execution_quality = "good"
        else:
            pipeline_health = "warning"
            execution_quality = "medium"

        if strategy_drift:
            status = "strategy_drift"
        elif decision_alignment >= 85:
            status = "aligned"
        elif decision_alignment >= 65:
            status = "mostly_aligned"
        elif decision_alignment >= 45:
            status = "partial_alignment"
        else:
            status = "strategy_drift"

    payload = {
        "status": status,
        "generated_at": utc_now(),
        "engine": "meta_validation_engine_v2",
        "semantics_version": "v4_temporal_lineage",
        "mode": "execution_governance_validation",
        "validation_state": validation_state,
        "temporally_comparable": temporally_comparable,
        "meta_snapshot_generated_at": (
            meta_snapshot_generated_at
        ),
        "plan_meta_snapshot_generated_at": (
            plan_meta_snapshot_generated_at
        ),
        "plan_meta_snapshot_lineage_status": (
            plan_meta_snapshot_lineage_status
        ),
        "decision_alignment_score": round(decision_alignment, 2),
        "opportunity_coverage_score": round(opportunity_coverage, 2),
        "alignment_score": round(decision_alignment, 2),
        "execution_quality": execution_quality,
        "pipeline_health": pipeline_health,
        "strategy_drift": strategy_drift,
        "raw_strategy_drift": raw_strategy_drift,
        "coverage": {
            "execution_orders": orders_count,
            "matched_top10": len(matched_top10),
            "matched_top20": len(matched_top20),
            "top20_order_coverage": round((len(matched_top20) / orders_count) * 100.0, 2) if orders_count else 100.0,
            "opportunity_coverage_score": round(opportunity_coverage, 2),
        },
        "execution_symbols": unique_order_symbols,

        "strategic_execution_universe": [
            norm_symbol(x.get("symbol"))
            for x in strategic_meta
            if isinstance(x, dict)
        ],
        "strategic_execution_universe_count": len(
            strategic_meta
        ),
        "strategic_allowed_verdicts": sorted(
            strategic_allowed_verdicts
        ),

        "matched_top10": matched_top10,
        "matched_top20": matched_top20,
        "missing_from_top20": missing_from_top20,
        "top_meta_symbols": [norm_symbol(x.get("symbol")) for x in top10 if isinstance(x, dict)],
        "top_tradable_symbols": [norm_symbol(x.get("symbol")) for x in top_tradable],
        "matched_top_tradable": matched_top_tradable,
        "ignored_top_tradable": ignored_top_tradable,
        "missing_high_conviction": missing_high_conviction,
        "notes": [
            "V4 validates strategy only when Meta Ranking and execution plan share the exact snapshot lineage.",
            "Temporal mismatch is awaiting_execution_refresh and cannot be classified as strategy drift.",
            "Missing or mixed execution lineage is explicit and cannot produce a healthy validation.",
            "Decision alignment checks whether planned orders are coherent with the consumed Meta Ranking snapshot.",
            "Strategic universe requires execution_eligible plus GOOD_CANDIDATE or WATCH_TRADABLE verdict.",
            "Validation remains non-mutating.",
        ],
    }

    save_json(OUT_PATH, payload)

    print({
        "output": str(OUT_PATH),
        "engine": payload["engine"],
        "status": payload["status"],
        "decision_alignment_score": payload["decision_alignment_score"],
        "opportunity_coverage_score": payload["opportunity_coverage_score"],
        "pipeline_health": payload["pipeline_health"],
    })


if __name__ == "__main__":
    main()
