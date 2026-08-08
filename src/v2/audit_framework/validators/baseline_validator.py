from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from src.v2.audit_framework.core.exceptions import (
    BaselineValidationError,
)
from src.v2.audit_framework.core.utils import (
    read_json,
    sha256_file,
    utc_now_iso,
)
from src.v2.audit_framework.validators.extraction import (
    coerce_bool,
    contains_token,
    find_all_values,
    find_first_value,
    normalize_scalar,
    normalize_upper,
)
from src.v2.audit_framework.validators.validation_models import (
    BaselineValidationResult,
    ValidationCheck,
)


class RC1BaselineValidator:
    EXPECTED_RELEASE = "RC1"

    EXPECTED_BASELINE_STATUS = "FROZEN"

    EXPECTED_DECISION = "APPROVED"

    EXPECTED_ALLOCATION_MODEL = (
        "DYNAMIC_POLICY_DRIVEN"
    )

    def __init__(
        self,
        package_dir: Path,
    ) -> None:
        self.package_dir = (
            package_dir.resolve()
        )

        self.artifacts_dir = (
            self.package_dir
            / "artifacts"
        )

        self.report_path = (
            self.package_dir
            / "artifact_collection_report.json"
        )

        self.inventory_path = (
            self.package_dir
            / "artifact_inventory.json"
        )

        self.request_path = (
            self.package_dir
            / "audit_request.json"
        )

        self.checks: list[
            ValidationCheck
        ] = []

    def _add_check(
        self,
        *,
        check_id: str,
        domain: str,
        status: str,
        message: str,
        blocking: bool,
        expected: Any = None,
        observed: Any = None,
        evidence: list[str] | None = None,
    ) -> None:
        self.checks.append(
            ValidationCheck(
                check_id=check_id,
                domain=domain,
                status=status,
                message=message,
                blocking=blocking,
                expected=expected,
                observed=observed,
                evidence=evidence or [],
            )
        )

    def _pass(
        self,
        *,
        check_id: str,
        domain: str,
        message: str,
        expected: Any = None,
        observed: Any = None,
        evidence: list[str] | None = None,
    ) -> None:
        self._add_check(
            check_id=check_id,
            domain=domain,
            status="PASS",
            message=message,
            blocking=False,
            expected=expected,
            observed=observed,
            evidence=evidence,
        )

    def _warn(
        self,
        *,
        check_id: str,
        domain: str,
        message: str,
        expected: Any = None,
        observed: Any = None,
        evidence: list[str] | None = None,
    ) -> None:
        self._add_check(
            check_id=check_id,
            domain=domain,
            status="WARNING",
            message=message,
            blocking=False,
            expected=expected,
            observed=observed,
            evidence=evidence,
        )

    def _fail(
        self,
        *,
        check_id: str,
        domain: str,
        message: str,
        expected: Any = None,
        observed: Any = None,
        evidence: list[str] | None = None,
    ) -> None:
        self._add_check(
            check_id=check_id,
            domain=domain,
            status="FAIL",
            message=message,
            blocking=True,
            expected=expected,
            observed=observed,
            evidence=evidence,
        )

    def _load_required_json(
        self,
        path: Path,
        label: str,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise BaselineValidationError(
                f"Missing required {label}: "
                f"{path}"
            )

        return read_json(path)

    def _find_artifact_by_definition(
        self,
        report: dict[str, Any],
        definition_id: str,
    ) -> list[Path]:
        matches: list[Path] = []

        for artifact in report.get(
            "artifacts",
            [],
        ):
            metadata = artifact.get(
                "metadata",
                {},
            )

            observed_definition = (
                metadata.get(
                    "definition_id"
                )
            )

            if (
                observed_definition
                == definition_id
            ):
                path = (
                    self.package_dir
                    / artifact[
                        "package_path"
                    ]
                )

                if path.is_file():
                    matches.append(path)

        return matches

    @staticmethod
    def _hash_inventory(
        report: dict[str, Any],
    ) -> str:
        digest = hashlib.sha256()

        artifacts = sorted(
            report.get(
                "artifacts",
                [],
            ),
            key=lambda item: (
                item.get(
                    "artifact_id",
                    "",
                ),
                item.get(
                    "package_path",
                    "",
                ),
            ),
        )

        for artifact in artifacts:
            digest.update(
                str(
                    artifact.get(
                        "artifact_id",
                        "",
                    )
                ).encode("utf-8")
            )
            digest.update(b"\0")
            digest.update(
                str(
                    artifact.get(
                        "role",
                        "",
                    )
                ).encode("utf-8")
            )
            digest.update(b"\0")
            digest.update(
                str(
                    artifact.get(
                        "package_path",
                        "",
                    )
                ).encode("utf-8")
            )
            digest.update(b"\0")
            digest.update(
                str(
                    artifact.get(
                        "sha256",
                        "",
                    )
                ).encode("ascii")
            )
            digest.update(b"\n")

        return digest.hexdigest()

    def _validate_package_files(
        self,
        report: dict[str, Any],
    ) -> str:
        all_valid = True

        for artifact in report.get(
            "artifacts",
            [],
        ):
            package_path = (
                self.package_dir
                / artifact[
                    "package_path"
                ]
            )

            if not package_path.is_file():
                all_valid = False

                self._fail(
                    check_id=(
                        "PACKAGE_ARTIFACT_PRESENT_"
                        + artifact[
                            "artifact_id"
                        ]
                    ),
                    domain="PACKAGE_INTEGRITY",
                    message=(
                        "Collected artifact is "
                        "missing from the package."
                    ),
                    expected="FILE_PRESENT",
                    observed="MISSING",
                    evidence=[
                        str(package_path)
                    ],
                )

                continue

            observed_hash = sha256_file(
                package_path
            )

            expected_hash = artifact.get(
                "sha256"
            )

            if (
                observed_hash
                != expected_hash
            ):
                all_valid = False

                self._fail(
                    check_id=(
                        "PACKAGE_ARTIFACT_HASH_"
                        + artifact[
                            "artifact_id"
                        ]
                    ),
                    domain="PACKAGE_INTEGRITY",
                    message=(
                        "Collected artifact SHA-256 "
                        "does not match inventory."
                    ),
                    expected=expected_hash,
                    observed=observed_hash,
                    evidence=[
                        str(package_path)
                    ],
                )

        calculated = self._hash_inventory(
            report
        )

        expected_aggregate = (
            report.get(
                "summary",
                {},
            ).get(
                "aggregate_sha256"
            )
        )

        if (
            calculated
            == expected_aggregate
        ):
            self._pass(
                check_id=(
                    "PACKAGE_AGGREGATE_SHA256"
                ),
                domain="PACKAGE_INTEGRITY",
                message=(
                    "Package aggregate SHA-256 "
                    "matches collection report."
                ),
                expected=expected_aggregate,
                observed=calculated,
                evidence=[
                    str(self.report_path)
                ],
            )
        else:
            all_valid = False

            self._fail(
                check_id=(
                    "PACKAGE_AGGREGATE_SHA256"
                ),
                domain="PACKAGE_INTEGRITY",
                message=(
                    "Package aggregate SHA-256 "
                    "does not match collection "
                    "report."
                ),
                expected=expected_aggregate,
                observed=calculated,
                evidence=[
                    str(self.report_path)
                ],
            )

        if all_valid:
            self._pass(
                check_id=(
                    "PACKAGE_ARTIFACT_HASHES"
                ),
                domain="PACKAGE_INTEGRITY",
                message=(
                    "All collected artifacts are "
                    "present and checksum-valid."
                ),
                expected="ALL_VALID",
                observed="ALL_VALID",
                evidence=[
                    str(self.inventory_path)
                ],
            )

        return calculated

    def _validate_identity(
        self,
        request: dict[str, Any],
        baseline: dict[str, Any],
        release_gate: dict[str, Any],
    ) -> str:
        request_target = request.get(
            "target",
            {},
        )

        requested_release = (
            request_target.get(
                "release"
            )
        )

        if (
            normalize_upper(
                requested_release
            )
            == self.EXPECTED_RELEASE
        ):
            self._pass(
                check_id="RELEASE_IDENTITY",
                domain="RELEASE",
                message=(
                    "Audit request targets RC1."
                ),
                expected=self.EXPECTED_RELEASE,
                observed=requested_release,
                evidence=[
                    str(self.request_path)
                ],
            )
        else:
            self._fail(
                check_id="RELEASE_IDENTITY",
                domain="RELEASE",
                message=(
                    "Audit request does not "
                    "target RC1."
                ),
                expected=self.EXPECTED_RELEASE,
                observed=requested_release,
                evidence=[
                    str(self.request_path)
                ],
            )

        request_baseline_id = (
            request_target.get(
                "baseline_id"
            )
        )

        baseline_id, baseline_path = (
            find_first_value(
                baseline,
                (
                    "baseline_id",
                    "release_baseline_id",
                    "id",
                ),
            )
        )

        gate_baseline_id, gate_path = (
            find_first_value(
                release_gate,
                (
                    "baseline_id",
                    "release_baseline_id",
                ),
            )
        )

        observed_ids = {
            normalize_scalar(value)
            for value in (
                request_baseline_id,
                baseline_id,
                gate_baseline_id,
            )
            if normalize_scalar(value)
        }

        if len(observed_ids) == 1:
            final_baseline_id = (
                next(iter(observed_ids))
            )

            self._pass(
                check_id=(
                    "BASELINE_ID_CONSISTENCY"
                ),
                domain="BASELINE",
                message=(
                    "Baseline identifier is "
                    "consistent across request, "
                    "pointer and release gate."
                ),
                expected=final_baseline_id,
                observed=sorted(
                    observed_ids
                ),
                evidence=[
                    str(self.request_path),
                    (
                        f"baseline:{baseline_path}"
                        if baseline_path
                        else "baseline:missing"
                    ),
                    (
                        f"release_gate:{gate_path}"
                        if gate_path
                        else "release_gate:missing"
                    ),
                ],
            )

            return final_baseline_id

        self._fail(
            check_id=(
                "BASELINE_ID_CONSISTENCY"
            ),
            domain="BASELINE",
            message=(
                "Baseline identifier is missing "
                "or inconsistent."
            ),
            expected="ONE_CONSISTENT_ID",
            observed=sorted(
                observed_ids
            ),
            evidence=[
                str(self.request_path),
                str(baseline_path),
                str(gate_path),
            ],
        )

        return (
            normalize_scalar(
                request_baseline_id
            )
            or normalize_scalar(
                baseline_id
            )
            or "UNKNOWN"
        )

    def _validate_state(
        self,
        baseline: dict[str, Any],
        release_gate: dict[str, Any],
    ) -> None:
        baseline_status, status_path = (
            find_first_value(
                baseline,
                (
                    "baseline_status",
                    "status",
                    "state",
                ),
            )
        )

        if (
            normalize_upper(
                baseline_status
            )
            == self.EXPECTED_BASELINE_STATUS
        ):
            self._pass(
                check_id="BASELINE_FROZEN",
                domain="BASELINE",
                message=(
                    "RC1 baseline is frozen."
                ),
                expected=(
                    self.EXPECTED_BASELINE_STATUS
                ),
                observed=baseline_status,
                evidence=[
                    str(status_path)
                ],
            )
        else:
            frozen_value, frozen_path = (
                find_first_value(
                    baseline,
                    (
                        "frozen",
                        "baseline_frozen",
                    ),
                )
            )

            if (
                coerce_bool(
                    frozen_value
                )
                is True
            ):
                self._pass(
                    check_id="BASELINE_FROZEN",
                    domain="BASELINE",
                    message=(
                        "RC1 baseline is frozen "
                        "according to its boolean "
                        "freeze flag."
                    ),
                    expected=True,
                    observed=frozen_value,
                    evidence=[
                        str(frozen_path)
                    ],
                )
            else:
                self._fail(
                    check_id="BASELINE_FROZEN",
                    domain="BASELINE",
                    message=(
                        "RC1 baseline is not "
                        "confirmed as frozen."
                    ),
                    expected=(
                        self.EXPECTED_BASELINE_STATUS
                    ),
                    observed=baseline_status,
                    evidence=[
                        str(status_path),
                        str(frozen_path),
                    ],
                )

        decision, decision_path = (
            find_first_value(
                release_gate,
                (
                    "decision",
                    "release_decision",
                    "gate_decision",
                    "approval_status",
                ),
            )
        )

        if (
            normalize_upper(decision)
            == self.EXPECTED_DECISION
        ):
            self._pass(
                check_id=(
                    "RELEASE_DECISION_APPROVED"
                ),
                domain="RELEASE",
                message=(
                    "RC1 release decision is "
                    "APPROVED."
                ),
                expected=self.EXPECTED_DECISION,
                observed=decision,
                evidence=[
                    str(decision_path)
                ],
            )
        else:
            approved_value, approved_path = (
                find_first_value(
                    release_gate,
                    (
                        "approved",
                        "is_approved",
                    ),
                )
            )

            if (
                coerce_bool(
                    approved_value
                )
                is True
            ):
                self._pass(
                    check_id=(
                        "RELEASE_DECISION_APPROVED"
                    ),
                    domain="RELEASE",
                    message=(
                        "RC1 release is approved "
                        "according to its boolean "
                        "approval flag."
                    ),
                    expected=True,
                    observed=approved_value,
                    evidence=[
                        str(approved_path)
                    ],
                )
            else:
                self._fail(
                    check_id=(
                        "RELEASE_DECISION_APPROVED"
                    ),
                    domain="RELEASE",
                    message=(
                        "RC1 release decision is "
                        "not confirmed as APPROVED."
                    ),
                    expected=(
                        self.EXPECTED_DECISION
                    ),
                    observed=decision,
                    evidence=[
                        str(decision_path),
                        str(approved_path),
                    ],
                )

    def _validate_allocation_policy(
        self,
        baseline: dict[str, Any],
        release_gate: dict[str, Any],
    ) -> None:
        combined = {
            "baseline": baseline,
            "release_gate": release_gate,
        }

        allocation_model, model_path = (
            find_first_value(
                combined,
                (
                    "allocation_model",
                    "allocation_mode",
                    "portfolio_allocation_model",
                ),
            )
        )

        model_evidence = (
            contains_token(
                combined,
                self.EXPECTED_ALLOCATION_MODEL,
            )
        )

        if (
            normalize_upper(
                allocation_model
            )
            == self.EXPECTED_ALLOCATION_MODEL
            or model_evidence
        ):
            self._pass(
                check_id=(
                    "ALLOCATION_MODEL_DYNAMIC_POLICY_DRIVEN"
                ),
                domain="ALLOCATION_POLICY",
                message=(
                    "Allocation model is "
                    "DYNAMIC_POLICY_DRIVEN."
                ),
                expected=(
                    self.EXPECTED_ALLOCATION_MODEL
                ),
                observed=(
                    allocation_model
                    or self.EXPECTED_ALLOCATION_MODEL
                ),
                evidence=(
                    [str(model_path)]
                    if model_path
                    else model_evidence
                ),
            )
        else:
            self._fail(
                check_id=(
                    "ALLOCATION_MODEL_DYNAMIC_POLICY_DRIVEN"
                ),
                domain="ALLOCATION_POLICY",
                message=(
                    "Expected dynamic policy-driven "
                    "allocation model was not found."
                ),
                expected=(
                    self.EXPECTED_ALLOCATION_MODEL
                ),
                observed=allocation_model,
                evidence=[
                    str(model_path)
                ],
            )

        policy_frozen, policy_path = (
            find_first_value(
                combined,
                (
                    "policy_frozen",
                    "allocation_policy_frozen",
                    "governance_policy_frozen",
                ),
            )
        )

        if (
            coerce_bool(
                policy_frozen
            )
            is True
        ):
            self._pass(
                check_id=(
                    "ALLOCATION_POLICY_FROZEN"
                ),
                domain="ALLOCATION_POLICY",
                message=(
                    "Allocation policy is frozen."
                ),
                expected=True,
                observed=policy_frozen,
                evidence=[
                    str(policy_path)
                ],
            )
        else:
            self._fail(
                check_id=(
                    "ALLOCATION_POLICY_FROZEN"
                ),
                domain="ALLOCATION_POLICY",
                message=(
                    "Allocation policy freeze "
                    "could not be confirmed."
                ),
                expected=True,
                observed=policy_frozen,
                evidence=[
                    str(policy_path)
                ],
            )

        fixed_weights, weights_path = (
            find_first_value(
                combined,
                (
                    "weights_permanently_fixed",
                    "allocation_weights_frozen",
                    "weights_frozen",
                    "fixed_weights",
                ),
            )
        )

        interpreted = coerce_bool(
            fixed_weights
        )

        if interpreted is False:
            self._pass(
                check_id=(
                    "ALLOCATION_WEIGHTS_NOT_FROZEN"
                ),
                domain="ALLOCATION_POLICY",
                message=(
                    "Allocation weights remain "
                    "dynamic and are not "
                    "permanently frozen."
                ),
                expected=False,
                observed=fixed_weights,
                evidence=[
                    str(weights_path)
                ],
            )
        else:
            dynamic_weight_evidence = []

            for token in (
                "WEIGHTS_PERMANENTLY_FIXED_FALSE",
                "ALLOCATION_WEIGHTS_FROZEN_FALSE",
                "WEIGHTS_FROZEN_FALSE",
            ):
                dynamic_weight_evidence.extend(
                    contains_token(
                        combined,
                        token,
                    )
                )

            if dynamic_weight_evidence:
                self._pass(
                    check_id=(
                        "ALLOCATION_WEIGHTS_NOT_FROZEN"
                    ),
                    domain="ALLOCATION_POLICY",
                    message=(
                        "Allocation weights are "
                        "explicitly documented as "
                        "not frozen."
                    ),
                    expected=False,
                    observed=False,
                    evidence=(
                        dynamic_weight_evidence
                    ),
                )
            else:
                self._fail(
                    check_id=(
                        "ALLOCATION_WEIGHTS_NOT_FROZEN"
                    ),
                    domain="ALLOCATION_POLICY",
                    message=(
                        "Allocation weights are "
                        "missing or appear frozen."
                    ),
                    expected=False,
                    observed=fixed_weights,
                    evidence=[
                        str(weights_path)
                    ],
                )

    def _validate_aggregate_sha(
        self,
        request: dict[str, Any],
        baseline: dict[str, Any],
        release_gate: dict[str, Any],
    ) -> str | None:
        values: list[
            tuple[str, str]
        ] = []

        sources = (
            (
                "request",
                request.get(
                    "target",
                    {},
                ),
            ),
            (
                "baseline",
                baseline,
            ),
            (
                "release_gate",
                release_gate,
            ),
        )

        for source_name, payload in sources:
            found = find_all_values(
                payload,
                (
                    "aggregate_sha256",
                    "baseline_aggregate_sha256",
                    "release_aggregate_sha256",
                ),
            )

            for value, path in found:
                normalized = (
                    normalize_scalar(value)
                )

                if (
                    len(normalized) == 64
                    and all(
                        char
                        in "0123456789abcdefABCDEF"
                        for char in normalized
                    )
                ):
                    values.append(
                        (
                            normalized.lower(),
                            f"{source_name}:{path}",
                        )
                    )

        unique_hashes = {
            value
            for value, _ in values
        }

        if len(unique_hashes) == 1:
            aggregate = next(
                iter(unique_hashes)
            )

            self._pass(
                check_id=(
                    "RC1_AGGREGATE_SHA256_CONSISTENCY"
                ),
                domain="BASELINE",
                message=(
                    "RC1 aggregate SHA-256 is "
                    "consistent across available "
                    "baseline references."
                ),
                expected=aggregate,
                observed=aggregate,
                evidence=[
                    evidence
                    for _, evidence in values
                ],
            )

            return aggregate

        if not unique_hashes:
            self._warn(
                check_id=(
                    "RC1_AGGREGATE_SHA256_CONSISTENCY"
                ),
                domain="BASELINE",
                message=(
                    "No canonical RC1 aggregate "
                    "SHA-256 was found in the "
                    "available JSON fields."
                ),
                expected=(
                    "64-character SHA-256"
                ),
                observed=None,
                evidence=[],
            )

            return None

        self._fail(
            check_id=(
                "RC1_AGGREGATE_SHA256_CONSISTENCY"
            ),
            domain="BASELINE",
            message=(
                "Conflicting RC1 aggregate "
                "SHA-256 values were found."
            ),
            expected="ONE_CONSISTENT_HASH",
            observed=sorted(
                unique_hashes
            ),
            evidence=[
                evidence
                for _, evidence in values
            ],
        )

        return None

    def _validate_certifications(
        self,
        report: dict[str, Any],
    ) -> None:
        certification_paths = (
            self._find_artifact_by_definition(
                report,
                "rc1_certifications",
            )
        )

        if not certification_paths:
            self._warn(
                check_id=(
                    "RC1_CERTIFICATION_ARTIFACTS"
                ),
                domain="CERTIFICATION",
                message=(
                    "No certification artifacts "
                    "were collected."
                ),
                expected=(
                    "AT_LEAST_ONE_CERTIFICATION"
                ),
                observed=0,
                evidence=[],
            )

            return

        valid_certifications = 0
        evidence: list[str] = []

        for path in certification_paths:
            try:
                payload = read_json(path)
            except Exception:
                continue

            pass_tokens = []

            for token in (
                "PASS",
                "CERTIFIED",
                "APPROVED",
                "SIMULATED_ONLY",
                "38",
            ):
                found = contains_token(
                    payload,
                    token,
                )

                if found:
                    pass_tokens.append(
                        token
                    )

            failures, _ = find_first_value(
                payload,
                (
                    "failures",
                    "failure_count",
                    "failed_checks",
                ),
            )

            warnings, _ = find_first_value(
                payload,
                (
                    "warnings",
                    "warning_count",
                ),
            )

            status, _ = find_first_value(
                payload,
                (
                    "status",
                    "result",
                    "decision",
                    "certification_status",
                ),
            )

            status_ok = (
                normalize_upper(status)
                in {
                    "PASS",
                    "PASSED",
                    "CERTIFIED",
                    "APPROVED",
                    "SUCCESS",
                    "RC1_END_TO_END_CERTIFIED",
                }
            )

            failure_count_ok = (
                failures in (
                    None,
                    0,
                    "0",
                    [],
                )
            )

            warning_count_ok = (
                warnings in (
                    None,
                    0,
                    "0",
                    [],
                )
            )

            if (
                status_ok
                and failure_count_ok
                and warning_count_ok
            ):
                valid_certifications += 1
                evidence.append(
                    str(path)
                )
            elif (
                "CERTIFIED"
                in pass_tokens
                and failure_count_ok
                and warning_count_ok
            ):
                valid_certifications += 1
                evidence.append(
                    str(path)
                )

        if valid_certifications > 0:
            self._pass(
                check_id=(
                    "RC1_CERTIFICATION_ARTIFACTS"
                ),
                domain="CERTIFICATION",
                message=(
                    "At least one valid RC1 "
                    "certification artifact was "
                    "found."
                ),
                expected=(
                    "AT_LEAST_ONE_VALID"
                ),
                observed=(
                    valid_certifications
                ),
                evidence=evidence,
            )
        else:
            self._fail(
                check_id=(
                    "RC1_CERTIFICATION_ARTIFACTS"
                ),
                domain="CERTIFICATION",
                message=(
                    "Certification artifacts exist "
                    "but none could be validated as "
                    "successful."
                ),
                expected=(
                    "AT_LEAST_ONE_VALID"
                ),
                observed=0,
                evidence=[
                    str(path)
                    for path
                    in certification_paths
                ],
            )

    def _validate_master(
        self,
        report: dict[str, Any],
    ) -> None:
        status_paths = (
            self._find_artifact_by_definition(
                report,
                "nsc_master_status",
            )
        )

        document_paths = (
            self._find_artifact_by_definition(
                report,
                "nsc_master_document",
            )
        )

        if not status_paths:
            self._fail(
                check_id=(
                    "MASTER_STATUS_PRESENT"
                ),
                domain="MASTER",
                message=(
                    "Machine-readable Master "
                    "status is missing."
                ),
                expected="PRESENT",
                observed="MISSING",
            )
            return

        master_status = read_json(
            status_paths[0]
        )

        rc1_evidence = contains_token(
            master_status,
            "RC1",
        )

        certified_evidence = []

        for token in (
            "CERTIFIED_APPROVED_FROZEN",
            "APPROVED",
            "FROZEN",
            "CERTIFIED",
        ):
            certified_evidence.extend(
                contains_token(
                    master_status,
                    token,
                )
            )

        rc2_evidence = []

        for token in (
            "OPEN_FOR_SCOPING_AND_DEVELOPMENT",
            "RC2",
        ):
            rc2_evidence.extend(
                contains_token(
                    master_status,
                    token,
                )
            )

        if (
            rc1_evidence
            and certified_evidence
        ):
            self._pass(
                check_id=(
                    "MASTER_RC1_STATUS_CONSISTENCY"
                ),
                domain="MASTER",
                message=(
                    "Master status records RC1 as "
                    "certified, approved or frozen."
                ),
                expected=(
                    "RC1 CERTIFIED/APPROVED/FROZEN"
                ),
                observed="CONSISTENT",
                evidence=[
                    str(status_paths[0])
                ],
            )
        else:
            self._fail(
                check_id=(
                    "MASTER_RC1_STATUS_CONSISTENCY"
                ),
                domain="MASTER",
                message=(
                    "Master status is not "
                    "consistent with frozen and "
                    "approved RC1."
                ),
                expected=(
                    "RC1 CERTIFIED/APPROVED/FROZEN"
                ),
                observed="NOT_CONFIRMED",
                evidence=[
                    str(status_paths[0])
                ],
            )

        if rc2_evidence:
            self._pass(
                check_id=(
                    "MASTER_RC2_OPEN_STATUS"
                ),
                domain="MASTER",
                message=(
                    "Master status includes RC2 "
                    "as the active next release."
                ),
                expected=(
                    "RC2 OPEN FOR DEVELOPMENT"
                ),
                observed="CONFIRMED",
                evidence=[
                    str(status_paths[0])
                ],
            )
        else:
            self._warn(
                check_id=(
                    "MASTER_RC2_OPEN_STATUS"
                ),
                domain="MASTER",
                message=(
                    "RC2 open status was not "
                    "explicitly identified in the "
                    "machine-readable Master."
                ),
                expected=(
                    "RC2 OPEN FOR DEVELOPMENT"
                ),
                observed="NOT_FOUND",
                evidence=[
                    str(status_paths[0])
                ],
            )

        if document_paths:
            content = document_paths[
                0
            ].read_text(
                encoding="utf-8",
                errors="replace",
            ).upper()

            if (
                "RC1" in content
                and "RC2" in content
            ):
                self._pass(
                    check_id=(
                        "MASTER_DOCUMENT_RELEASE_REFERENCES"
                    ),
                    domain="MASTER",
                    message=(
                        "Human-readable Master "
                        "references both RC1 and RC2."
                    ),
                    expected="RC1_AND_RC2",
                    observed="RC1_AND_RC2",
                    evidence=[
                        str(
                            document_paths[0]
                        )
                    ],
                )
            else:
                self._warn(
                    check_id=(
                        "MASTER_DOCUMENT_RELEASE_REFERENCES"
                    ),
                    domain="MASTER",
                    message=(
                        "Human-readable Master does "
                        "not clearly reference both "
                        "RC1 and RC2."
                    ),
                    expected="RC1_AND_RC2",
                    observed="PARTIAL",
                    evidence=[
                        str(
                            document_paths[0]
                        )
                    ],
                )

    def validate(
        self,
    ) -> BaselineValidationResult:
        started_at = utc_now_iso()

        report = self._load_required_json(
            self.report_path,
            "artifact collection report",
        )

        request = self._load_required_json(
            self.request_path,
            "audit request",
        )

        inventory = self._load_required_json(
            self.inventory_path,
            "artifact inventory",
        )

        if (
            report.get("status")
            == "PASS"
        ):
            self._pass(
                check_id=(
                    "ARTIFACT_COLLECTION_STATUS"
                ),
                domain="COLLECTION",
                message=(
                    "Artifact collection completed "
                    "successfully."
                ),
                expected="PASS",
                observed=report.get(
                    "status"
                ),
                evidence=[
                    str(self.report_path)
                ],
            )
        else:
            self._fail(
                check_id=(
                    "ARTIFACT_COLLECTION_STATUS"
                ),
                domain="COLLECTION",
                message=(
                    "Artifact collection is not "
                    "in PASS status."
                ),
                expected="PASS",
                observed=report.get(
                    "status"
                ),
                evidence=[
                    str(self.report_path)
                ],
            )

        report_count = len(
            report.get(
                "artifacts",
                [],
            )
        )

        inventory_count = (
            inventory.get(
                "artifact_count"
            )
        )

        if report_count == inventory_count:
            self._pass(
                check_id=(
                    "ARTIFACT_COUNT_CONSISTENCY"
                ),
                domain="COLLECTION",
                message=(
                    "Artifact inventory count "
                    "matches collection report."
                ),
                expected=report_count,
                observed=inventory_count,
                evidence=[
                    str(self.report_path),
                    str(self.inventory_path),
                ],
            )
        else:
            self._fail(
                check_id=(
                    "ARTIFACT_COUNT_CONSISTENCY"
                ),
                domain="COLLECTION",
                message=(
                    "Artifact inventory count "
                    "does not match collection "
                    "report."
                ),
                expected=report_count,
                observed=inventory_count,
                evidence=[
                    str(self.report_path),
                    str(self.inventory_path),
                ],
            )

        package_integrity_sha256 = (
            self._validate_package_files(
                report
            )
        )

        baseline_paths = (
            self._find_artifact_by_definition(
                report,
                "rc1_current_baseline",
            )
        )

        gate_paths = (
            self._find_artifact_by_definition(
                report,
                "rc1_release_gate",
            )
        )

        if not baseline_paths:
            raise BaselineValidationError(
                "Collected baseline pointer "
                "not found."
            )

        if not gate_paths:
            raise BaselineValidationError(
                "Collected release gate "
                "not found."
            )

        baseline = read_json(
            baseline_paths[0]
        )

        release_gate = read_json(
            gate_paths[0]
        )

        baseline_id = self._validate_identity(
            request,
            baseline,
            release_gate,
        )

        self._validate_state(
            baseline,
            release_gate,
        )

        self._validate_allocation_policy(
            baseline,
            release_gate,
        )

        aggregate_sha256 = (
            self._validate_aggregate_sha(
                request,
                baseline,
                release_gate,
            )
        )

        self._validate_certifications(
            report
        )

        self._validate_master(
            report
        )

        blocking_failures = sum(
            1
            for check in self.checks
            if (
                check.status == "FAIL"
                and check.blocking
            )
        )

        warnings = sum(
            1
            for check in self.checks
            if check.status == "WARNING"
        )

        passed = sum(
            1
            for check in self.checks
            if check.status == "PASS"
        )

        status = (
            "PASS"
            if blocking_failures == 0
            else "FAILED"
        )

        result = BaselineValidationResult(
            audit_id=str(
                request.get(
                    "audit_id",
                    "UNKNOWN",
                )
            ),
            baseline_id=baseline_id,
            release=self.EXPECTED_RELEASE,
            started_at=started_at,
            completed_at=utc_now_iso(),
            status=status,
            checks=self.checks,
            blocking_failures=(
                blocking_failures
            ),
            warnings=warnings,
            passed=passed,
            aggregate_sha256=(
                aggregate_sha256
            ),
            package_integrity_sha256=(
                package_integrity_sha256
            ),
            metadata={
                "provider_executed": False,
                "automatic_remediation": False,
                "validation_scope": [
                    "PACKAGE_INTEGRITY",
                    "BASELINE_IDENTITY",
                    "RELEASE_STATE",
                    "ALLOCATION_POLICY",
                    "CERTIFICATION",
                    "MASTER_STATUS",
                ],
            },
        )

        if blocking_failures > 0:
            failed_ids = [
                check.check_id
                for check in self.checks
                if check.status == "FAIL"
            ]

            raise BaselineValidationError(
                "RC1 baseline validation "
                "failed: "
                + ", ".join(
                    failed_ids
                )
            )

        return result
