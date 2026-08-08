from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from fastapi import APIRouter


router = APIRouter(tags=["system-go-no-go"])


SUPERVISION_GATE = Path(
    "/opt/nsc/data/preprod/portfolio/audit/"
    "supervision_gate.json"
)

PRODUCTION_READINESS = Path(
    "/opt/nsc/data/preprod/portfolio/audit/"
    "global_preprod_production_readiness.json"
)

COMMITTEE_REVIEW = Path(
    "/opt/nsc/data/preprod/portfolio/audit/"
    "global_preprod_committee_review.json"
)

PREPROD_GO_NO_GO = Path(
    "/opt/nsc/app/data/audits/"
    "preprod_go_nogo_master_audit.json"
)

RC1_RELEASE_GATE = Path(
    "/opt/nsc/data/preprod/releases/RC1/"
    "rc1_release_gate.json"
)

RC1_GLOBAL_CERTIFICATION = Path(
    "/opt/nsc/app/data/audits/"
    "rc1_07e_global_certification_20260801T125158Z.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}


def age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None

    modified = datetime.fromtimestamp(
        path.stat().st_mtime,
        timezone.utc,
    )

    return round(
        (
            datetime.now(timezone.utc)
            - modified
        ).total_seconds(),
        2,
    )


def source_payload(
    name: str,
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "age_seconds": age_seconds(path),
        "engine": payload.get("engine"),
        "generated_at": (
            payload.get("generated_at")
            or payload.get("updated_at")
            or payload.get("approved_at")
            or payload.get("audited_at_utc")
        ),
    }


@router.get(
    "/api/system/go-no-go",
    summary="Institutional NSC Go / No-Go status",
)
def get_system_go_no_go() -> dict[str, Any]:
    supervision = read_json(SUPERVISION_GATE)
    readiness = read_json(PRODUCTION_READINESS)
    committee = read_json(COMMITTEE_REVIEW)
    preprod_audit = read_json(PREPROD_GO_NO_GO)
    release_gate = read_json(RC1_RELEASE_GATE)
    global_cert = read_json(RC1_GLOBAL_CERTIFICATION)

    supervision_summary = (
        supervision.get("summary", {})
        if isinstance(supervision.get("summary"), dict)
        else {}
    )

    supervision_actions = (
        supervision.get("recommended_actions", {})
        if isinstance(
            supervision.get("recommended_actions"),
            dict,
        )
        else {}
    )

    readiness_checks = (
        readiness.get("checks", {})
        if isinstance(readiness.get("checks"), dict)
        else {}
    )

    release_certification = (
        release_gate.get("certification", {})
        if isinstance(
            release_gate.get("certification"),
            dict,
        )
        else {}
    )

    release_governance = (
        release_gate.get("governance", {})
        if isinstance(
            release_gate.get("governance"),
            dict,
        )
        else {}
    )

    old_audit_summary = (
        preprod_audit.get("summary", {})
        if isinstance(preprod_audit.get("summary"), dict)
        else {}
    )

    committee_values = (
        committee.get("committees", {})
        if isinstance(committee.get("committees"), dict)
        else {}
    )

    automatic_checks = [
        {
            "id": "rc1_release_approved",
            "label": "RC1 officiellement approuvée",
            "status": (
                "PASS"
                if release_gate.get("decision") == "APPROVED"
                else "FAIL"
            ),
            "value": release_gate.get("decision"),
            "source": str(RC1_RELEASE_GATE),
        },
        {
            "id": "rc1_certification",
            "label": "Certification RC1 de bout en bout",
            "status": (
                "PASS"
                if (
                    release_certification.get("status") == "PASS"
                    and int(
                        release_certification.get(
                            "blocking_failures_count",
                            0,
                        )
                        or 0
                    )
                    == 0
                )
                else "FAIL"
            ),
            "value": {
                "status": release_certification.get("status"),
                "checks_passed": (
                    release_certification.get("checks_passed")
                ),
                "checks_total": (
                    release_certification.get("checks_total")
                ),
                "blocking_failures": (
                    release_certification.get(
                        "blocking_failures_count"
                    )
                ),
            },
            "source": str(RC1_RELEASE_GATE),
        },
        {
            "id": "global_certification",
            "label": "Certification globale post-remédiation",
            "status": (
                "PASS"
                if (
                    global_cert.get("verdict") == "PASS"
                    and int(
                        global_cert.get(
                            "failure_count",
                            0,
                        )
                        or 0
                    )
                    == 0
                )
                else "FAIL"
            ),
            "value": {
                "verdict": global_cert.get("verdict"),
                "failure_count": global_cert.get(
                    "failure_count"
                ),
            },
            "source": str(RC1_GLOBAL_CERTIFICATION),
        },
        {
            "id": "supervision_gate",
            "label": "Supervision gate ouvert en mode sûr",
            "status": (
                "PASS"
                if (
                    supervision.get("gate_open") is True
                    and supervision.get("blocking") is False
                    and int(
                        supervision_summary.get(
                            "blocking_checks",
                            0,
                        )
                        or 0
                    )
                    == 0
                )
                else "FAIL"
            ),
            "value": {
                "gate_open": supervision.get("gate_open"),
                "mode": supervision.get("mode"),
                "blocking": supervision.get("blocking"),
                "blocking_checks": (
                    supervision_summary.get(
                        "blocking_checks"
                    )
                ),
                "warning_checks": (
                    supervision_summary.get(
                        "warning_checks"
                    )
                ),
            },
            "source": str(SUPERVISION_GATE),
        },
        {
            "id": "simulated_execution_only",
            "label": "Exécution simulée autorisée et réelle interdite",
            "status": (
                "PASS"
                if (
                    supervision_actions.get(
                        "allow_simulated_execution"
                    )
                    is True
                    and supervision_actions.get(
                        "allow_real_execution"
                    )
                    is False
                    and release_governance.get(
                        "real_execution_allowed"
                    )
                    is False
                )
                else "FAIL"
            ),
            "value": {
                "simulated_execution_allowed": (
                    supervision_actions.get(
                        "allow_simulated_execution"
                    )
                ),
                "real_execution_allowed": (
                    supervision_actions.get(
                        "allow_real_execution"
                    )
                ),
                "action_policy": (
                    release_governance.get(
                        "action_policy"
                    )
                ),
            },
            "source": str(SUPERVISION_GATE),
        },
        {
            "id": "production_readiness",
            "label": "Production readiness institutionnelle",
            "status": (
                "PASS"
                if (
                    readiness.get("decision") == "GO"
                    and float(
                        readiness.get(
                            "readiness_score",
                            0,
                        )
                        or 0
                    )
                    >= 100
                    and int(
                        readiness_checks.get(
                            "blocking_checks",
                            0,
                        )
                        or 0
                    )
                    == 0
                )
                else "FAIL"
            ),
            "value": {
                "decision": readiness.get("decision"),
                "readiness_score": readiness.get(
                    "readiness_score"
                ),
                "progress_pct": readiness.get(
                    "progress_pct"
                ),
                "blocking_checks": (
                    readiness_checks.get(
                        "blocking_checks"
                    )
                ),
                "warning_checks": (
                    readiness_checks.get(
                        "warning_checks"
                    )
                ),
            },
            "source": str(PRODUCTION_READINESS),
        },
        {
            "id": "legacy_go_no_go_audit",
            "label": "Audit maître Go / No-Go",
            "status": (
                "PASS"
                if (
                    old_audit_summary.get("audits_critical", 0) == 0
                    and old_audit_summary.get("audits_missing", 0) == 0
                    and str(
                        old_audit_summary.get(
                            "go_nogo",
                            "",
                        )
                    ).startswith("GO")
                )
                else "FAIL"
            ),
            "value": {
                "go_nogo": old_audit_summary.get(
                    "go_nogo"
                ),
                "audits_ok": old_audit_summary.get(
                    "audits_ok"
                ),
                "audits_total": old_audit_summary.get(
                    "audits_total"
                ),
                "audits_critical": (
                    old_audit_summary.get(
                        "audits_critical"
                    )
                ),
            },
            "source": str(PREPROD_GO_NO_GO),
        },
    ]

    blocking_checks = [
        check
        for check in automatic_checks
        if check.get("status") != "PASS"
    ]

    automatic_pass = len(blocking_checks) == 0

    automatic_decision = (
        "GO_RC2_PREPROD"
        if automatic_pass
        else "NO_GO_REMEDIATION_REQUIRED"
    )

    manual_controls = [
        {
            "id": "external_audit_review",
            "label": "Audit externe IA relu et accepté",
            "description": (
                "Contrôle humain à réaliser avant validation "
                "finale RC2."
            ),
        },
        {
            "id": "operational_playbook_review",
            "label": "Playbooks d’incident relus",
            "description": (
                "Vérification humaine des procédures de "
                "reprise et d’escalade."
            ),
        },
        {
            "id": "dashboard_visual_review",
            "label": "Revue visuelle complète du dashboard",
            "description": (
                "Contrôle manuel des écrans après les "
                "remédiations de lineage."
            ),
        },
        {
            "id": "rc2_launch_authorization",
            "label": "Autorisation humaine de démarrage RC2",
            "description": (
                "Validation finale du responsable NSC avant "
                "le lancement de la session."
            ),
        },
    ]

    sources = [
        source_payload(
            "supervision_gate",
            SUPERVISION_GATE,
            supervision,
        ),
        source_payload(
            "production_readiness",
            PRODUCTION_READINESS,
            readiness,
        ),
        source_payload(
            "committee_review",
            COMMITTEE_REVIEW,
            committee,
        ),
        source_payload(
            "preprod_go_no_go",
            PREPROD_GO_NO_GO,
            preprod_audit,
        ),
        source_payload(
            "rc1_release_gate",
            RC1_RELEASE_GATE,
            release_gate,
        ),
        source_payload(
            "rc1_global_certification",
            RC1_GLOBAL_CERTIFICATION,
            global_cert,
        ),
    ]

    return {
        "status": "ok",
        "engine": "institutional_go_no_go_v1",
        "environment": "PREPROD",
        "automatic_decision": automatic_decision,
        "automatic_pass": automatic_pass,
        "automatic_check_count": len(automatic_checks),
        "automatic_pass_count": len(
            [
                check
                for check in automatic_checks
                if check.get("status") == "PASS"
            ]
        ),
        "blocking_check_count": len(blocking_checks),
        "automatic_checks": automatic_checks,
        "blocking_checks": blocking_checks,
        "manual_controls": manual_controls,
        "institutional_state": {
            "rc1_release": release_gate.get("release"),
            "rc1_release_decision": (
                release_gate.get("decision")
            ),
            "rc1_approved_at": (
                release_gate.get("approved_at")
            ),
            "production_readiness_decision": (
                readiness.get("decision")
            ),
            "production_readiness_score": (
                readiness.get("readiness_score")
            ),
            "supervision_gate_open": (
                supervision.get("gate_open")
            ),
            "supervision_gate_mode": (
                supervision.get("mode")
            ),
            "real_execution_allowed": (
                supervision_actions.get(
                    "allow_real_execution"
                )
            ),
            "simulated_execution_allowed": (
                supervision_actions.get(
                    "allow_simulated_execution"
                )
            ),
            "manual_funding_required": (
                supervision_actions.get(
                    "manual_funding_required"
                )
            ),
            "committee_progress": (
                committee.get("progress", {})
            ),
            "committee_statuses": committee_values,
            "committee_trajectory": (
                committee.get("trajectory", {})
            ),
            "accepted_non_blocking_debt": (
                release_gate.get(
                    "accepted_non_blocking_debt",
                    [],
                )
            ),
        },
        "sources": sources,
        "safety_statement": (
            "The automatic institutional decision cannot be "
            "overridden by browser-local manual controls."
        ),
        "generated_at": utc_now(),
    }
