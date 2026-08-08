from __future__ import annotations

from pathlib import Path
from typing import Any

from src.v2.audit_framework.evidence import (
    ImmutableAuditEvidenceRepository,
)
from src.v2.audit_framework.integrations.codex.evidence_bridge import (
    CodexEvidenceCaptureBridge,
)
from src.v2.audit_framework.transports import (
    ProviderTransport,
    ProviderTransportRequest,
)

from .coordinator import (
    CodexInvocationCoordinator,
    atomic_write_json,
)


class EvidenceAwareCodexInvocationCoordinator(
    CodexInvocationCoordinator
):
    """
    Codex invocation coordinator requiring immutable evidence
    persistence and verification before gate consumption.

    Execution order:

    1. reserve the approved single-use gate;
    2. invoke the selected transport;
    3. capture immutable provider evidence;
    4. verify evidence integrity;
    5. bind evidence to the invocation;
    6. consume the gate.

    Any failure after reservation consumes the gate as a failed
    invocation, preventing an ambiguous replay.
    """

    COORDINATOR_VERSION = "1.1.0-EVIDENCE-AWARE"

    def __init__(
        self,
        *,
        package_dir: Path,
        gate_id: str,
        evidence_repository: (
            ImmutableAuditEvidenceRepository
        ),
    ) -> None:
        super().__init__(
            package_dir=package_dir,
            gate_id=gate_id,
        )

        self.evidence_repository = (
            evidence_repository
        )

        self.evidence_bridge = (
            CodexEvidenceCaptureBridge(
                repository=(
                    evidence_repository
                )
            )
        )

    def invoke(
        self,
        *,
        request: ProviderTransportRequest,
        transport: ProviderTransport,
    ):
        if (
            transport.provider_id
            != self.PROVIDER_ID
        ):
            raise RuntimeError(
                "Transport provider mismatch."
            )

        if (
            request.provider_id
            != self.PROVIDER_ID
        ):
            raise RuntimeError(
                "Request provider mismatch."
            )

        if request.gate_id != self.gate_id:
            raise RuntimeError(
                "Request gate mismatch."
            )

        if (
            request.network_invocation_authorized
            and transport.transport_mode
            == "SIMULATED_NO_NETWORK"
        ):
            raise RuntimeError(
                "Network authorization is invalid "
                "for simulated transport."
            )

        if (
            not request.network_invocation_authorized
            and transport.transport_mode
            != "SIMULATED_NO_NETWORK"
        ):
            raise RuntimeError(
                "Network transport is not authorized."
            )

        reservation = self.reserve(
            invocation_id=(
                request.invocation_id
            ),
            payload_sha256=(
                request.payload_sha256
            ),
            package_readiness_sha256=(
                request.package_readiness_sha256
            ),
            transport_mode=(
                transport.transport_mode
            ),
            network_invocation_authorized=(
                request
                .network_invocation_authorized
            ),
        )

        invocation_dir = (
            self.invocations_dir
            / reservation.invocation_id
        )

        try:
            result = transport.invoke(
                request
            )

            evidence = (
                self.evidence_bridge.capture(
                    request=request,
                    result=result,
                    metadata={
                        "reservation_id": (
                            reservation
                            .reservation_id
                        ),
                        "coordinator_version": (
                            self
                            .COORDINATOR_VERSION
                        ),
                        "single_use": True,
                        "read_only": True,
                        "recommendation_only": (
                            True
                        ),
                        "automatic_remediation": (
                            False
                        ),
                        "source_writes": False,
                        "live_trading": False,
                    },
                )
            )

            evidence_dir = Path(
                evidence.evidence_dir
            )

            verification = (
                self.evidence_repository.verify(
                    evidence_dir=evidence_dir
                )
            )

            if (
                verification.get("status")
                != "VERIFIED"
            ):
                raise RuntimeError(
                    "Audit evidence verification "
                    "failed."
                )

            binding = {
                "schema_version": "1.0",
                "invocation_id": (
                    reservation.invocation_id
                ),
                "reservation_id": (
                    reservation.reservation_id
                ),
                "gate_id": self.gate_id,
                "provider_id": (
                    self.PROVIDER_ID
                ),
                "audit_id": (
                    reservation.audit_id
                ),
                "evidence_id": (
                    evidence.evidence_id
                ),
                "evidence_dir": (
                    evidence.evidence_dir
                ),
                "evidence_status": (
                    evidence.status
                ),
                "evidence_aggregate_sha256": (
                    evidence
                    .aggregate_sha256
                ),
                "verification_status": (
                    verification["status"]
                ),
                "request_sha256": (
                    result.request_sha256
                ),
                "response_sha256": (
                    result.response_sha256
                ),
                "provider_executed": bool(
                    result.provider_executed
                ),
                "network_invocation_performed": (
                    bool(
                        result
                        .network_invocation_performed
                    )
                ),
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
                "metadata": {
                    "coordinator_version": (
                        self
                        .COORDINATOR_VERSION
                    ),
                    "evidence_required": True,
                    "evidence_verified": True,
                },
            }

            atomic_write_json(
                invocation_dir
                / "invocation_evidence_binding.json",
                binding,
            )

        except BaseException as exc:
            self._consume(
                reservation=reservation,
                transport_request=request,
                transport_result=None,
                error=exc,
            )

            raise

        return self._consume(
            reservation=reservation,
            transport_request=request,
            transport_result=result,
            error=None,
        )
