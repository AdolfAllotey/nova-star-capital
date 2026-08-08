from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import os
import re
import tempfile

from src.v2.audit_framework.core.utils import (
    utc_now_iso,
)
from src.v2.audit_framework.evidence.contracts import (
    EvidenceArtifact,
    EvidencePersistenceResult,
    EvidenceRecord,
)


class ImmutableAuditEvidenceRepository:
    """
    Immutable storage for provider execution evidence.

    The repository:
    - never modifies source code;
    - never applies recommendations;
    - never overwrites existing evidence;
    - verifies all evidence through SHA-256;
    - supports idempotent replay of identical evidence.
    """

    SCHEMA_VERSION = "1.0"
    REPOSITORY_VERSION = "1.0.0"

    SAFE_IDENTIFIER = re.compile(
        r"^[A-Za-z0-9._-]+$"
    )

    def __init__(
        self,
        *,
        root_dir: Path,
    ) -> None:
        self.root_dir = root_dir.resolve()

    @staticmethod
    def _canonical_json_bytes(
        payload: Any,
    ) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @staticmethod
    def _sha256_bytes(
        content: bytes,
    ) -> str:
        return hashlib.sha256(
            content
        ).hexdigest()

    @classmethod
    def _sha256_payload(
        cls,
        payload: Any,
    ) -> str:
        return cls._sha256_bytes(
            cls._canonical_json_bytes(
                payload
            )
        )

    @classmethod
    def _validate_identifier(
        cls,
        value: str,
        field_name: str,
    ) -> None:
        if not value:
            raise ValueError(
                f"{field_name} is required."
            )

        if not cls.SAFE_IDENTIFIER.fullmatch(
            value
        ):
            raise ValueError(
                f"Unsafe {field_name}: {value}"
            )

    @staticmethod
    def _validate_sha256(
        value: str,
        field_name: str,
    ) -> None:
        if (
            len(value) != 64
            or any(
                char not in "0123456789abcdef"
                for char in value
            )
        ):
            raise ValueError(
                f"Invalid {field_name}."
            )

    @staticmethod
    def _atomic_write_bytes(
        path: Path,
        content: bytes,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        descriptor, temp_name = (
            tempfile.mkstemp(
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp",
            )
        )

        temp_path = Path(temp_name)

        try:
            with os.fdopen(
                descriptor,
                "wb",
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temp_path,
                path,
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @classmethod
    def _atomic_write_json(
        cls,
        path: Path,
        payload: Any,
    ) -> None:
        cls._atomic_write_bytes(
            path,
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            + b"\n",
        )

    @staticmethod
    def _make_read_only(
        path: Path,
    ) -> None:
        path.chmod(0o440)

    @classmethod
    def _build_evidence_id(
        cls,
        *,
        provider_id: str,
        audit_id: str,
        invocation_id: str,
        response_sha256: str,
    ) -> str:
        identity = {
            "provider_id": provider_id,
            "audit_id": audit_id,
            "invocation_id": invocation_id,
            "response_sha256": response_sha256,
        }

        identity_sha = cls._sha256_payload(
            identity
        )

        return (
            "EVIDENCE-"
            + identity_sha[:24].upper()
        )

    @classmethod
    def _artifact_from_bytes(
        cls,
        *,
        relative_path: str,
        role: str,
        content: bytes,
        media_type: str,
    ) -> EvidenceArtifact:
        return EvidenceArtifact(
            path=relative_path,
            role=role,
            sha256=cls._sha256_bytes(
                content
            ),
            size_bytes=len(content),
            media_type=media_type,
            immutable=True,
        )

    @classmethod
    def _aggregate_sha256(
        cls,
        artifacts: list[
            EvidenceArtifact
        ],
    ) -> str:
        canonical = [
            {
                "path": item.path,
                "role": item.role,
                "sha256": item.sha256,
                "size_bytes": (
                    item.size_bytes
                ),
                "media_type": (
                    item.media_type
                ),
                "immutable": (
                    item.immutable
                ),
            }
            for item in sorted(
                artifacts,
                key=lambda entry: entry.path,
            )
        ]

        return cls._sha256_payload(
            canonical
        )

    def persist(
        self,
        *,
        provider_id: str,
        audit_id: str,
        gate_id: str,
        invocation_id: str,
        package_readiness_sha256: str,
        payload_sha256: str,
        request_sha256: str,
        response_sha256: str,
        provider_response_id: str | None,
        model: str,
        transport_mode: str,
        provider_executed: bool,
        network_invocation_performed: bool,
        raw_request: dict[str, Any],
        raw_response: dict[str, Any],
        output_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> EvidencePersistenceResult:
        for value, field_name in (
            (provider_id, "provider_id"),
            (audit_id, "audit_id"),
            (gate_id, "gate_id"),
            (invocation_id, "invocation_id"),
        ):
            self._validate_identifier(
                value,
                field_name,
            )

        for value, field_name in (
            (
                package_readiness_sha256,
                "package_readiness_sha256",
            ),
            (
                payload_sha256,
                "payload_sha256",
            ),
            (
                request_sha256,
                "request_sha256",
            ),
            (
                response_sha256,
                "response_sha256",
            ),
        ):
            self._validate_sha256(
                value,
                field_name,
            )

        observed_request_sha = (
            self._sha256_payload(
                raw_request
            )
        )

        if (
            observed_request_sha
            != request_sha256
        ):
            raise ValueError(
                "Raw request SHA mismatch."
            )

        observed_response_sha = (
            self._sha256_payload(
                raw_response
            )
        )

        if (
            observed_response_sha
            != response_sha256
        ):
            raise ValueError(
                "Raw response SHA mismatch."
            )

        evidence_id = (
            self._build_evidence_id(
                provider_id=provider_id,
                audit_id=audit_id,
                invocation_id=(
                    invocation_id
                ),
                response_sha256=(
                    response_sha256
                ),
            )
        )

        evidence_dir = (
            self.root_dir
            / audit_id
            / provider_id.lower()
            / evidence_id
        )

        manifest_path = (
            evidence_dir
            / "evidence_manifest.json"
        )

        if evidence_dir.exists():
            if not manifest_path.is_file():
                raise RuntimeError(
                    "Existing evidence directory "
                    "has no manifest."
                )

            existing = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            if (
                existing.get(
                    "aggregate_sha256"
                )
                is None
            ):
                raise RuntimeError(
                    "Existing evidence manifest "
                    "is incomplete."
                )

            return EvidencePersistenceResult(
                schema_version=(
                    self.SCHEMA_VERSION
                ),
                evidence_id=evidence_id,
                evidence_dir=str(
                    evidence_dir
                ),
                status=(
                    "IMMUTABLE_EVIDENCE_REUSED"
                ),
                aggregate_sha256=(
                    existing[
                        "aggregate_sha256"
                    ]
                ),
                artifact_count=len(
                    existing.get(
                        "artifacts",
                        []
                    )
                ),
                immutable=True,
                created_at=existing[
                    "created_at"
                ],
                existing_record_reused=True,
                metadata={
                    "repository_version": (
                        self.REPOSITORY_VERSION
                    ),
                },
            )

        evidence_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        created_at = utc_now_iso()

        request_bytes = (
            self._canonical_json_bytes(
                raw_request
            )
        )

        response_bytes = (
            self._canonical_json_bytes(
                raw_response
            )
        )

        output_bytes = (
            output_text.encode("utf-8")
        )

        artifact_payloads = {
            "raw_request.json": (
                "PROVIDER_REQUEST",
                request_bytes,
                "application/json",
            ),
            "raw_response.json": (
                "PROVIDER_RESPONSE",
                response_bytes,
                "application/json",
            ),
            "provider_output.txt": (
                "PROVIDER_OUTPUT_TEXT",
                output_bytes,
                "text/plain",
            ),
        }

        artifacts: list[
            EvidenceArtifact
        ] = []

        for (
            relative_path,
            (
                role,
                content,
                media_type,
            ),
        ) in artifact_payloads.items():
            target = (
                evidence_dir
                / relative_path
            )

            self._atomic_write_bytes(
                target,
                content,
            )

            artifact = (
                self._artifact_from_bytes(
                    relative_path=(
                        relative_path
                    ),
                    role=role,
                    content=content,
                    media_type=media_type,
                )
            )

            artifacts.append(
                artifact
            )

        aggregate_sha256 = (
            self._aggregate_sha256(
                artifacts
            )
        )

        record = EvidenceRecord(
            schema_version=(
                self.SCHEMA_VERSION
            ),
            evidence_id=evidence_id,
            provider_id=provider_id,
            audit_id=audit_id,
            gate_id=gate_id,
            invocation_id=invocation_id,
            package_readiness_sha256=(
                package_readiness_sha256
            ),
            payload_sha256=(
                payload_sha256
            ),
            request_sha256=(
                request_sha256
            ),
            response_sha256=(
                response_sha256
            ),
            provider_response_id=(
                provider_response_id
            ),
            model=model,
            transport_mode=(
                transport_mode
            ),
            provider_executed=(
                provider_executed
            ),
            network_invocation_performed=(
                network_invocation_performed
            ),
            created_at=created_at,
            artifacts=artifacts,
            aggregate_sha256=(
                aggregate_sha256
            ),
            metadata={
                **(metadata or {}),
                "repository_version": (
                    self.REPOSITORY_VERSION
                ),
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
                "immutable": True,
            },
        )

        self._atomic_write_json(
            manifest_path,
            record.to_dict(),
        )

        checksum_lines = [
            (
                f"{artifact.sha256}  "
                f"{artifact.path}"
            )
            for artifact in sorted(
                artifacts,
                key=lambda entry: entry.path,
            )
        ]

        checksum_lines.append(
            (
                f"{aggregate_sha256}  "
                "AGGREGATE"
            )
        )

        checksum_path = (
            evidence_dir
            / "EVIDENCE_CHECKSUMS.sha256"
        )

        self._atomic_write_bytes(
            checksum_path,
            (
                "\n".join(
                    checksum_lines
                )
                + "\n"
            ).encode("utf-8"),
        )

        for path in evidence_dir.iterdir():
            if path.is_file():
                self._make_read_only(
                    path
                )

        evidence_dir.chmod(0o550)

        return EvidencePersistenceResult(
            schema_version=(
                self.SCHEMA_VERSION
            ),
            evidence_id=evidence_id,
            evidence_dir=str(
                evidence_dir
            ),
            status=(
                "IMMUTABLE_EVIDENCE_STORED"
            ),
            aggregate_sha256=(
                aggregate_sha256
            ),
            artifact_count=len(
                artifacts
            ),
            immutable=True,
            created_at=created_at,
            existing_record_reused=False,
            metadata={
                "repository_version": (
                    self.REPOSITORY_VERSION
                ),
            },
        )

    def verify(
        self,
        *,
        evidence_dir: Path,
    ) -> dict[str, Any]:
        evidence_dir = (
            evidence_dir.resolve()
        )

        manifest_path = (
            evidence_dir
            / "evidence_manifest.json"
        )

        if not manifest_path.is_file():
            raise RuntimeError(
                "Evidence manifest is missing."
            )

        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        findings: list[
            dict[str, Any]
        ] = []

        verified_artifacts: list[
            EvidenceArtifact
        ] = []

        for item in manifest.get(
            "artifacts",
            []
        ):
            artifact_path = (
                evidence_dir
                / item["path"]
            )

            if not artifact_path.is_file():
                findings.append(
                    {
                        "path": item["path"],
                        "status": "MISSING",
                    }
                )
                continue

            content = (
                artifact_path.read_bytes()
            )

            observed_sha = (
                self._sha256_bytes(
                    content
                )
            )

            status = (
                "PASS"
                if observed_sha
                == item["sha256"]
                else "HASH_MISMATCH"
            )

            findings.append(
                {
                    "path": item["path"],
                    "status": status,
                    "expected_sha256": (
                        item["sha256"]
                    ),
                    "observed_sha256": (
                        observed_sha
                    ),
                }
            )

            verified_artifacts.append(
                EvidenceArtifact(
                    path=item["path"],
                    role=item["role"],
                    sha256=observed_sha,
                    size_bytes=len(
                        content
                    ),
                    media_type=(
                        item["media_type"]
                    ),
                    immutable=True,
                )
            )

        observed_aggregate = (
            self._aggregate_sha256(
                verified_artifacts
            )
        )

        aggregate_match = (
            observed_aggregate
            == manifest.get(
                "aggregate_sha256"
            )
        )

        artifact_checks_pass = all(
            item["status"] == "PASS"
            for item in findings
        )

        status = (
            "VERIFIED"
            if (
                artifact_checks_pass
                and aggregate_match
                and len(
                    verified_artifacts
                )
                == len(
                    manifest.get(
                        "artifacts",
                        []
                    )
                )
            )
            else "FAILED"
        )

        return {
            "schema_version": (
                self.SCHEMA_VERSION
            ),
            "evidence_id": (
                manifest.get(
                    "evidence_id"
                )
            ),
            "status": status,
            "aggregate_match": (
                aggregate_match
            ),
            "expected_aggregate_sha256": (
                manifest.get(
                    "aggregate_sha256"
                )
            ),
            "observed_aggregate_sha256": (
                observed_aggregate
            ),
            "artifact_count": len(
                findings
            ),
            "findings": findings,
            "verified_at": utc_now_iso(),
        }
