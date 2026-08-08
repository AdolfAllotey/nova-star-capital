from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from src.v2.audit_framework.core.utils import (
    atomic_write_json,
    atomic_write_text,
    read_json,
    sha256_file,
    utc_now_iso,
)
from src.v2.audit_framework.manifests.package_models import (
    AuditPackageManifest,
    PackageFile,
)


class RC1AuditPackageBuilder:
    """
    Build a provider-independent institutional audit package.

    The builder does not invoke an audit provider and does not modify
    certified RC1 source artifacts.
    """

    EXCLUDED_FROM_READINESS_HASH = {
        "AUDIT_PACKAGE_MANIFEST.json",
        "AUDIT_PACKAGE_READY.json",
        "PACKAGE_CHECKSUMS.sha256",
    }

    MUTABLE_PACKAGE_PREFIXES = (
        "execution_gates/",
        "provider_payloads/",
    )

    def __init__(
        self,
        package_dir: Path,
    ) -> None:
        self.package_dir = package_dir.resolve()

        self.collection_report_path = (
            self.package_dir
            / "artifact_collection_report.json"
        )

        self.validation_report_path = (
            self.package_dir
            / "baseline_validation_report.json"
        )

        self.audit_request_path = (
            self.package_dir
            / "audit_request.json"
        )

        self.inventory_path = (
            self.package_dir
            / "artifact_inventory.json"
        )

    def _load_inputs(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        required = (
            self.collection_report_path,
            self.validation_report_path,
            self.audit_request_path,
            self.inventory_path,
        )

        for path in required:
            if not path.is_file():
                raise RuntimeError(
                    f"Missing package input: {path}"
                )

        collection = read_json(
            self.collection_report_path
        )

        validation = read_json(
            self.validation_report_path
        )

        request = read_json(
            self.audit_request_path
        )

        inventory = read_json(
            self.inventory_path
        )

        if collection.get("status") != "PASS":
            raise RuntimeError(
                "Artifact collection is not PASS."
            )

        if validation.get("status") != "PASS":
            raise RuntimeError(
                "Baseline validation is not PASS."
            )

        if (
            validation.get(
                "summary",
                {},
            ).get(
                "blocking_failures"
            )
            != 0
        ):
            raise RuntimeError(
                "Baseline validation contains "
                "blocking failures."
            )

        return (
            collection,
            validation,
            request,
            inventory,
        )

    @staticmethod
    def _build_executive_summary(
        validation: dict[str, Any],
        collection: dict[str, Any],
    ) -> str:
        summary = validation["summary"]
        collection_summary = collection["summary"]

        return "\n".join(
            [
                "# RC1 Engineering Audit — Executive Brief",
                "",
                "## Release identity",
                "",
                f"- Release: `{validation['release']}`",
                (
                    "- Baseline ID: "
                    f"`{validation['baseline_id']}`"
                ),
                (
                    "- Baseline status: "
                    "`FROZEN`"
                ),
                (
                    "- Release decision: "
                    "`APPROVED`"
                ),
                (
                    "- Audit package status: "
                    "`READY_FOR_PROVIDER_AUDIT`"
                ),
                "",
                "## Integrity",
                "",
                (
                    "- RC1 aggregate SHA-256: "
                    f"`{summary['aggregate_sha256']}`"
                ),
                (
                    "- Collection aggregate SHA-256: "
                    f"`{collection_summary['aggregate_sha256']}`"
                ),
                (
                    "- Collected artifacts: "
                    f"`{collection_summary['total_collected']}`"
                ),
                (
                    "- Required artifacts: "
                    f"`{collection_summary['required_collected']}/"
                    f"{collection_summary['required_expected']}`"
                ),
                (
                    "- Validation checks passed: "
                    f"`{summary['passed']}`"
                ),
                (
                    "- Validation warnings: "
                    f"`{summary['warnings']}`"
                ),
                (
                    "- Blocking failures: "
                    f"`{summary['blocking_failures']}`"
                ),
                "",
                "## Frozen architecture decision",
                "",
                (
                    "- Allocation model: "
                    "`DYNAMIC_POLICY_DRIVEN`"
                ),
                "- Policy frozen: `true`",
                (
                    "- Allocation weights permanently "
                    "fixed: `false`"
                ),
                "",
                "The policy and governance rules are frozen. "
                "Portfolio weights remain dynamically determined "
                "by the approved allocation policy.",
                "",
                "## Audit purpose",
                "",
                (
                    "Perform an independent engineering review of "
                    "RC1 without modifying the certified baseline."
                ),
                "",
                "The audit must identify engineering risks, "
                "architectural weaknesses, technical debt, "
                "operational gaps and production-readiness issues. "
                "Recommendations must remain separate from "
                "implementation.",
                "",
                "## Provider state",
                "",
                "- Provider selected: `NONE`",
                "- Provider executed: `false`",
                "- Automatic remediation: `false`",
                "",
            ]
        )

    @staticmethod
    def _build_scope_document() -> str:
        return "\n".join(
            [
                "# RC1 Engineering Audit Scope",
                "",
                "## In scope",
                "",
                "- RC1 institutional architecture;",
                "- release and baseline governance;",
                "- component boundaries and responsibilities;",
                "- source-code structure and maintainability;",
                "- configuration and environment management;",
                "- data flows and persistence;",
                "- market-data integrity controls;",
                "- strategy and portfolio orchestration;",
                "- risk and governance enforcement;",
                "- execution isolation and simulation safety;",
                "- observability, logs and reporting;",
                "- error handling and failure containment;",
                "- tests, certifications and release gates;",
                "- security and secret-management risks;",
                "- performance and scalability risks;",
                "- dashboard/backend data integrity;",
                "- production-readiness gaps;",
                "- RC2 architectural impact and prerequisites.",
                "",
                "## Out of scope",
                "",
                "- modification of the frozen RC1 baseline;",
                "- execution of live trades;",
                "- activation of production credentials;",
                "- automatic remediation;",
                "- direct implementation of recommendations;",
                "- business approval of RC2 scope;",
                "- portfolio performance promises;",
                "- regulatory or legal certification.",
                "",
                "## Audit boundaries",
                "",
                (
                    "The collected artifacts represent the "
                    "certified RC1 baseline and its institutional "
                    "governance context."
                ),
                "",
                (
                    "The provider may inspect source code and "
                    "package evidence but must not write into the "
                    "certified baseline or production data paths."
                ),
                "",
            ]
        )

    @staticmethod
    def _build_provider_instructions() -> str:
        return "\n".join(
            [
                "# Provider Instructions — RC1 Engineering Audit",
                "",
                "## Role",
                "",
                (
                    "Act as an independent institutional software "
                    "engineering auditor."
                ),
                "",
                "Do not act as an implementation agent.",
                "",
                "## Mandatory rules",
                "",
                "1. Treat RC1 as frozen and immutable.",
                (
                    "2. Do not edit, delete, rename or regenerate "
                    "certified RC1 artifacts."
                ),
                (
                    "3. Do not execute live trading, broker or "
                    "exchange operations."
                ),
                (
                    "4. Do not use production credentials or "
                    "secrets."
                ),
                (
                    "5. Do not apply automatic fixes."
                ),
                (
                    "6. Separate findings, recommendations and "
                    "implementation proposals."
                ),
                (
                    "7. Every material finding must include "
                    "evidence."
                ),
                (
                    "8. Every recommendation must include impact, "
                    "priority, risk and suggested release."
                ),
                (
                    "9. Distinguish RC1 defects from RC2 "
                    "enhancements."
                ),
                (
                    "10. Preserve the approved dynamic allocation "
                    "architecture."
                ),
                "",
                "## Frozen allocation decision",
                "",
                "- Model: `DYNAMIC_POLICY_DRIVEN`",
                "- Policy frozen: `true`",
                "- Weights permanently fixed: `false`",
                "",
                (
                    "Do not recommend replacing dynamic allocation "
                    "with permanently hard-coded portfolio weights."
                ),
                "",
                "## Required analysis method",
                "",
                "For each domain:",
                "",
                "- describe the observed architecture;",
                "- identify strengths;",
                "- identify weaknesses;",
                "- provide file-level evidence;",
                "- assess severity and likelihood;",
                "- assess operational and financial impact;",
                "- identify dependencies;",
                "- propose remediation options;",
                "- classify the target release;",
                "- avoid implementation unless requested later.",
                "",
                "## Finding severity",
                "",
                "- `CRITICAL`: production or capital safety risk;",
                "- `HIGH`: major reliability or governance risk;",
                "- `MEDIUM`: material engineering weakness;",
                "- `LOW`: limited or local weakness;",
                "- `INFO`: observation or improvement opportunity.",
                "",
                "## Recommendation categories",
                "",
                "- `RC1_HOTFIX`",
                "- `RC1_HARDENING`",
                "- `RC2_PREREQUISITE`",
                "- `RC2_ENHANCEMENT`",
                "- `PRODUCTION_READINESS`",
                "- `LONG_TERM_ARCHITECTURE`",
                "- `DOCUMENTATION`",
                "- `TESTING_AND_CERTIFICATION`",
                "",
            ]
        )

    @staticmethod
    def _build_review_checklist() -> str:
        domains = [
            (
                "Architecture",
                "Boundaries, coupling, dependency direction, "
                "single points of failure."
            ),
            (
                "Governance",
                "Release gates, baseline immutability, approvals, "
                "traceability."
            ),
            (
                "Data integrity",
                "Source quality, freshness, reconciliation, "
                "fallback behavior."
            ),
            (
                "Portfolio engine",
                "Capital allocation, state consistency, "
                "rebalancing and cash controls."
            ),
            (
                "Strategies",
                "Signal lifecycle, scoring, vetoes, sizing and "
                "strategy isolation."
            ),
            (
                "Risk",
                "Limits, exposure, concentration, drawdown and "
                "kill-switch controls."
            ),
            (
                "Execution",
                "Simulation isolation, idempotency, order state "
                "and broker boundaries."
            ),
            (
                "Persistence",
                "Atomic writes, corruption handling, migrations "
                "and historical traceability."
            ),
            (
                "Observability",
                "Logs, metrics, alerts, audit history and failure "
                "visibility."
            ),
            (
                "Security",
                "Secrets, permissions, injection risks and unsafe "
                "command execution."
            ),
            (
                "Testing",
                "Unit, integration, end-to-end, regression and "
                "failure-path coverage."
            ),
            (
                "Dashboard",
                "Backend/UI consistency, hard-coded values and "
                "stale data risks."
            ),
            (
                "Performance",
                "Complexity, expensive scans, network usage and "
                "scalability."
            ),
            (
                "Production readiness",
                "Operational runbooks, rollback, recovery and "
                "deployment controls."
            ),
            (
                "RC2 impact",
                "Options integration prerequisites and regression "
                "risks."
            ),
        ]

        lines = [
            "# RC1 Engineering Review Checklist",
            "",
        ]

        for title, description in domains:
            lines.extend(
                [
                    f"## {title}",
                    "",
                    f"- [ ] {description}",
                    "- [ ] Evidence captured",
                    "- [ ] Severity assigned",
                    "- [ ] Recommendation classified",
                    "- [ ] Target release assigned",
                    "",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _build_deliverables_document() -> str:
        return "\n".join(
            [
                "# Expected Audit Deliverables",
                "",
                "The provider must return the following outputs.",
                "",
                "## 1. Executive audit report",
                "",
                "- overall conclusion;",
                "- production-readiness assessment;",
                "- top risks;",
                "- top strengths;",
                "- Go / Conditional Go / No-Go opinion.",
                "",
                "## 2. Engineering scorecard",
                "",
                "Score each domain from 0 to 100:",
                "",
                "- architecture;",
                "- code quality;",
                "- reliability;",
                "- data integrity;",
                "- risk controls;",
                "- security;",
                "- observability;",
                "- testing;",
                "- maintainability;",
                "- production readiness.",
                "",
                "## 3. Findings register",
                "",
                "Each finding must contain:",
                "",
                "- unique ID;",
                "- title;",
                "- domain;",
                "- severity;",
                "- description;",
                "- evidence;",
                "- affected components;",
                "- impact;",
                "- likelihood;",
                "- root cause;",
                "- recommendation;",
                "- target release;",
                "- implementation complexity.",
                "",
                "## 4. Recommendation register",
                "",
                "Recommendations must be grouped into:",
                "",
                "- immediate RC1 hotfixes;",
                "- RC1 hardening;",
                "- RC2 prerequisites;",
                "- RC2 enhancements;",
                "- production-readiness work;",
                "- long-term architecture.",
                "",
                "## 5. RC2 impact analysis",
                "",
                "- dependencies created by Options;",
                "- portfolio and risk impacts;",
                "- execution impacts;",
                "- data and broker impacts;",
                "- dashboard impacts;",
                "- regression risks;",
                "- certification requirements.",
                "",
                "## 6. Remediation roadmap",
                "",
                "- priority;",
                "- sequence;",
                "- dependencies;",
                "- estimated complexity;",
                "- release assignment;",
                "- validation required.",
                "",
                "## 7. Machine-readable report",
                "",
                (
                    "Provide a structured JSON report compatible "
                    "with the Audit Framework normalization phase."
                ),
                "",
                "No recommendation may be implemented automatically.",
                "",
            ]
        )

    @staticmethod
    def _build_recommendation_policy() -> str:
        return "\n".join(
            [
                "# Recommendation Classification Policy",
                "",
                "## RC1_HOTFIX",
                "",
                (
                    "A defect that invalidates RC1 certification, "
                    "creates an immediate capital-safety risk or "
                    "prevents reliable preproduction operation."
                ),
                "",
                "## RC1_HARDENING",
                "",
                (
                    "A material weakness that should be corrected "
                    "before production but does not invalidate the "
                    "frozen RC1 baseline."
                ),
                "",
                "## RC2_PREREQUISITE",
                "",
                (
                    "A change required before Options or another "
                    "RC2 capability can be safely integrated."
                ),
                "",
                "## RC2_ENHANCEMENT",
                "",
                (
                    "A functional or architectural improvement "
                    "that belongs naturally to RC2."
                ),
                "",
                "## PRODUCTION_READINESS",
                "",
                (
                    "Operational work required before deployment "
                    "with real capital."
                ),
                "",
                "## LONG_TERM_ARCHITECTURE",
                "",
                (
                    "Strategic architecture improvements not "
                    "required for RC1 or RC2 approval."
                ),
                "",
                "## DOCUMENTATION",
                "",
                (
                    "Missing, inconsistent or insufficient "
                    "technical and operational documentation."
                ),
                "",
                "## TESTING_AND_CERTIFICATION",
                "",
                (
                    "Additional tests, evidence or certification "
                    "gates required to establish confidence."
                ),
                "",
            ]
        )

    @staticmethod
    def _build_package_index(
        validation: dict[str, Any],
        collection: dict[str, Any],
    ) -> str:
        return "\n".join(
            [
                "# RC1 Audit Package Index",
                "",
                "## Package status",
                "",
                "- Status: `READY_FOR_PROVIDER_AUDIT`",
                (
                    "- Audit ID: "
                    f"`{validation['audit_id']}`"
                ),
                (
                    "- Baseline ID: "
                    f"`{validation['baseline_id']}`"
                ),
                "- Provider: `NONE`",
                "- Provider executed: `false`",
                "",
                "## Start here",
                "",
                "1. `EXECUTIVE_AUDIT_BRIEF.md`",
                "2. `AUDIT_SCOPE.md`",
                "3. `PROVIDER_INSTRUCTIONS.md`",
                "4. `ENGINEERING_REVIEW_CHECKLIST.md`",
                "5. `EXPECTED_DELIVERABLES.md`",
                "6. `RECOMMENDATION_POLICY.md`",
                "",
                "## Control evidence",
                "",
                "- `audit_request.json`",
                "- `artifact_collection_report.json`",
                "- `artifact_inventory.json`",
                "- `baseline_validation_report.json`",
                "- `ARTIFACT_COLLECTION_REPORT.md`",
                "- `BASELINE_VALIDATION_REPORT.md`",
                "",
                "## Collected evidence",
                "",
                (
                    f"`{collection['summary']['total_collected']}` "
                    "collected files are stored under "
                    "`artifacts/`."
                ),
                "",
                "## Package control files",
                "",
                "- `AUDIT_PACKAGE_MANIFEST.json`",
                "- `PACKAGE_CHECKSUMS.sha256`",
                "- `AUDIT_PACKAGE_READY.json`",
                "",
                "The checksum manifest excludes itself and the "
                "final package manifest to avoid circular hashing.",
                "",
            ]
        )

    def _write_control_documents(
        self,
        validation: dict[str, Any],
        collection: dict[str, Any],
    ) -> None:
        documents = {
            "EXECUTIVE_AUDIT_BRIEF.md": (
                self._build_executive_summary(
                    validation,
                    collection,
                )
            ),
            "AUDIT_SCOPE.md": (
                self._build_scope_document()
            ),
            "PROVIDER_INSTRUCTIONS.md": (
                self._build_provider_instructions()
            ),
            "ENGINEERING_REVIEW_CHECKLIST.md": (
                self._build_review_checklist()
            ),
            "EXPECTED_DELIVERABLES.md": (
                self._build_deliverables_document()
            ),
            "RECOMMENDATION_POLICY.md": (
                self._build_recommendation_policy()
            ),
            "PACKAGE_INDEX.md": (
                self._build_package_index(
                    validation,
                    collection,
                )
            ),
        }

        for filename, content in documents.items():
            atomic_write_text(
                self.package_dir / filename,
                content,
            )

    def _enumerate_files(
        self,
    ) -> list[Path]:
        files: list[Path] = []

        for path in self.package_dir.rglob("*"):
            if not path.is_file():
                continue

            relative = str(
                path.relative_to(
                    self.package_dir
                )
            )

            if (
                path.name
                in self.EXCLUDED_FROM_READINESS_HASH
            ):
                continue

            if relative.startswith(
                self.MUTABLE_PACKAGE_PREFIXES
            ):
                continue

            files.append(path)

        return sorted(
            files,
            key=lambda item: str(
                item.relative_to(
                    self.package_dir
                )
            ),
        )

    def _calculate_readiness_hash(
        self,
        files: list[Path],
    ) -> str:
        digest = hashlib.sha256()

        for path in files:
            relative = str(
                path.relative_to(
                    self.package_dir
                )
            )

            digest.update(
                relative.encode("utf-8")
            )
            digest.update(b"\0")
            digest.update(
                sha256_file(path).encode(
                    "ascii"
                )
            )
            digest.update(b"\n")

        return digest.hexdigest()

    @staticmethod
    def _infer_role(
        relative: str,
    ) -> tuple[str, bool, str]:
        filename = Path(relative).name

        role_map = {
            "audit_request.json": (
                "AUDIT_REQUEST",
                True,
                "Original provider-independent audit request.",
            ),
            "artifact_collection_report.json": (
                "COLLECTION_REPORT",
                True,
                "Machine-readable artifact collection result.",
            ),
            "artifact_inventory.json": (
                "ARTIFACT_INVENTORY",
                True,
                "Inventory and checksums of collected evidence.",
            ),
            "baseline_validation_report.json": (
                "BASELINE_VALIDATION",
                True,
                "Machine-readable RC1 baseline validation.",
            ),
            "EXECUTIVE_AUDIT_BRIEF.md": (
                "EXECUTIVE_BRIEF",
                True,
                "Executive context and frozen decisions.",
            ),
            "AUDIT_SCOPE.md": (
                "AUDIT_SCOPE",
                True,
                "Audit boundaries and domains.",
            ),
            "PROVIDER_INSTRUCTIONS.md": (
                "PROVIDER_INSTRUCTIONS",
                True,
                "Mandatory provider operating rules.",
            ),
            "ENGINEERING_REVIEW_CHECKLIST.md": (
                "REVIEW_CHECKLIST",
                True,
                "Engineering review checklist.",
            ),
            "EXPECTED_DELIVERABLES.md": (
                "DELIVERABLE_SPECIFICATION",
                True,
                "Required audit outputs.",
            ),
            "RECOMMENDATION_POLICY.md": (
                "RECOMMENDATION_POLICY",
                True,
                "Recommendation classification rules.",
            ),
            "PACKAGE_INDEX.md": (
                "PACKAGE_INDEX",
                True,
                "Human-readable package navigation.",
            ),
            "AUDIT_PACKAGE_READY.json": (
                "READINESS_GATE",
                True,
                "Machine-readable package readiness decision.",
            ),
        }

        if filename in role_map:
            return role_map[filename]

        if relative.startswith("artifacts/"):
            return (
                "COLLECTED_EVIDENCE",
                False,
                "Collected RC1 audit evidence.",
            )

        if filename.endswith(".md"):
            return (
                "SUPPORTING_DOCUMENT",
                False,
                "Supporting human-readable document.",
            )

        return (
            "SUPPORTING_ARTIFACT",
            False,
            "Supporting package artifact.",
        )

    def build(
        self,
    ) -> AuditPackageManifest:
        (
            collection,
            validation,
            request,
            inventory,
        ) = self._load_inputs()

        self._write_control_documents(
            validation,
            collection,
        )

        existing_ready_path = (
            self.package_dir
            / "AUDIT_PACKAGE_READY.json"
        )

        existing_manifest_path = (
            self.package_dir
            / "AUDIT_PACKAGE_MANIFEST.json"
        )

        existing_ready = (
            read_json(existing_ready_path)
            if existing_ready_path.is_file()
            else {}
        )

        existing_manifest = (
            read_json(existing_manifest_path)
            if existing_manifest_path.is_file()
            else {}
        )

        package_created_at = (
            existing_ready.get("created_at")
            or existing_manifest.get("created_at")
            or utc_now_iso()
        )

        readiness_payload = {
            "schema_version": "1.0",
            "audit_id": validation[
                "audit_id"
            ],
            "release": validation[
                "release"
            ],
            "baseline_id": validation[
                "baseline_id"
            ],
            "status": (
                "READY_FOR_PROVIDER_AUDIT"
            ),
            "created_at": package_created_at,
            "collection_status": (
                collection["status"]
            ),
            "validation_status": (
                validation["status"]
            ),
            "validation_warnings": (
                validation["summary"][
                    "warnings"
                ]
            ),
            "blocking_failures": (
                validation["summary"][
                    "blocking_failures"
                ]
            ),
            "provider": "NONE",
            "provider_executed": False,
            "automatic_remediation": False,
            "baseline_immutable": True,
            "allocation_policy": {
                "model": (
                    "DYNAMIC_POLICY_DRIVEN"
                ),
                "policy_frozen": True,
                "weights_permanently_fixed": (
                    False
                ),
            },
        }

        atomic_write_json(
            self.package_dir
            / "AUDIT_PACKAGE_READY.json",
            readiness_payload,
        )

        package_files = self._enumerate_files()

        readiness_sha256 = (
            self._calculate_readiness_hash(
                package_files
            )
        )

        checksum_lines: list[str] = []

        manifest_files: list[
            PackageFile
        ] = []

        for path in package_files:
            relative = str(
                path.relative_to(
                    self.package_dir
                )
            )

            checksum = sha256_file(path)

            role, required, description = (
                self._infer_role(relative)
            )

            checksum_lines.append(
                f"{checksum}  {relative}"
            )

            manifest_files.append(
                PackageFile(
                    path=relative,
                    role=role,
                    sha256=checksum,
                    size_bytes=(
                        path.stat().st_size
                    ),
                    required_for_audit=required,
                    description=description,
                )
            )

        atomic_write_text(
            self.package_dir
            / "PACKAGE_CHECKSUMS.sha256",
            "\n".join(
                checksum_lines
            )
            + "\n",
        )

        manifest = AuditPackageManifest(
            audit_id=validation[
                "audit_id"
            ],
            release=validation[
                "release"
            ],
            baseline_id=validation[
                "baseline_id"
            ],
            package_status=(
                "READY_FOR_PROVIDER_AUDIT"
            ),
            created_at=package_created_at,
            package_root=str(
                self.package_dir
            ),
            provider="NONE",
            audit_mode=(
                "READ_ONLY_RECOMMENDATION_ONLY"
            ),
            baseline_aggregate_sha256=(
                validation["summary"][
                    "aggregate_sha256"
                ]
            ),
            collection_aggregate_sha256=(
                collection["summary"][
                    "aggregate_sha256"
                ]
            ),
            package_readiness_sha256=(
                readiness_sha256
            ),
            files=manifest_files,
            objectives=request.get(
                "objectives",
                [],
            ),
            constraints=request.get(
                "constraints",
                [],
            ),
            deliverables=[
                "Executive audit report",
                "Engineering scorecard",
                "Findings register",
                "Recommendation register",
                "RC2 impact analysis",
                "Remediation roadmap",
                "Machine-readable audit report",
            ],
            recommendation_categories=[
                "RC1_HOTFIX",
                "RC1_HARDENING",
                "RC2_PREREQUISITE",
                "RC2_ENHANCEMENT",
                "PRODUCTION_READINESS",
                "LONG_TERM_ARCHITECTURE",
                "DOCUMENTATION",
                "TESTING_AND_CERTIFICATION",
            ],
            metadata={
                "provider_executed": False,
                "automatic_remediation": False,
                "baseline_immutable": True,
                "artifact_count": inventory.get(
                    "artifact_count"
                ),
                "validation_checks": (
                    validation["summary"][
                        "total_checks"
                    ]
                ),
                "validation_warnings": (
                    validation["summary"][
                        "warnings"
                    ]
                ),
                "blocking_failures": (
                    validation["summary"][
                        "blocking_failures"
                    ]
                ),
                "allocation_model": (
                    "DYNAMIC_POLICY_DRIVEN"
                ),
                "policy_frozen": True,
                "weights_permanently_fixed": (
                    False
                ),
                "checksum_exclusions": sorted(
                    self.EXCLUDED_FROM_READINESS_HASH
                ),
            },
        )

        atomic_write_json(
            self.package_dir
            / "AUDIT_PACKAGE_MANIFEST.json",
            manifest.to_dict(),
        )

        return manifest
