from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from src.v2.audit_framework.core.utils import (
    atomic_write_json,
    read_json,
    sha256_file,
    utc_now_iso,
)
from src.v2.audit_framework.providers.base import (
    ProviderAdapter,
)
from src.v2.audit_framework.providers.base.security import (
    validate_no_sensitive_files,
)
from src.v2.audit_framework.providers.contracts import (
    ProviderAuditPayload,
    ProviderCapabilities,
    ProviderExecutionPolicy,
    ProviderPreparationResult,
)


class CodexAuditAdapter(ProviderAdapter):
    PROVIDER_ID = "OPENAI_CODEX"

    ADAPTER_VERSION = "1.0.0"

    REQUIRED_PACKAGE_FILES = (
        "AUDIT_PACKAGE_MANIFEST.json",
        "AUDIT_PACKAGE_READY.json",
        "PACKAGE_CHECKSUMS.sha256",
        "PACKAGE_INDEX.md",
        "EXECUTIVE_AUDIT_BRIEF.md",
        "AUDIT_SCOPE.md",
        "PROVIDER_INSTRUCTIONS.md",
        "ENGINEERING_REVIEW_CHECKLIST.md",
        "EXPECTED_DELIVERABLES.md",
        "RECOMMENDATION_POLICY.md",
        "baseline_validation_report.json",
        "artifact_collection_report.json",
        "artifact_inventory.json",
        "audit_request.json",
    )

    @property
    def capabilities(
        self,
    ) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.PROVIDER_ID,
            display_name="OpenAI Codex",
            adapter_version=(
                self.ADAPTER_VERSION
            ),
            supports_read_only_audit=True,
            supports_structured_output=True,
            supports_file_evidence=True,
            supports_automatic_remediation=False,
            supports_live_execution=False,
            maximum_package_files=None,
            metadata={
                "integration_status": (
                    "PREPARATION_ONLY"
                ),
                "provider_execution_enabled": (
                    False
                ),
            },
        )

    @staticmethod
    def _load_package(
        package_dir: Path,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
    ]:
        manifest = read_json(
            package_dir
            / "AUDIT_PACKAGE_MANIFEST.json"
        )

        ready = read_json(
            package_dir
            / "AUDIT_PACKAGE_READY.json"
        )

        return manifest, ready

    @staticmethod
    def _check(
        *,
        check_id: str,
        domain: str,
        condition: bool,
        message_pass: str,
        message_fail: str,
        blocking: bool = True,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "domain": domain,
            "status": (
                "PASS"
                if condition
                else "FAIL"
            ),
            "blocking": blocking,
            "message": (
                message_pass
                if condition
                else message_fail
            ),
            "evidence": evidence or [],
        }

    @staticmethod
    def _calculate_manifest_hash(
        package_dir: Path,
        manifest: dict[str, Any],
    ) -> str:
        digest = hashlib.sha256()

        files = sorted(
            manifest["files"],
            key=lambda item: item["path"],
        )

        for item in files:
            path = (
                package_dir
                / item["path"]
            )

            if not path.is_file():
                raise RuntimeError(
                    "Missing package file: "
                    f"{item['path']}"
                )

            observed_sha256 = (
                sha256_file(path)
            )

            if (
                observed_sha256
                != item["sha256"]
            ):
                raise RuntimeError(
                    "Package checksum mismatch: "
                    f"{item['path']}"
                )

            digest.update(
                item["path"].encode(
                    "utf-8"
                )
            )
            digest.update(b"\0")
            digest.update(
                observed_sha256.encode(
                    "ascii"
                )
            )
            digest.update(b"\n")

        return digest.hexdigest()

    def validate_package(
        self,
        package_dir: Path,
    ) -> list[dict[str, Any]]:
        package_dir = package_dir.resolve()

        checks: list[
            dict[str, Any]
        ] = []

        missing_required = [
            filename
            for filename
            in self.REQUIRED_PACKAGE_FILES
            if not (
                package_dir
                / filename
            ).is_file()
        ]

        checks.append(
            self._check(
                check_id=(
                    "CODEX_REQUIRED_FILES"
                ),
                domain="PACKAGE",
                condition=(
                    not missing_required
                ),
                message_pass=(
                    "All required package "
                    "files are present."
                ),
                message_fail=(
                    "Required package files "
                    "are missing."
                ),
                evidence=missing_required,
            )
        )

        if missing_required:
            return checks

        manifest, ready = (
            self._load_package(
                package_dir
            )
        )

        checks.extend(
            [
                self._check(
                    check_id=(
                        "CODEX_RELEASE_RC1"
                    ),
                    domain="RELEASE",
                    condition=(
                        manifest.get(
                            "release"
                        )
                        == "RC1"
                    ),
                    message_pass=(
                        "Release is RC1."
                    ),
                    message_fail=(
                        "Release is not RC1."
                    ),
                ),
                self._check(
                    check_id=(
                        "CODEX_PACKAGE_READY"
                    ),
                    domain="PACKAGE",
                    condition=(
                        manifest.get(
                            "package_status"
                        )
                        == (
                            "READY_FOR_"
                            "PROVIDER_AUDIT"
                        )
                        and ready.get(
                            "status"
                        )
                        == (
                            "READY_FOR_"
                            "PROVIDER_AUDIT"
                        )
                    ),
                    message_pass=(
                        "Package readiness "
                        "gate is valid."
                    ),
                    message_fail=(
                        "Package is not ready "
                        "for provider audit."
                    ),
                ),
                self._check(
                    check_id=(
                        "CODEX_BASELINE_IMMUTABLE"
                    ),
                    domain="GOVERNANCE",
                    condition=(
                        ready.get(
                            "baseline_immutable"
                        )
                        is True
                    ),
                    message_pass=(
                        "Baseline is immutable."
                    ),
                    message_fail=(
                        "Baseline immutability "
                        "is not established."
                    ),
                ),
                self._check(
                    check_id=(
                        "CODEX_PROVIDER_NOT_EXECUTED"
                    ),
                    domain="EXECUTION",
                    condition=(
                        ready.get(
                            "provider_executed"
                        )
                        is False
                    ),
                    message_pass=(
                        "No provider has "
                        "executed."
                    ),
                    message_fail=(
                        "A provider execution "
                        "is already recorded."
                    ),
                ),
                self._check(
                    check_id=(
                        "CODEX_REMEDIATION_DISABLED"
                    ),
                    domain="SECURITY",
                    condition=(
                        ready.get(
                            "automatic_remediation"
                        )
                        is False
                    ),
                    message_pass=(
                        "Automatic remediation "
                        "is disabled."
                    ),
                    message_fail=(
                        "Automatic remediation "
                        "is enabled."
                    ),
                ),
                self._check(
                    check_id=(
                        "CODEX_DYNAMIC_ALLOCATION"
                    ),
                    domain="ARCHITECTURE",
                    condition=(
                        ready.get(
                            "allocation_policy",
                            {},
                        ).get(
                            "model"
                        )
                        == (
                            "DYNAMIC_POLICY_DRIVEN"
                        )
                        and ready.get(
                            "allocation_policy",
                            {},
                        ).get(
                            "policy_frozen"
                        )
                        is True
                        and ready.get(
                            "allocation_policy",
                            {},
                        ).get(
                            "weights_"
                            "permanently_fixed"
                        )
                        is False
                    ),
                    message_pass=(
                        "Frozen dynamic "
                        "allocation policy is "
                        "preserved."
                    ),
                    message_fail=(
                        "Allocation policy "
                        "contract is invalid."
                    ),
                ),
            ]
        )

        manifest_hash = (
            self._calculate_manifest_hash(
                package_dir,
                manifest,
            )
        )

        expected_hash = (
            manifest.get(
                "package_readiness_sha256"
            )
        )

        checks.append(
            self._check(
                check_id=(
                    "CODEX_PACKAGE_INTEGRITY"
                ),
                domain="INTEGRITY",
                condition=(
                    manifest_hash
                    == expected_hash
                ),
                message_pass=(
                    "Package readiness hash "
                    "is valid."
                ),
                message_fail=(
                    "Package readiness hash "
                    "does not match."
                ),
                evidence=[
                    (
                        "expected="
                        f"{expected_hash}"
                    ),
                    (
                        "observed="
                        f"{manifest_hash}"
                    ),
                ],
            )
        )

        relative_paths = [
            item["path"]
            for item
            in manifest.get(
                "files",
                [],
            )
        ]

        checks.extend(
            validate_no_sensitive_files(
                package_dir,
                relative_paths,
            )
        )

        return checks

    @staticmethod
    def _build_system_instructions() -> str:
        return "\n".join(
            [
                (
                    "You are acting as an "
                    "independent institutional "
                    "software engineering auditor."
                ),
                (
                    "The RC1 baseline is frozen "
                    "and immutable."
                ),
                (
                    "Perform a read-only review."
                ),
                (
                    "Do not modify any source, "
                    "configuration, artifact, "
                    "database or runtime state."
                ),
                (
                    "Do not execute trades, "
                    "orders, broker actions or "
                    "production operations."
                ),
                (
                    "Do not apply automatic "
                    "remediation."
                ),
                (
                    "Separate observations, "
                    "findings, recommendations "
                    "and implementation proposals."
                ),
                (
                    "Every material finding must "
                    "include precise evidence."
                ),
                (
                    "Preserve the approved "
                    "DYNAMIC_POLICY_DRIVEN "
                    "allocation model."
                ),
            ]
        )

    @staticmethod
    def _build_audit_instructions() -> str:
        return "\n".join(
            [
                (
                    "Review the complete RC1 "
                    "engineering audit package."
                ),
                "",
                (
                    "Assess architecture, code "
                    "quality, reliability, data "
                    "integrity, strategy isolation, "
                    "portfolio state management, "
                    "risk controls, execution "
                    "safety, security, persistence, "
                    "observability, testing, "
                    "dashboard integrity and "
                    "production readiness."
                ),
                "",
                (
                    "Identify RC1 defects "
                    "separately from RC2 "
                    "enhancements."
                ),
                "",
                (
                    "Classify each recommendation "
                    "using the supplied "
                    "recommendation policy."
                ),
                "",
                (
                    "Return both a human-readable "
                    "report and a machine-readable "
                    "JSON report."
                ),
            ]
        )

    def build_payload(
        self,
        package_dir: Path,
    ) -> ProviderAuditPayload:
        package_dir = package_dir.resolve()

        manifest, _ = (
            self._load_package(
                package_dir
            )
        )

        input_files = []

        for item in manifest["files"]:
            input_files.append(
                {
                    "path": item["path"],
                    "sha256": (
                        item["sha256"]
                    ),
                    "role": item["role"],
                    "required_for_audit": (
                        item[
                            "required_for_audit"
                        ]
                    ),
                    "access_mode": (
                        "READ_ONLY"
                    ),
                }
            )

        policy = ProviderExecutionPolicy(
            execution_mode="DRY_RUN",
            read_only=True,
            recommendation_only=True,
            automatic_remediation=False,
            allow_source_writes=False,
            allow_live_trading=False,
            allow_production_credentials=False,
            allow_network_side_effects=False,
            require_human_approval=True,
        )

        return ProviderAuditPayload(
            schema_version="1.0",
            provider_id=self.PROVIDER_ID,
            adapter_version=(
                self.ADAPTER_VERSION
            ),
            audit_id=manifest["audit_id"],
            release=manifest["release"],
            baseline_id=(
                manifest["baseline_id"]
            ),
            package_dir=str(
                package_dir
            ),
            package_manifest_path=str(
                package_dir
                / "AUDIT_PACKAGE_MANIFEST.json"
            ),
            package_readiness_sha256=(
                manifest[
                    "package_readiness_sha256"
                ]
            ),
            execution_policy=policy,
            system_instructions=(
                self._build_system_instructions()
            ),
            audit_instructions=(
                self._build_audit_instructions()
            ),
            input_files=input_files,
            expected_deliverables=(
                manifest[
                    "deliverables"
                ]
            ),
            output_contract={
                "human_readable_report": (
                    "CODEX_ENGINEERING_AUDIT.md"
                ),
                "machine_readable_report": (
                    "codex_engineering_audit.json"
                ),
                "findings_register": (
                    "codex_findings.json"
                ),
                "recommendations_register": (
                    "codex_recommendations.json"
                ),
                "execution_receipt": (
                    "codex_execution_receipt.json"
                ),
                "automatic_remediation": False,
            },
            metadata={
                "prepared_only": True,
                "provider_execution_enabled": (
                    False
                ),
                "baseline_immutable": True,
                "human_approval_required": True,
                "network_execution_permitted": (
                    False
                ),
            },
        )

    def prepare(
        self,
        package_dir: Path,
    ) -> ProviderPreparationResult:
        package_dir = package_dir.resolve()

        checks = self.validate_package(
            package_dir
        )

        blocking_failures = sum(
            1
            for check in checks
            if (
                check["status"]
                == "FAIL"
                and check["blocking"]
            )
        )

        warnings = sum(
            1
            for check in checks
            if check["status"]
            == "WARN"
        )

        if blocking_failures:
            raise RuntimeError(
                "Codex provider preparation "
                "blocked by package validation."
            )

        payload = self.build_payload(
            package_dir
        )

        payload_dir = (
            package_dir
            / "provider_payloads"
            / "openai_codex"
        )

        payload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload_path = (
            payload_dir
            / "codex_audit_payload.json"
        )

        atomic_write_json(
            payload_path,
            payload.to_dict(),
        )

        payload_sha256 = (
            sha256_file(payload_path)
        )

        result = ProviderPreparationResult(
            provider_id=self.PROVIDER_ID,
            audit_id=payload.audit_id,
            status="PREPARED_DRY_RUN",
            execution_mode="DRY_RUN",
            prepared_at=utc_now_iso(),
            payload_path=str(
                payload_path
            ),
            payload_sha256=(
                payload_sha256
            ),
            package_readiness_sha256=(
                payload.package_readiness_sha256
            ),
            checks=checks,
            blocking_failures=(
                blocking_failures
            ),
            warnings=warnings,
            provider_executed=False,
            automatic_remediation=False,
            metadata={
                "adapter_version": (
                    self.ADAPTER_VERSION
                ),
                "payload_file_count": len(
                    payload.input_files
                ),
                "human_approval_required": (
                    True
                ),
                "execution_available": False,
            },
        )

        result_path = (
            payload_dir
            / "codex_preparation_report.json"
        )

        atomic_write_json(
            result_path,
            result.to_dict(),
        )

        return result
