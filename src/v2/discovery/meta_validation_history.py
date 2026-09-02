from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

VALIDATION_PATH = DATA_DIR / "discovery" / "meta_validation.json"
HISTORY_PATH = DATA_DIR / "discovery" / "meta_validation_history.json"
SUMMARY_PATH = DATA_DIR / "discovery" / "meta_validation_history_summary.json"


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


def avg(values: list[float]) -> float:
    vals = [float(x) for x in values if x is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def main() -> None:
    now = utc_now()
    validation = load_json(VALIDATION_PATH, default={}) or {}
    history = load_json(HISTORY_PATH, default=[]) or []

    if not isinstance(history, list):
        history = []

    row = {
        "ts": now,
        "engine": validation.get("engine"),
        "semantics_version": validation.get("semantics_version"),
        "validation_state": validation.get("validation_state"),
        "temporally_comparable": validation.get("temporally_comparable"),
        "meta_snapshot_generated_at": validation.get("meta_snapshot_generated_at"),
        "plan_meta_snapshot_generated_at": validation.get("plan_meta_snapshot_generated_at"),
        "plan_meta_snapshot_lineage_status": validation.get("plan_meta_snapshot_lineage_status"),
        "status": validation.get("status"),
        "pipeline_health": validation.get("pipeline_health"),
        "decision_alignment_score": validation.get("decision_alignment_score"),
        "opportunity_coverage_score": validation.get("opportunity_coverage_score"),
        "execution_quality": validation.get("execution_quality"),
        "strategy_drift": validation.get("strategy_drift"),
        "raw_strategy_drift": validation.get("raw_strategy_drift"),
        "execution_symbols": validation.get("execution_symbols", []),
        "matched_top_tradable": validation.get("matched_top_tradable", []),
        "missing_high_conviction_count": len(validation.get("missing_high_conviction", []) or []),
        "ignored_top_tradable_count": len(validation.get("ignored_top_tradable", []) or []),
    }

    history.append(row)
    history = history[-500:]

    active_semantics_version = "v4_temporal_lineage"

    current_semantics = [
        x for x in history
        if isinstance(x, dict)
        and x.get("semantics_version") == active_semantics_version
    ]

    comparable = [
        x for x in current_semantics
        if x.get("temporally_comparable") is True
    ]

    pending = [
        x for x in current_semantics
        if x.get("validation_state") == "awaiting_execution_refresh"
    ]

    lineage_unavailable = [
        x for x in current_semantics
        if x.get("validation_state") == "lineage_unavailable"
    ]

    alignments = [
        x.get("decision_alignment_score")
        for x in comparable
    ]

    coverages = [
        x.get("opportunity_coverage_score")
        for x in comparable
    ]

    drifts = [
        x for x in comparable
        if x.get("strategy_drift") is True
    ]

    healthy = [
        x for x in comparable
        if x.get("pipeline_health") == "healthy"
    ]

    recent = history[-20:]
    comparable_count = len(comparable)

    summary = {
        "status": "ok",
        "generated_at": now,
        "engine": "meta_validation_history_v2",
        "active_semantics_version": active_semantics_version,
        "history_count": len(history),
        "recent_count": len(recent),
        "current_semantics_count": len(current_semantics),
        "comparable_count": comparable_count,
        "pending_count": len(pending),
        "lineage_unavailable_count": len(lineage_unavailable),
        "avg_decision_alignment": avg(alignments),
        "avg_opportunity_coverage": avg(coverages),
        "drift_count": len(drifts),
        "healthy_count": len(healthy),
        "healthy_ratio": (
            round((len(healthy) / comparable_count) * 100.0, 2)
            if comparable_count else 0.0
        ),
        "latest": row,
        "recent": recent,
    }

    save_json(HISTORY_PATH, history)
    save_json(SUMMARY_PATH, summary)

    print({
        "output": str(SUMMARY_PATH),
        "engine": summary["engine"],
        "history_count": summary["history_count"],
        "avg_decision_alignment": summary["avg_decision_alignment"],
        "avg_opportunity_coverage": summary["avg_opportunity_coverage"],
        "drift_count": summary["drift_count"],
    })


if __name__ == "__main__":
    main()
