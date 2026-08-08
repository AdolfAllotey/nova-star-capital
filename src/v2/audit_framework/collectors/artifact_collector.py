from __future__ import annotations

from pathlib import Path
from typing import Iterable
import glob
import hashlib
import shutil

from src.v2.audit_framework.collectors.artifact_definitions import (
    ArtifactDefinition,
)
from src.v2.audit_framework.collectors.collection_models import (
    CollectionIssue,
    CollectionResult,
)
from src.v2.audit_framework.core.constants import (
    APP_DIR,
    DATA_DIR,
)
from src.v2.audit_framework.core.exceptions import (
    ArtifactCollectionError,
)
from src.v2.audit_framework.core.models import (
    AuditArtifact,
    AuditRequest,
)
from src.v2.audit_framework.core.utils import (
    sha256_file,
    utc_now_iso,
)


class InstitutionalArtifactCollector:
    """
    Provider-independent, read-only artifact collector.

    Source files are never edited, moved or deleted. Every copied
    artifact is hashed before and after the copy.
    """

    FORBIDDEN_DESTINATION_ROOTS = (
        DATA_DIR / "releases",
        DATA_DIR / "governance",
        APP_DIR / "src",
        APP_DIR / "docs",
    )

    def __init__(
        self,
        definitions: Iterable[
            ArtifactDefinition
        ],
    ) -> None:
        self.definitions = tuple(
            definitions
        )

    @staticmethod
    def _is_relative_to(
        path: Path,
        parent: Path,
    ) -> bool:
        try:
            path.resolve().relative_to(
                parent.resolve()
            )
            return True
        except ValueError:
            return False

    def _validate_destination(
        self,
        package_dir: Path,
    ) -> None:
        resolved = package_dir.resolve()

        for forbidden_root in (
            self.FORBIDDEN_DESTINATION_ROOTS
        ):
            if self._is_relative_to(
                resolved,
                forbidden_root,
            ):
                raise ArtifactCollectionError(
                    "Audit package destination "
                    "cannot be located inside a "
                    "certified source or code "
                    f"directory: {resolved}"
                )

    @staticmethod
    def _discover_exact(
        definition: ArtifactDefinition,
    ) -> list[Path]:
        return [
            path.resolve()
            for path in definition.exact_paths
            if path.is_file()
        ]

    @staticmethod
    def _discover_glob(
        definition: ArtifactDefinition,
    ) -> list[Path]:
        discovered: list[Path] = []

        for pattern in (
            definition.glob_patterns
        ):
            for raw_path in glob.glob(
                pattern,
                recursive=True,
            ):
                path = Path(raw_path)

                if path.is_file():
                    discovered.append(
                        path.resolve()
                    )

        return discovered

    def _discover(
        self,
        definition: ArtifactDefinition,
    ) -> list[Path]:
        candidates = (
            self._discover_exact(
                definition
            )
            + self._discover_glob(
                definition
            )
        )

        unique: dict[str, Path] = {}

        for path in candidates:
            unique[str(path)] = path

        paths = sorted(
            unique.values(),
            key=lambda item: str(item),
        )

        if (
            not definition.allow_multiple
            and paths
        ):
            return [paths[0]]

        return paths

    @staticmethod
    def _build_destination(
        package_dir: Path,
        definition: ArtifactDefinition,
        source: Path,
        index: int,
        total: int,
    ) -> Path:
        base = (
            package_dir
            / "artifacts"
            / definition.destination_name
        )

        if definition.allow_multiple:
            base.mkdir(
                parents=True,
                exist_ok=True,
            )

            candidate = (
                base
                / source.name
            )

            if candidate.exists():
                candidate = (
                    base
                    / f"{index:03d}_{source.name}"
                )

            return candidate

        if (
            total == 1
            and Path(
                definition.destination_name
            ).suffix
        ):
            return base

        base.mkdir(
            parents=True,
            exist_ok=True,
        )

        return base / source.name

    @staticmethod
    def _copy_verified(
        source: Path,
        destination: Path,
    ) -> tuple[str, int]:
        source_hash_before = sha256_file(
            source
        )

        source_stat_before = source.stat()

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        destination_hash = sha256_file(
            destination
        )

        source_hash_after = sha256_file(
            source
        )

        source_stat_after = source.stat()

        if (
            source_hash_before
            != destination_hash
        ):
            destination.unlink(
                missing_ok=True
            )
            raise ArtifactCollectionError(
                "Checksum mismatch after copy: "
                f"{source}"
            )

        if (
            source_hash_before
            != source_hash_after
        ):
            raise ArtifactCollectionError(
                "Source artifact changed during "
                f"collection: {source}"
            )

        if (
            source_stat_before.st_size
            != source_stat_after.st_size
            or source_stat_before.st_mtime_ns
            != source_stat_after.st_mtime_ns
        ):
            raise ArtifactCollectionError(
                "Source metadata changed during "
                f"collection: {source}"
            )

        return (
            destination_hash,
            destination.stat().st_size,
        )

    @staticmethod
    def _aggregate_hash(
        artifacts: list[AuditArtifact],
    ) -> str:
        digest = hashlib.sha256()

        for artifact in sorted(
            artifacts,
            key=lambda item: (
                item.artifact_id,
                item.package_path,
            ),
        ):
            digest.update(
                artifact.artifact_id.encode(
                    "utf-8"
                )
            )
            digest.update(b"\0")
            digest.update(
                artifact.role.value.encode(
                    "utf-8"
                )
            )
            digest.update(b"\0")
            digest.update(
                artifact.package_path.encode(
                    "utf-8"
                )
            )
            digest.update(b"\0")
            digest.update(
                artifact.sha256.encode(
                    "ascii"
                )
            )
            digest.update(b"\n")

        return digest.hexdigest()

    def collect(
        self,
        request: AuditRequest,
        package_dir: Path,
    ) -> CollectionResult:
        started_at = utc_now_iso()

        self._validate_destination(
            package_dir
        )

        package_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        artifacts: list[AuditArtifact] = []
        issues: list[CollectionIssue] = []

        required_expected = sum(
            1
            for definition in self.definitions
            if definition.required
        )

        required_collected_ids: set[str] = (
            set()
        )

        optional_collected = 0

        for definition in self.definitions:
            discovered = self._discover(
                definition
            )

            if not discovered:
                issue = CollectionIssue(
                    issue_type=(
                        "MISSING_REQUIRED_ARTIFACT"
                        if definition.required
                        else "OPTIONAL_ARTIFACT_NOT_FOUND"
                    ),
                    artifact_id=(
                        definition.artifact_id
                    ),
                    message=(
                        "No source file found for "
                        f"{definition.artifact_id}"
                    ),
                    blocking=definition.required,
                )

                issues.append(issue)
                continue

            for index, source in enumerate(
                discovered,
                start=1,
            ):
                destination = (
                    self._build_destination(
                        package_dir=package_dir,
                        definition=definition,
                        source=source,
                        index=index,
                        total=len(discovered),
                    )
                )

                checksum, size_bytes = (
                    self._copy_verified(
                        source,
                        destination,
                    )
                )

                artifact_id = (
                    definition.artifact_id
                    if len(discovered) == 1
                    else (
                        f"{definition.artifact_id}"
                        f"_{index:03d}"
                    )
                )

                artifact = AuditArtifact(
                    artifact_id=artifact_id,
                    role=definition.role,
                    source_path=str(source),
                    package_path=str(
                        destination.relative_to(
                            package_dir
                        )
                    ),
                    sha256=checksum,
                    size_bytes=size_bytes,
                    required=(
                        definition.required
                    ),
                    metadata={
                        "definition_id": (
                            definition.artifact_id
                        ),
                        "description": (
                            definition.description
                        ),
                        "source_name": (
                            source.name
                        ),
                    },
                )

                artifacts.append(artifact)

                if definition.required:
                    required_collected_ids.add(
                        definition.artifact_id
                    )
                else:
                    optional_collected += 1

        required_collected = len(
            required_collected_ids
        )

        blocking_issues = [
            issue
            for issue in issues
            if issue.blocking
        ]

        status = (
            "PASS"
            if not blocking_issues
            else "FAILED"
        )

        aggregate_sha256 = (
            self._aggregate_hash(
                artifacts
            )
        )

        result = CollectionResult(
            audit_id=request.audit_id,
            package_dir=str(
                package_dir.resolve()
            ),
            started_at=started_at,
            completed_at=utc_now_iso(),
            status=status,
            artifacts=[
                artifact.to_dict()
                for artifact in artifacts
            ],
            issues=issues,
            required_expected=(
                required_expected
            ),
            required_collected=(
                required_collected
            ),
            optional_collected=(
                optional_collected
            ),
            total_collected=len(
                artifacts
            ),
            aggregate_sha256=(
                aggregate_sha256
            ),
            source_mutation_detected=False,
            metadata={
                "provider_executed": False,
                "source_mode": "READ_ONLY",
                "copy_verification": (
                    "SHA256_AND_METADATA"
                ),
            },
        )

        if blocking_issues:
            missing = ", ".join(
                issue.artifact_id
                for issue in blocking_issues
            )

            raise ArtifactCollectionError(
                "Required artifact collection "
                f"failed: {missing}"
            )

        return result
