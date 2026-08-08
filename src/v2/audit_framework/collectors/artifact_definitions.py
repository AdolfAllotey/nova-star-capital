from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.v2.audit_framework.core.constants import (
    APP_DIR,
    DATA_DIR,
)
from src.v2.audit_framework.core.enums import (
    ArtifactRole,
)


@dataclass(frozen=True)
class ArtifactDefinition:
    artifact_id: str
    role: ArtifactRole
    destination_name: str
    required: bool
    exact_paths: tuple[Path, ...] = field(
        default_factory=tuple
    )
    glob_patterns: tuple[str, ...] = field(
        default_factory=tuple
    )
    description: str = ""
    allow_multiple: bool = False


def build_rc1_artifact_definitions(
) -> tuple[ArtifactDefinition, ...]:
    release_dir = (
        DATA_DIR
        / "releases"
        / "RC1"
    )

    governance_dir = (
        DATA_DIR
        / "governance"
    )

    return (
        ArtifactDefinition(
            artifact_id="rc1_release_gate",
            role=ArtifactRole.RELEASE_GATE,
            destination_name=(
                "governance/rc1_release_gate.json"
            ),
            required=True,
            exact_paths=(
                release_dir
                / "rc1_release_gate.json",
            ),
            description=(
                "Official machine-readable "
                "RC1 release gate."
            ),
        ),
        ArtifactDefinition(
            artifact_id="rc1_release_gate_markdown",
            role=ArtifactRole.RELEASE_GATE,
            destination_name=(
                "governance/RC1_RELEASE_GATE.md"
            ),
            required=False,
            exact_paths=(
                release_dir
                / "RC1_RELEASE_GATE.md",
            ),
            description=(
                "Human-readable RC1 release gate."
            ),
        ),
        ArtifactDefinition(
            artifact_id="rc1_current_baseline",
            role=ArtifactRole.BASELINE_POINTER,
            destination_name=(
                "baseline/current_baseline.json"
            ),
            required=True,
            exact_paths=(
                release_dir
                / "current_baseline.json",
            ),
            description=(
                "Official pointer to the frozen "
                "RC1 baseline."
            ),
        ),
        ArtifactDefinition(
            artifact_id="rc1_release_history",
            role=ArtifactRole.GOVERNANCE,
            destination_name=(
                "history/release_history.jsonl"
            ),
            required=False,
            exact_paths=(
                DATA_DIR
                / "releases"
                / "release_history.jsonl",
            ),
            description=(
                "Release history ledger."
            ),
        ),
        ArtifactDefinition(
            artifact_id="nsc_master_document",
            role=ArtifactRole.MASTER_DOCUMENT,
            destination_name=(
                "master/MASTER_NOVA_STAR_CAPITAL.md"
            ),
            required=True,
            exact_paths=(
                APP_DIR
                / "docs"
                / "MASTER_NOVA_STAR_CAPITAL.md",
            ),
            description=(
                "Nova Star Capital institutional "
                "Master document."
            ),
        ),
        ArtifactDefinition(
            artifact_id="nsc_master_status",
            role=ArtifactRole.MASTER_STATUS,
            destination_name=(
                "master/nsc_master_status.json"
            ),
            required=True,
            exact_paths=(
                governance_dir
                / "nsc_master_status.json",
            ),
            description=(
                "Machine-readable Master status."
            ),
        ),
        ArtifactDefinition(
            artifact_id="nsc_master_history",
            role=ArtifactRole.GOVERNANCE,
            destination_name=(
                "history/nsc_master_history.jsonl"
            ),
            required=False,
            exact_paths=(
                governance_dir
                / "nsc_master_history.jsonl",
            ),
            description=(
                "Master governance history ledger."
            ),
        ),
        ArtifactDefinition(
            artifact_id="rc1_certifications",
            role=ArtifactRole.CERTIFICATION,
            destination_name=(
                "certifications"
            ),
            required=False,
            glob_patterns=(
                str(
                    DATA_DIR
                    / "**"
                    / "*RC1*certif*.json"
                ),
                str(
                    DATA_DIR
                    / "**"
                    / "*rc1*certif*.json"
                ),
                str(
                    DATA_DIR
                    / "**"
                    / "*end_to_end*certif*.json"
                ),
                str(
                    DATA_DIR
                    / "**"
                    / "*certification*.json"
                ),
            ),
            description=(
                "RC1 and end-to-end certification "
                "artifacts."
            ),
            allow_multiple=True,
        ),
        ArtifactDefinition(
            artifact_id="baseline_manifests",
            role=ArtifactRole.BASELINE_MANIFEST,
            destination_name=(
                "baseline/manifests"
            ),
            required=False,
            glob_patterns=(
                str(
                    release_dir
                    / "**"
                    / "*manifest*.json"
                ),
                str(
                    release_dir
                    / "**"
                    / "*baseline*.json"
                ),
            ),
            description=(
                "Baseline manifests and related "
                "machine-readable inventories."
            ),
            allow_multiple=True,
        ),
        ArtifactDefinition(
            artifact_id="architecture_documents",
            role=(
                ArtifactRole.ARCHITECTURE_DOCUMENT
            ),
            destination_name=(
                "architecture"
            ),
            required=False,
            glob_patterns=(
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*ARCHITECTURE*.md"
                ),
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*architecture*.md"
                ),
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*ARCHITECTURE*.json"
                ),
            ),
            description=(
                "Available architecture documents."
            ),
            allow_multiple=True,
        ),
        ArtifactDefinition(
            artifact_id="engineering_constitution",
            role=(
                ArtifactRole.ENGINEERING_CONSTITUTION
            ),
            destination_name=(
                "governance/"
                "ENGINEERING_CONSTITUTION"
            ),
            required=False,
            glob_patterns=(
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*ENGINEERING*CONSTITUTION*"
                ),
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*engineering*constitution*"
                ),
            ),
            description=(
                "Nova Star Capital Engineering "
                "Constitution, if already stored."
            ),
            allow_multiple=True,
        ),
        ArtifactDefinition(
            artifact_id="component_inventory",
            role=ArtifactRole.SOURCE_INVENTORY,
            destination_name=(
                "inventory"
            ),
            required=False,
            glob_patterns=(
                str(
                    DATA_DIR
                    / "**"
                    / "*component*inventory*.json"
                ),
                str(
                    DATA_DIR
                    / "**"
                    / "*enterprise*inventory*.json"
                ),
                str(
                    APP_DIR
                    / "docs"
                    / "**"
                    / "*COMPONENT*INVENTORY*"
                ),
            ),
            description=(
                "Enterprise component or source "
                "inventory artifacts."
            ),
            allow_multiple=True,
        ),
    )
