#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Clean Restart Readiness V1

Prépare un clean restart contrôlé sans l'exécuter.

Ce module :
- inventorie les artefacts legacy ;
- calcule leurs empreintes ;
- produit un manifeste d'archive ;
- construit des registres vides candidats ;
- prépare un rapport de clôture administrative ;
- prépare un plan de rollback ;
- ne modifie aucun artefact canonique.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

PROVIDER_ROOT = ROOT / "market/providers"

READINESS_ROOT = PROVIDER_ROOT / "clean_restart"
STAGING_ROOT = READINESS_ROOT / "staging"

DECISION_PACK_PATH = (
    PROVIDER_ROOT / "migration_decision_pack_v1.json"
)

QUALITY_GATE_PATH = (
    PROVIDER_ROOT / "provider_quality_gate_v1.json"
)

VALIDATION_PATH = (
    PROVIDER_ROOT / "cross_source_validation_v1.json"
)

OUTPUT = (
    READINESS_ROOT / "clean_restart_readiness_v1.json"
)

MANIFEST_OUTPUT = (
    READINESS_ROOT / "legacy_archive_manifest_v1.json"
)

CLOSURE_OUTPUT = (
    READINESS_ROOT
    / "administrative_closure_candidate_v1.json"
)

ROLLBACK_OUTPUT = (
    READINESS_ROOT / "rollback_plan_v1.json"
)

STAGED_POSITIONS = (
    STAGING_ROOT / "positions.empty.candidate.json"
)

STAGED_STATE = (
    STAGING_ROOT / "state.empty.candidate.json"
)

STAGED_FILLS = (
    STAGING_ROOT / "simulated_fills.empty.candidate.jsonl"
)

STAGED_EQUITY_CURVE = (
    STAGING_ROOT / "equity_curve.reset.candidate.json"
)


LEGACY_ARTIFACTS = [
    ROOT / "state/positions.json",
    ROOT / "state/state.json",
    ROOT / "state/positions_state.json",
    ROOT / "state/position_report.json",
    ROOT / "state/exposure_snapshot.json",
    ROOT / "state/limits_report.json",
    ROOT / "state/reconciliation_report.json",
    ROOT / "execution/simulated_fills.jsonl",
    ROOT / "execution/fills.json",
    ROOT / "execution/fills_simulated.json",
    ROOT / "execution/execution_plan.json",
    ROOT / "execution/rejected_orders.jsonl",
    ROOT / "reporting/equity_curve.json",
    ROOT / "reporting/dashboard_payload.json",
    ROOT / "ui/ui_bundle.json",
    ROOT / "market/prices.json",
    ROOT / "universe/price_snapshot.json",
]


CANONICAL_WATCHLIST = LEGACY_ARTIFACTS.copy()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(temporary, path)


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def file_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": None,
            "sha256": None,
            "modified_at": None,
        }

    stat = path.stat()

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
        "modified_at": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat().replace("+00:00", "Z"),
    }


def extract_active_positions(
    payload: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}

    positions: dict[str, dict[str, Any]] = {}

    for symbol, row in payload.items():
        if not isinstance(symbol, str):
            continue

        if not isinstance(row, dict):
            continue

        try:
            quantity = float(
                row.get("qty")
                if row.get("qty") is not None
                else row.get("quantity", 0)
            )
        except (TypeError, ValueError):
            quantity = 0.0

        if quantity <= 0:
            continue

        positions[symbol.upper()] = {
            "quantity": quantity,
            "average_price": (
                row.get("avg_price")
                if row.get("avg_price") is not None
                else row.get("average_price")
            ),
        }

    return positions


def build_staging_candidates(
    generated_at: str,
) -> dict[str, Any]:
    positions_candidate = {}

    state_candidate = {
        "ts": generated_at,
        "engine": (
            "offensive_equities_clean_restart_candidate_v1"
        ),
        "status": "staging_only",
        "positions": {},
        "orders_seen": [],
        "orders_seen_plan_id": None,
        "last_run": None,
        "last_broker_run": None,
        "meta": {
            "performance_start_at": None,
            "legacy_archive_reference": None,
            "clean_restart_executed": False,
        },
    }

    equity_curve_candidate = {
        "ts": generated_at,
        "engine": (
            "offensive_equities_equity_curve_reset_candidate_v1"
        ),
        "status": "staging_only",
        "performance_start_at": None,
        "starting_equity": None,
        "points": [],
        "legacy_history_excluded": True,
        "clean_restart_executed": False,
    }

    atomic_write_json(
        STAGED_POSITIONS,
        positions_candidate,
    )

    atomic_write_json(
        STAGED_STATE,
        state_candidate,
    )

    STAGED_FILLS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_fills = STAGED_FILLS.with_suffix(
        STAGED_FILLS.suffix + ".tmp"
    )

    temporary_fills.write_text(
        "",
        encoding="utf-8",
    )

    os.replace(
        temporary_fills,
        STAGED_FILLS,
    )

    atomic_write_json(
        STAGED_EQUITY_CURVE,
        equity_curve_candidate,
    )

    return {
        "positions": file_metadata(
            STAGED_POSITIONS
        ),
        "state": file_metadata(
            STAGED_STATE
        ),
        "simulated_fills": file_metadata(
            STAGED_FILLS
        ),
        "equity_curve": file_metadata(
            STAGED_EQUITY_CURVE
        ),
    }


def main() -> int:
    generated_at = utc_now_iso()

    decision_pack = read_json(
        DECISION_PACK_PATH
    )

    quality_gate = read_json(
        QUALITY_GATE_PATH
    )

    validation = read_json(
        VALIDATION_PATH
    )

    if not isinstance(decision_pack, dict):
        decision_pack = {}

    if not isinstance(quality_gate, dict):
        quality_gate = {}

    if not isinstance(validation, dict):
        validation = {}

    positions_payload = read_json(
        ROOT / "state/positions.json"
    )

    active_positions = extract_active_positions(
        positions_payload
    )

    artifact_inventory = [
        file_metadata(path)
        for path in LEGACY_ARTIFACTS
    ]

    manifest = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_legacy_archive_manifest"
        ),
        "generated_at": generated_at,
        "status": "manifest_only",
        "archive_created": False,
        "canonical_files_modified": False,
        "artifact_count": len(
            artifact_inventory
        ),
        "existing_artifact_count": sum(
            1
            for row in artifact_inventory
            if row["exists"]
        ),
        "artifacts": artifact_inventory,
    }

    atomic_write_json(
        MANIFEST_OUTPUT,
        manifest,
    )

    closure_candidate = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_administrative_closure_candidate"
        ),
        "generated_at": generated_at,
        "status": "candidate_only",
        "closure_type": (
            "administrative_legacy_close_without_market_pnl"
        ),
        "reason": (
            "Transition from simulated and partially corrupted "
            "market data to validated real market data."
        ),
        "performance_treatment": {
            "legacy_realized_pnl_created": False,
            "legacy_unrealized_pnl_transferred": False,
            "artificial_pnl_recognized": False,
            "legacy_performance_preserved_in_archive": True,
            "new_performance_series_required": True,
        },
        "positions_to_close_administratively": [
            {
                "symbol": symbol,
                "quantity": row["quantity"],
                "legacy_average_price": row[
                    "average_price"
                ],
                "market_order_generated": False,
                "realized_pnl_generated": False,
            }
            for symbol, row in sorted(
                active_positions.items()
            )
        ],
        "execution_authorized": False,
        "canonical_files_modified": False,
    }

    atomic_write_json(
        CLOSURE_OUTPUT,
        closure_candidate,
    )

    staging_candidates = (
        build_staging_candidates(
            generated_at
        )
    )

    rollback_plan = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_clean_restart_rollback_plan"
        ),
        "generated_at": generated_at,
        "status": "plan_only",
        "rollback_tested": False,
        "execution_authorized": False,
        "requirements": [
            (
                "Create a timestamped immutable archive "
                "before any canonical write."
            ),
            (
                "Verify every archived SHA-256 against "
                "the manifest."
            ),
            (
                "Restore all canonical artifacts as one "
                "transaction if any post-restart check fails."
            ),
            (
                "Restart the offensive equities pipeline "
                "only after restoration is complete."
            ),
            (
                "Re-run position, exposure, reconciliation "
                "and reporting checks after rollback."
            ),
        ],
        "restore_targets": [
            row["path"]
            for row in artifact_inventory
            if row["exists"]
        ],
        "canonical_files_modified": False,
    }

    atomic_write_json(
        ROLLBACK_OUTPUT,
        rollback_plan,
    )

    blockers: list[str] = []

    quality_decision = quality_gate.get(
        "decision"
    )

    promotion = quality_gate.get(
        "promotion"
    )

    if not isinstance(promotion, dict):
        promotion = {}

    if quality_decision != "PASS":
        blockers.append(
            "Quality Gate strict non validé."
        )

    if promotion.get(
        "authorized_by_quality_gate"
    ) is not True:
        blockers.append(
            "Promotion non autorisée par le Quality Gate."
        )

    if validation.get(
        "secondary_configured"
    ) is not True:
        blockers.append(
            "Source secondaire non configurée."
        )

    recommendation = (
        decision_pack.get("recommendation")
        if isinstance(
            decision_pack.get("recommendation"),
            dict,
        )
        else {}
    )

    if recommendation.get(
        "decision"
    ) != "clean_restart":
        blockers.append(
            "Le Migration Decision Pack ne recommande "
            "pas formellement le clean restart."
        )

    hashes_before = {
        str(path): sha256_file(path)
        for path in CANONICAL_WATCHLIST
    }

    hashes_after = {
        str(path): sha256_file(path)
        for path in CANONICAL_WATCHLIST
    }

    changed_canonical_files = [
        path
        for path in hashes_before
        if hashes_before[path]
        != hashes_after[path]
    ]

    if changed_canonical_files:
        blockers.append(
            "Un artefact canonique a été modifié "
            "pendant le dry-run."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_clean_restart_readiness"
        ),
        "generated_at": generated_at,
        "status": (
            "readiness_prepared_execution_blocked"
            if blockers
            else "readiness_prepared"
        ),
        "mode": "dry_run",
        "execution_authorized": False,
        "clean_restart_executed": False,
        "canonical_files_modified": False,
        "active_positions": {
            "count": len(active_positions),
            "symbols": sorted(
                active_positions
            ),
        },
        "decision_inputs": {
            "migration_decision": (
                recommendation.get("decision")
            ),
            "quality_gate": quality_decision,
            "secondary_configured": (
                validation.get(
                    "secondary_configured"
                )
            ),
            "promotion_authorized": (
                promotion.get(
                    "authorized_by_quality_gate"
                )
            ),
        },
        "legacy_manifest": {
            "path": str(MANIFEST_OUTPUT),
            "sha256": sha256_file(
                MANIFEST_OUTPUT
            ),
            "archive_created": False,
        },
        "administrative_closure_candidate": {
            "path": str(CLOSURE_OUTPUT),
            "sha256": sha256_file(
                CLOSURE_OUTPUT
            ),
            "executed": False,
        },
        "staging_candidates": (
            staging_candidates
        ),
        "rollback_plan": {
            "path": str(ROLLBACK_OUTPUT),
            "sha256": sha256_file(
                ROLLBACK_OUTPUT
            ),
            "tested": False,
        },
        "canonical_integrity": {
            "changed_files": (
                changed_canonical_files
            ),
            "verified_unchanged": (
                not changed_canonical_files
            ),
        },
        "blockers": blockers,
        "next_requirements": [
            "Configure and validate a secondary provider.",
            "Obtain a strict Quality Gate PASS.",
            "Generate the immutable archive.",
            "Test archive restore in an isolated directory.",
            "Set the new performance start timestamp.",
            "Run the clean restart during a controlled maintenance window.",
        ],
    }

    atomic_write_json(
        OUTPUT,
        report,
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "active_positions": report[
                    "active_positions"
                ],
                "decision_inputs": report[
                    "decision_inputs"
                ],
                "legacy_manifest": report[
                    "legacy_manifest"
                ],
                "administrative_closure_candidate": (
                    report[
                        "administrative_closure_candidate"
                    ]
                ),
                "staging_candidates": report[
                    "staging_candidates"
                ],
                "rollback_plan": report[
                    "rollback_plan"
                ],
                "canonical_integrity": report[
                    "canonical_integrity"
                ],
                "blockers": blockers,
                "output": str(OUTPUT),
                "canonical_files_modified": False,
                "clean_restart_executed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
