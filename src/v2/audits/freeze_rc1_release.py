from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shutil
import subprocess
import sys


APP_DIR = Path(
    os.getenv(
        "NSC_APP_DIR",
        "/opt/nsc/app",
    )
)

DATA_DIR = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

RELEASES_DIR = DATA_DIR / "releases"
RC1_DIR = RELEASES_DIR / "RC1"
BASELINES_DIR = RC1_DIR / "baselines"

RELEASE_GATE_JSON = RC1_DIR / "rc1_release_gate.json"
RELEASE_GATE_MD = RC1_DIR / "RC1_RELEASE_GATE.md"
RELEASE_HISTORY = RELEASES_DIR / "release_history.jsonl"
CURRENT_BASELINE_POINTER = RC1_DIR / "current_baseline.json"

CERTIFICATION_PATH = (
    DATA_DIR
    / "portfolio"
    / "audit"
    / "rc1_end_to_end_certification.json"
)

REQUIRED_ARTIFACTS = {
    "allocation_policy": (
        DATA_DIR
        / "portfolio"
        / "policy"
        / "allocation_policy.json"
    ),
    "portfolio_target": (
        DATA_DIR
        / "portfolio"
        / "portfolio_target.json"
    ),
    "portfolio_state": (
        DATA_DIR
        / "portfolio"
        / "state"
        / "portfolio_state.json"
    ),
    "rebalance_plan": (
        DATA_DIR
        / "portfolio"
        / "rebalance"
        / "rebalance_plan.json"
    ),
    "funding_plan": (
        DATA_DIR
        / "portfolio"
        / "rebalance"
        / "funding_plan.json"
    ),
    "master_coherence_audit": (
        DATA_DIR
        / "portfolio"
        / "audit"
        / "master_coherence_audit.json"
    ),
    "executive_decision": (
        DATA_DIR
        / "executive_decision"
        / "executive_decision.json"
    ),
    "rc1_end_to_end_certification": CERTIFICATION_PATH,
}

OPTIONAL_ARTIFACT_CANDIDATES = {
    "orchestration_status": [
        DATA_DIR / "portfolio" / "orchestration_status.json",
        DATA_DIR / "portfolio" / "audit" / "orchestration_status.json",
        DATA_DIR / "orchestration" / "orchestration_status.json",
    ],
    "orchestration_consistency": [
        DATA_DIR / "portfolio" / "orchestration_consistency.json",
        DATA_DIR / "portfolio" / "audit" / "orchestration_consistency.json",
        DATA_DIR / "orchestration" / "orchestration_consistency.json",
    ],
    "global_orchestration_audit": [
        DATA_DIR / "portfolio" / "audit" / "global_orchestration_audit.json",
        DATA_DIR / "orchestration" / "global_orchestration_audit.json",
    ],
    "supervision_gate": [
        DATA_DIR / "portfolio" / "supervision_gate.json",
        DATA_DIR / "portfolio" / "audit" / "supervision_gate.json",
        DATA_DIR / "supervision" / "supervision_gate.json",
    ],
    "institutional_supervision_summary": [
        DATA_DIR / "portfolio" / "institutional_supervision_summary.json",
        DATA_DIR / "portfolio" / "audit" / "institutional_supervision_summary.json",
        DATA_DIR / "supervision" / "institutional_supervision_summary.json",
    ],
    "executive_decision_master_audit": [
        DATA_DIR
        / "executive_decision"
        / "executive_decision_master_audit.json",
        DATA_DIR
        / "portfolio"
        / "audit"
        / "executive_decision_master_audit.json",
    ],
    "governance_engine": [
        DATA_DIR / "analysis" / "governance_engine_pro.json",
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required JSON file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON file: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object in: {path}")

    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def relative_to_data_dir(path: Path) -> str:
    try:
        return str(path.relative_to(DATA_DIR))
    except ValueError:
        return str(path)


def get_git_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "repository": str(APP_DIR),
        "git_available": False,
        "commit": None,
        "branch": None,
        "dirty": None,
    }

    try:
        commit = subprocess.check_output(
            ["git", "-C", str(APP_DIR), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        branch = subprocess.check_output(
            ["git", "-C", str(APP_DIR), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        status = subprocess.check_output(
            ["git", "-C", str(APP_DIR), "status", "--porcelain"],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        metadata.update(
            {
                "git_available": True,
                "commit": commit,
                "branch": branch,
                "dirty": bool(status.strip()),
            }
        )

    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
    ):
        pass

    return metadata


def certification_value(
    certification: dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    if key in certification:
        return certification[key]

    for section_name in (
        "summary",
        "certification_summary",
        "result",
        "checks_summary",
    ):
        section = certification.get(section_name)

        if isinstance(section, dict) and key in section:
            return section[key]

    return default


def normalize_certification(
    certification: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(certification)

    keys = (
        "status",
        "certification",
        "rc1_blocker",
        "checks_total",
        "checks_passed",
        "checks_failed",
        "blocking_failures",
        "warnings",
        "portfolio_regime",
        "action_policy",
        "rebalance_execution_allowed",
        "executive_decision",
        "executive_recommended_brick",
        "executive_recommended_amount_eur",
        "executive_confidence",
        "executive_execution_posture",
        "executive_risk_posture",
    )

    for key in keys:
        value = certification_value(
            certification,
            key,
            None,
        )

        if value is not None:
            normalized[key] = value

    if "checks_total" not in normalized:
        checks = certification.get("checks")

        if isinstance(checks, dict):
            normalized["checks_total"] = checks.get("total")
            normalized["checks_passed"] = checks.get("passed")
            normalized["checks_failed"] = checks.get("failed")
            normalized["warnings"] = checks.get(
                "warnings",
                normalized.get("warnings", []),
            )

    return normalized


def validate_certification(
    certification: dict[str, Any],
) -> None:
    failures: list[str] = []

    if certification.get("status") != "PASS":
        failures.append(
            f"status={certification.get('status')!r}, expected 'PASS'"
        )

    if (
        certification.get("certification")
        != "RC1_END_TO_END_CERTIFIED"
    ):
        failures.append(
            "certification is not RC1_END_TO_END_CERTIFIED"
        )

    if certification.get("rc1_blocker") is not False:
        failures.append(
            f"rc1_blocker={certification.get('rc1_blocker')!r}"
        )

    checks_total = certification.get("checks_total")
    checks_passed = certification.get("checks_passed")
    checks_failed = certification.get("checks_failed")

    if checks_total != 38:
        failures.append(
            f"checks_total={checks_total!r}, expected 38"
        )

    if checks_passed != checks_total:
        failures.append(
            f"checks_passed={checks_passed!r}, expected {checks_total!r}"
        )

    if checks_failed != 0:
        failures.append(
            f"checks_failed={checks_failed!r}, expected 0"
        )

    blocking_failures = certification.get(
        "blocking_failures",
        [],
    )

    if blocking_failures:
        failures.append(
            f"blocking_failures is not empty: {blocking_failures!r}"
        )

    warnings = certification.get("warnings", [])

    if isinstance(warnings, int):
        warnings_present = warnings != 0
    else:
        warnings_present = bool(warnings)

    if warnings_present:
        failures.append(
            f"warnings is not empty: {warnings!r}"
        )

    if (
        certification.get("action_policy")
        != "SIMULATED_ONLY"
    ):
        failures.append(
            "action_policy is not SIMULATED_ONLY"
        )

    if (
        certification.get("executive_execution_posture")
        != "SIMULATED_ONLY"
    ):
        failures.append(
            "executive_execution_posture is not SIMULATED_ONLY"
        )

    if failures:
        formatted = "\n - ".join(failures)

        raise RuntimeError(
            "RC1 certification validation failed:\n"
            f" - {formatted}"
        )


def resolve_optional_artifacts() -> dict[str, Path]:
    resolved: dict[str, Path] = {}

    for name, candidates in OPTIONAL_ARTIFACT_CANDIDATES.items():
        for candidate in candidates:
            if candidate.is_file():
                resolved[name] = candidate
                break

    return resolved


def check_existing_freeze() -> None:
    if not RELEASE_GATE_JSON.exists():
        return

    existing = read_json(RELEASE_GATE_JSON)

    if (
        existing.get("release") == "RC1"
        and existing.get("baseline_status") == "FROZEN"
        and existing.get("decision") == "APPROVED"
    ):
        current = existing.get("baseline", {}).get(
            "baseline_id",
            "unknown",
        )

        raise RuntimeError(
            "RC1 is already frozen and approved. "
            f"Existing baseline: {current}. "
            "No overwrite has been performed."
        )


def copy_artifacts(
    baseline_dir: Path,
    artifacts: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifacts_dir = baseline_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=False)

    manifest_entries: list[dict[str, Any]] = []

    for logical_name, source_path in artifacts.items():
        destination_name = f"{logical_name}.json"
        destination_path = artifacts_dir / destination_name

        shutil.copy2(source_path, destination_path)

        entry = {
            "name": logical_name,
            "required": logical_name in REQUIRED_ARTIFACTS,
            "source_path": str(source_path),
            "source_relative_path": relative_to_data_dir(source_path),
            "archived_path": str(destination_path),
            "archived_relative_path": str(
                destination_path.relative_to(RELEASES_DIR)
            ),
            "size_bytes": destination_path.stat().st_size,
            "source_modified_at": datetime.fromtimestamp(
                source_path.stat().st_mtime,
                timezone.utc,
            ).isoformat(),
            "sha256": sha256_file(destination_path),
        }

        manifest_entries.append(entry)

    manifest_entries.sort(key=lambda item: item["name"])

    aggregate_source = "\n".join(
        f"{entry['name']}:{entry['sha256']}"
        for entry in manifest_entries
    ).encode("utf-8")

    aggregate_sha256 = hashlib.sha256(
        aggregate_source
    ).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "release": "RC1",
        "algorithm": "SHA-256",
        "artifact_count": len(manifest_entries),
        "aggregate_sha256": aggregate_sha256,
        "artifacts": manifest_entries,
    }

    return manifest_entries, manifest


def build_markdown(
    release_gate: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    generated_at = release_gate["approved_at"]
    baseline_id = release_gate["baseline"]["baseline_id"]
    certification = release_gate["certification"]
    allocation = release_gate["allocation_policy"]
    governance = release_gate["governance"]
    technical_debt = release_gate["accepted_non_blocking_debt"]

    artifact_rows = "\n".join(
        "| "
        f"{entry['name']} | "
        f"{'Required' if entry['required'] else 'Optional'} | "
        f"`{entry['sha256']}` |"
        for entry in manifest["artifacts"]
    )

    debt_rows = "\n".join(
        f"- {item}" for item in technical_debt
    )

    governed_bricks = "\n".join(
        f"- {brick}" for brick in release_gate["scope"]["governed_bricks"]
    )

    excluded_components = "\n".join(
        f"- **{name}** — `{details['status']}`: "
        f"{details['reason']}"
        for name, details
        in release_gate["scope"]["excluded_components"].items()
    )

    return f"""# Nova Star Capital — RC1 Release Gate

## Official decision

- **Release:** RC1
- **Component:** Core Portfolio Engine
- **Decision:** APPROVED
- **Baseline status:** FROZEN
- **Approval timestamp:** {generated_at}
- **Baseline ID:** `{baseline_id}`
- **Certification:** `{certification['name']}`
- **Certification status:** `{certification['status']}`
- **End-to-end checks:** {certification['checks_passed']}/{certification['checks_total']}
- **Failed checks:** {certification['checks_failed']}
- **Warnings:** {certification['warnings_count']}
- **RC1 blocker:** {str(certification['rc1_blocker']).lower()}

## Release statement

The Nova Star Capital RC1 Core Portfolio Engine is certified,
approved and frozen as the institutional baseline for subsequent releases.

Any functional evolution after this freeze belongs to RC2 or a later release.
Any regression assessment must use this RC1 baseline as its reference.

## Certified scope

{governed_bricks}

## Explicitly excluded from governed RC1 allocation

{excluded_components}

These components may remain visible as observations, but they do not
participate in the governed RC1 allocation or authorize real execution.

## Certified allocation policy

RC1 certifies a **dynamic, policy-driven allocation engine**.

The allocation percentages observed during the certification run are a
point-in-time output. They are not permanently fixed weights.

The frozen elements are:

- allocation rules;
- market-regime interpretation;
- brick and family classifications;
- risk caps;
- normalization method;
- minimum cash buffer;
- policy exclusions;
- governance and execution restrictions.

The resulting target weights may change dynamically according to:

- market regime;
- signal strength;
- confidence levels;
- risk constraints;
- family caps;
- cross-asset conditions;
- applicable governance rules.

### Certification-run allocation snapshot

| Brick | Weight |
|---|---:|
| Bonds | {allocation['certification_snapshot']['bonds'] * 100:.4f}% |
| Crypto | {allocation['certification_snapshot']['crypto'] * 100:.4f}% |
| Defensive equities | {allocation['certification_snapshot']['equities_defensive'] * 100:.4f}% |
| Offensive equities | {allocation['certification_snapshot']['equities_offensive'] * 100:.4f}% |
| Precious metals | {allocation['certification_snapshot']['precious_metals'] * 100:.4f}% |
| Cash | {allocation['cash_buffer'] * 100:.4f}% |

This table is retained only as evidence of the certified run.

## Governance and execution posture

- **Action policy:** `{governance['action_policy']}`
- **Execution mode:** `{governance['execution_mode']}`
- **Real execution allowed:** {str(governance['real_execution_allowed']).lower()}
- **Simulated execution allowed:** {str(governance['simulated_execution_allowed']).lower()}
- **Automatic rebalance allowed:** {str(governance['automatic_rebalance_allowed']).lower()}
- **Automatic funding allowed:** {str(governance['automatic_funding_allowed']).lower()}
- **Manual approval required:** {str(governance['manual_approval_required']).lower()}
- **Manual inter-pool funding required:** {str(governance['manual_inter_pool_funding_required']).lower()}

## Certified executive decision snapshot

- **Decision:** `{release_gate['executive_decision_snapshot']['decision']}`
- **Recommended brick:** `{release_gate['executive_decision_snapshot']['recommended_brick']}`
- **Recommended amount:** EUR {release_gate['executive_decision_snapshot']['recommended_amount_eur']:.2f}
- **Confidence:** {release_gate['executive_decision_snapshot']['confidence'] * 100:.2f}%
- **Execution posture:** `{release_gate['executive_decision_snapshot']['execution_posture']}`
- **Risk posture:** `{release_gate['executive_decision_snapshot']['risk_posture']}`

This decision is also a point-in-time certification snapshot and is not
a permanent investment instruction.

## Accepted non-blocking technical debt

{debt_rows}

None of these items invalidates the certified RC1 behavior.
They must be tracked during RC2 hardening and before production readiness.

## Baseline integrity

- **Hash algorithm:** SHA-256
- **Archived artifacts:** {manifest['artifact_count']}
- **Aggregate baseline hash:** `{manifest['aggregate_sha256']}`

| Artifact | Classification | SHA-256 |
|---|---|---|
{artifact_rows}

## RC2 entry criteria

RC2 may begin on top of this baseline with:

- governed integration of US Options;
- explicit Options allocation policy;
- Greeks and Options risk controls;
- Multi-Asset Portfolio Brain integration;
- refreshed governance and supervision rules;
- RC2 end-to-end certification;
- a new 30-day preproduction run.

## Final approval

**RC1 Core Portfolio Engine: APPROVED AND FROZEN**

This document and its JSON counterpart constitute the official Nova Star
Capital RC1 Release Gate.
"""


def append_release_history(entry: dict[str, Any]) -> None:
    RELEASE_HISTORY.parent.mkdir(parents=True, exist_ok=True)

    with RELEASE_HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                entry,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )


def main() -> int:
    approved_at_dt = utc_now()
    approved_at = approved_at_dt.isoformat()

    stamp = approved_at_dt.strftime("%Y%m%dT%H%M%SZ")
    baseline_id = f"RC1-{stamp}"

    print("===== RC1 RELEASE FREEZE =====")
    print(f"APP_DIR: {APP_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")

    check_existing_freeze()

    certification_raw = read_json(CERTIFICATION_PATH)
    certification = normalize_certification(
        certification_raw
    )
    validate_certification(certification)

    missing_required = [
        str(path)
        for path in REQUIRED_ARTIFACTS.values()
        if not path.is_file()
    ]

    if missing_required:
        formatted = "\n - ".join(missing_required)

        raise RuntimeError(
            "Required RC1 artifacts are missing:\n"
            f" - {formatted}"
        )

    optional_artifacts = resolve_optional_artifacts()

    all_artifacts = {
        **REQUIRED_ARTIFACTS,
        **optional_artifacts,
    }

    BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    baseline_dir = BASELINES_DIR / baseline_id

    if baseline_dir.exists():
        raise RuntimeError(
            f"Baseline directory already exists: {baseline_dir}"
        )

    baseline_dir.mkdir(parents=True, exist_ok=False)

    try:
        manifest_entries, manifest = copy_artifacts(
            baseline_dir,
            all_artifacts,
        )

        manifest["generated_at"] = approved_at
        manifest["baseline_id"] = baseline_id

        manifest_path = baseline_dir / "manifest_sha256.json"
        write_json(manifest_path, manifest)

        git_metadata = get_git_metadata()

        certification_snapshot = {
            "bonds": 0.136364,
            "crypto": 0.363636,
            "equities_defensive": 0.181818,
            "equities_offensive": 0.181818,
            "precious_metals": 0.036364,
        }

        release_gate: dict[str, Any] = {
            "schema_version": "1.0",
            "release": "RC1",
            "component": "Core Portfolio Engine",
            "decision": "APPROVED",
            "baseline_status": "FROZEN",
            "approved_at": approved_at,
            "environment": "PREPROD",
            "release_statement": (
                "RC1 Core Portfolio Engine is certified, approved "
                "and frozen as the institutional baseline."
            ),
            "certification": {
                "name": certification["certification"],
                "status": certification["status"],
                "checks_total": certification["checks_total"],
                "checks_passed": certification["checks_passed"],
                "checks_failed": certification["checks_failed"],
                "warnings_count": len(
                    certification.get("warnings", [])
                ),
                "blocking_failures_count": len(
                    certification.get(
                        "blocking_failures",
                        [],
                    )
                ),
                "rc1_blocker": certification["rc1_blocker"],
                "source_path": str(CERTIFICATION_PATH),
                "source_sha256": sha256_file(
                    CERTIFICATION_PATH
                ),
            },
            "scope": {
                "governed_bricks": [
                    "bonds",
                    "crypto",
                    "equities_defensive",
                    "equities_offensive",
                    "precious_metals",
                ],
                "excluded_components": {
                    "options_us": {
                        "status": "policy_excluded_observation",
                        "reason": "not_allowed_by_master_policy",
                        "governed_target": False,
                    },
                    "options_v2_shadow": {
                        "status": "shadow_observation_only",
                        "reason": "shadow_observation_only",
                        "governed_target": False,
                    },
                    "long_term": {
                        "status": "passive_patrimonial_observation",
                        "reason": "outside_active_allocation_target",
                        "governed_target": False,
                    },
                },
            },
            "allocation_policy": {
                "model": "DYNAMIC_POLICY_DRIVEN",
                "weights_permanently_fixed": False,
                "policy_frozen": True,
                "dynamic_inputs": [
                    "market_regime",
                    "brick_signals",
                    "confidence_levels",
                    "risk_constraints",
                    "family_caps",
                    "cross_asset_conditions",
                    "governance_rules",
                ],
                "frozen_controls": [
                    "allocation_rules",
                    "brick_families",
                    "family_caps",
                    "normalization_method",
                    "cash_buffer_policy",
                    "policy_exclusions",
                    "governance_constraints",
                ],
                "cash_buffer": 0.1,
                "investable_limit": 0.9,
                "certification_snapshot": certification_snapshot,
                "snapshot_is_permanent_target": False,
                "snapshot_purpose": (
                    "Point-in-time evidence of the certified run."
                ),
            },
            "governance": {
                "action_policy": "SIMULATED_ONLY",
                "execution_mode": "SIMULATED",
                "real_execution_allowed": False,
                "simulated_execution_allowed": True,
                "automatic_rebalance_allowed": False,
                "automatic_funding_allowed": False,
                "automatic_inter_universe_transfer": False,
                "manual_approval_required": True,
                "manual_inter_pool_funding_required": True,
            },
            "executive_decision_snapshot": {
                "decision": certification.get(
                    "executive_decision"
                ),
                "recommended_brick": certification.get(
                    "executive_recommended_brick"
                ),
                "recommended_amount_eur": float(
                    certification.get(
                        "executive_recommended_amount_eur",
                        0.0,
                    )
                ),
                "confidence": float(
                    certification.get(
                        "executive_confidence",
                        0.0,
                    )
                ),
                "execution_posture": certification.get(
                    "executive_execution_posture"
                ),
                "risk_posture": (
                    "CONTROLLED_RISK_ON_WITH_CORRELATION_WATCH"
                ),
                "snapshot_is_permanent_instruction": False,
            },
            "baseline": {
                "baseline_id": baseline_id,
                "baseline_path": str(baseline_dir),
                "artifact_count": manifest["artifact_count"],
                "manifest_path": str(manifest_path),
                "aggregate_sha256": manifest[
                    "aggregate_sha256"
                ],
                "archived_artifacts": [
                    {
                        "name": entry["name"],
                        "required": entry["required"],
                        "archived_relative_path": entry[
                            "archived_relative_path"
                        ],
                        "sha256": entry["sha256"],
                    }
                    for entry in manifest_entries
                ],
            },
            "source_control": git_metadata,
            "accepted_non_blocking_debt": [
                (
                    "Clarify and harmonize options_us shadow and "
                    "observation semantics."
                ),
                (
                    "Remove the historical options_us pocket from "
                    "capital_allocator_v1 or mark it explicitly as "
                    "non-governed."
                ),
                (
                    "Replace datetime.utcnow() with timezone-aware "
                    "UTC datetime generation."
                ),
                (
                    "Centralize risk_limits.json under NSC_DATA_DIR "
                    "and remove divergent runtime paths."
                ),
                (
                    "Populate the governance artifact status field "
                    "explicitly."
                ),
                (
                    "Install yfinance or formally document and test "
                    "the market snapshot fallback."
                ),
                (
                    "Refresh stale Options status timestamps before "
                    "RC2 certification."
                ),
                (
                    "Reconcile Risk Controller runtime parameters "
                    "with Global Orchestration Audit inputs."
                ),
            ],
            "next_release": {
                "name": "RC2",
                "component": "Multi-Asset Engine",
                "planned_scope": [
                    "governed_us_options",
                    "options_allocation_policy",
                    "options_greeks",
                    "multi_asset_risk",
                    "portfolio_brain_integration",
                    "rc2_end_to_end_certification",
                    "30_day_preproduction",
                ],
            },
        }

        baseline_release_gate_json = (
            baseline_dir
            / "rc1_release_gate.json"
        )

        baseline_release_gate_md = (
            baseline_dir
            / "RC1_RELEASE_GATE.md"
        )

        markdown = build_markdown(
            release_gate,
            manifest,
        )

        write_json(
            baseline_release_gate_json,
            release_gate,
        )

        baseline_release_gate_md.write_text(
            markdown,
            encoding="utf-8",
        )

        RC1_DIR.mkdir(parents=True, exist_ok=True)

        shutil.copy2(
            baseline_release_gate_json,
            RELEASE_GATE_JSON,
        )

        shutil.copy2(
            baseline_release_gate_md,
            RELEASE_GATE_MD,
        )

        current_pointer = {
            "release": "RC1",
            "baseline_status": "FROZEN",
            "decision": "APPROVED",
            "baseline_id": baseline_id,
            "baseline_path": str(baseline_dir),
            "release_gate_json": str(RELEASE_GATE_JSON),
            "release_gate_markdown": str(RELEASE_GATE_MD),
            "manifest_path": str(manifest_path),
            "aggregate_sha256": manifest[
                "aggregate_sha256"
            ],
            "approved_at": approved_at,
        }

        write_json(
            CURRENT_BASELINE_POINTER,
            current_pointer,
        )

        history_entry = {
            "event": "RELEASE_FROZEN",
            "release": "RC1",
            "component": "Core Portfolio Engine",
            "decision": "APPROVED",
            "baseline_status": "FROZEN",
            "baseline_id": baseline_id,
            "approved_at": approved_at,
            "certification": (
                "RC1_END_TO_END_CERTIFIED"
            ),
            "checks": {
                "total": certification["checks_total"],
                "passed": certification["checks_passed"],
                "failed": certification["checks_failed"],
                "warnings": len(
                    certification.get("warnings", [])
                ),
            },
            "allocation_model": (
                "DYNAMIC_POLICY_DRIVEN"
            ),
            "aggregate_sha256": manifest[
                "aggregate_sha256"
            ],
            "release_gate_path": str(
                RELEASE_GATE_JSON
            ),
            "baseline_path": str(baseline_dir),
            "git_commit": git_metadata.get("commit"),
            "git_branch": git_metadata.get("branch"),
            "git_dirty": git_metadata.get("dirty"),
        }

        append_release_history(history_entry)

        print()
        print("===== RC1 RELEASE FREEZE COMPLETE =====")
        print("Decision: APPROVED")
        print("Baseline status: FROZEN")
        print(f"Baseline ID: {baseline_id}")
        print(
            "Allocation model: "
            "DYNAMIC_POLICY_DRIVEN"
        )
        print(
            "Weights permanently fixed: false"
        )
        print(
            "Policy frozen: true"
        )
        print(
            f"Artifacts archived: "
            f"{manifest['artifact_count']}"
        )
        print(
            "Aggregate SHA-256: "
            f"{manifest['aggregate_sha256']}"
        )
        print(
            f"Release Gate JSON: "
            f"{RELEASE_GATE_JSON}"
        )
        print(
            f"Release Gate Markdown: "
            f"{RELEASE_GATE_MD}"
        )
        print(
            f"Baseline directory: "
            f"{baseline_dir}"
        )
        print(
            f"Release history: "
            f"{RELEASE_HISTORY}"
        )

    except Exception:
        if baseline_dir.exists():
            shutil.rmtree(
                baseline_dir,
                ignore_errors=True,
            )
        raise

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"RC1 RELEASE FREEZE FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
