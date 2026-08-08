from __future__ import annotations

from pathlib import Path
import os


AUDIT_FRAMEWORK_NAME = "NSC_AUDIT_FRAMEWORK"
AUDIT_FRAMEWORK_VERSION = "1.0.0"
AUDIT_FRAMEWORK_SCHEMA_VERSION = "1.0"

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

AUDIT_DATA_DIR = (
    DATA_DIR
    / "audits"
    / "audit_framework"
)

PACKAGES_DIR = AUDIT_DATA_DIR / "packages"
REPORTS_DIR = AUDIT_DATA_DIR / "reports"
MANIFESTS_DIR = AUDIT_DATA_DIR / "manifests"
REGISTRY_DIR = AUDIT_DATA_DIR / "registry"
TEMP_DIR = AUDIT_DATA_DIR / "tmp"

RC1_RELEASE_GATE_PATH = (
    DATA_DIR
    / "releases"
    / "RC1"
    / "rc1_release_gate.json"
)

RC1_CURRENT_BASELINE_PATH = (
    DATA_DIR
    / "releases"
    / "RC1"
    / "current_baseline.json"
)

NSC_MASTER_PATH = Path(
    os.getenv(
        "NSC_MASTER_PATH",
        str(
            APP_DIR
            / "docs"
            / "MASTER_NOVA_STAR_CAPITAL.md"
        ),
    )
)

NSC_MASTER_STATUS_PATH = (
    DATA_DIR
    / "governance"
    / "nsc_master_status.json"
)

FRAMEWORK_REGISTRY_PATH = (
    REGISTRY_DIR
    / "audit_framework_registry.json"
)

FRAMEWORK_HISTORY_PATH = (
    REGISTRY_DIR
    / "audit_framework_history.jsonl"
)
