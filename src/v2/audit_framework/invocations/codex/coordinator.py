from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
import fcntl
import hashlib
import json
import os
import uuid

from src.v2.audit_framework.core.utils import (
    atomic_write_json,
    read_json,
    utc_now_iso,
)
from src.v2.audit_framework.invocations.contracts import (
    InvocationReceipt,
    InvocationReservation,
)
from src.v2.audit_framework.transports.base import (
    ProviderTransport,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
)


class CodexInvocationCoordinator:
    """
    Atomic coordinator for a single-use Codex invocation.

    The coordinator does not decide whether an execution gate
    should be approved. It only enforces an already-approved
    gate and guarantees single reservation/consumption.
    """

    PROVIDER_ID = "OPENAI_CODEX"
    COORDINATOR_VERSION = "1.0.0"

    AUTHORIZED_STATUSES = {
        "AUTHORIZED_FOR_SINGLE_EXECUTION",
    }

    RESERVED_STATUS = "RESERVED_FOR_EXECUTION"

    TERMINAL_STATUSES = {
        "CONSUMED_SIMULATED",
        "CONSUMED_AFTER_EXECUTION",
        "CONSUMED_AFTER_FAILURE",
        "CONSUMED_WITHOUT_EXECUTION",
        "REVOKED",
    }

    def __init__(
        self,
        *,
        package_dir: Path,
        gate_id: str,
    ) -> None:
        self.package_dir = (
            package_dir.resolve()
        )

        self.gate_id = gate_id

        self.gate_dir = (
            self.package_dir
            / "execution_gates"
            / "openai_codex"
            / gate_id
        )

        self.state_path = (
            self.gate_dir
            / "execution_gate_state.json"
        )

        self.request_path = (
            self.gate_dir
            / "execution_gate_request.json"
        )

        self.lock_path = (
            self.gate_dir
            / ".invocation.lock"
        )

        self.invocations_dir = (
            self.gate_dir
            / "invocations"
        )

    @staticmethod
    def _canonical_sha256(
        payload: dict[str, Any],
    ) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(
            encoded
        ).hexdigest()

    @contextmanager
    def _exclusive_lock(
        self,
    ) -> Iterator[None]:
        self.gate_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        descriptor = os.open(
            self.lock_path,
            os.O_CREAT | os.O_RDWR,
            0o600,
        )

        try:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_EX,
            )

            yield
        finally:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_UN,
            )

            os.close(descriptor)

    def _load_gate_documents(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
    ]:
        if not self.request_path.is_file():
            raise RuntimeError(
                "Execution gate request is missing."
            )

        if not self.state_path.is_file():
            raise RuntimeError(
                "Execution gate state is missing."
            )

        request = read_json(
            self.request_path
        )

        state = read_json(
            self.state_path
        )

        return request, state

    def _validate_gate_binding(
        self,
        *,
        request: dict[str, Any],
        state: dict[str, Any],
        payload_sha256: str,
        package_readiness_sha256: str,
    ) -> None:
        if (
            request.get("gate_id")
            != self.gate_id
        ):
            raise RuntimeError(
                "Gate request identity mismatch."
            )

        if (
            request.get("provider_id")
            != self.PROVIDER_ID
        ):
            raise RuntimeError(
                "Gate provider mismatch."
            )

        if (
            state.get("gate_id")
            not in (None, self.gate_id)
        ):
            raise RuntimeError(
                "Gate state identity mismatch."
            )

        if state.get("consumed") is True:
            raise RuntimeError(
                "Execution gate is already consumed."
            )

        if state.get("revoked") is True:
            raise RuntimeError(
                "Execution gate is revoked."
            )

        if state.get("approved") is not True:
            raise RuntimeError(
                "Execution gate is not approved."
            )

        if (
            state.get("status")
            not in self.AUTHORIZED_STATUSES
        ):
            raise RuntimeError(
                "Execution gate is not available "
                "for reservation."
            )

        if (
            request.get(
                "package_readiness_sha256"
            )
            != package_readiness_sha256
        ):
            raise RuntimeError(
                "Package SHA binding mismatch."
            )

        if (
            request.get("payload_sha256")
            != payload_sha256
        ):
            raise RuntimeError(
                "Payload SHA binding mismatch."
            )

        if request.get("single_use") is not True:
            raise RuntimeError(
                "Gate is not single-use."
            )

        if request.get("read_only") is not True:
            raise RuntimeError(
                "Read-only policy is missing."
            )

        if (
            request.get(
                "recommendation_only"
            )
            is not True
        ):
            raise RuntimeError(
                "Recommendation-only policy "
                "is missing."
            )

        if (
            request.get(
                "automatic_remediation"
            )
            is not False
        ):
            raise RuntimeError(
                "Automatic remediation is enabled."
            )

        if (
            request.get(
                "allow_source_writes"
            )
            is not False
        ):
            raise RuntimeError(
                "Source writes are enabled."
            )

        if (
            request.get(
                "allow_live_trading"
            )
            is not False
        ):
            raise RuntimeError(
                "Live trading is enabled."
            )

        if (
            request.get(
                "allow_production_credentials"
            )
            is not False
        ):
            raise RuntimeError(
                "Production credentials are enabled."
            )

    def reserve(
        self,
        *,
        invocation_id: str,
        payload_sha256: str,
        package_readiness_sha256: str,
        transport_mode: str,
        network_invocation_authorized: bool,
    ) -> InvocationReservation:
        with self._exclusive_lock():
            request, state = (
                self._load_gate_documents()
            )

            self._validate_gate_binding(
                request=request,
                state=state,
                payload_sha256=payload_sha256,
                package_readiness_sha256=(
                    package_readiness_sha256
                ),
            )

            reservation_id = (
                "RESERVATION-CODEX-"
                + uuid.uuid4().hex.upper()
            )

            reservation = InvocationReservation(
                schema_version="1.0",
                reservation_id=reservation_id,
                invocation_id=invocation_id,
                gate_id=self.gate_id,
                provider_id=self.PROVIDER_ID,
                audit_id=request["audit_id"],
                status=self.RESERVED_STATUS,
                reserved_at=utc_now_iso(),
                package_readiness_sha256=(
                    package_readiness_sha256
                ),
                payload_sha256=payload_sha256,
                transport_mode=transport_mode,
                network_invocation_authorized=(
                    network_invocation_authorized
                ),
                metadata={
                    "coordinator_version": (
                        self.COORDINATOR_VERSION
                    ),
                    "single_use": True,
                    "read_only": True,
                    "recommendation_only": True,
                    "automatic_remediation": False,
                },
            )

            invocation_dir = (
                self.invocations_dir
                / invocation_id
            )

            invocation_dir.mkdir(
                parents=True,
                exist_ok=False,
            )

            atomic_write_json(
                invocation_dir
                / "invocation_reservation.json",
                reservation.to_dict(),
            )

            state.update(
                {
                    "status": self.RESERVED_STATUS,
                    "reserved": True,
                    "reservation_id": (
                        reservation_id
                    ),
                    "invocation_id": (
                        invocation_id
                    ),
                    "reserved_at": (
                        reservation.reserved_at
                    ),
                    "transport_mode": (
                        transport_mode
                    ),
                    "network_invocation_authorized": (
                        network_invocation_authorized
                    ),
                    "provider_executed": False,
                    "automatic_remediation": False,
                }
            )

            atomic_write_json(
                self.state_path,
                state,
            )

            return reservation

    def _consume(
        self,
        *,
        reservation: InvocationReservation,
        transport_request: (
            ProviderTransportRequest
        ),
        transport_result: Any | None,
        error: BaseException | None,
    ) -> InvocationReceipt:
        with self._exclusive_lock():
            _, state = (
                self._load_gate_documents()
            )

            if (
                state.get("reservation_id")
                != reservation.reservation_id
            ):
                raise RuntimeError(
                    "Reservation ownership mismatch."
                )

            if (
                state.get("invocation_id")
                != reservation.invocation_id
            ):
                raise RuntimeError(
                    "Invocation ownership mismatch."
                )

            if (
                state.get("status")
                != self.RESERVED_STATUS
            ):
                raise RuntimeError(
                    "Gate is no longer reserved."
                )

            invocation_dir = (
                self.invocations_dir
                / reservation.invocation_id
            )

            request_payload = (
                transport_request.to_dict()
            )

            atomic_write_json(
                invocation_dir
                / "transport_request.json",
                request_payload,
            )

            if transport_result is not None:
                result_payload = (
                    transport_result.to_dict()
                )

                atomic_write_json(
                    invocation_dir
                    / "transport_result.json",
                    result_payload,
                )

                provider_executed = bool(
                    transport_result
                    .provider_executed
                )

                network_performed = bool(
                    transport_result
                    .network_invocation_performed
                )

                status = (
                    "CONSUMED_AFTER_EXECUTION"
                    if provider_executed
                    else "CONSUMED_SIMULATED"
                )

                request_sha256 = (
                    transport_result
                    .request_sha256
                )

                response_sha256 = (
                    transport_result
                    .response_sha256
                )

                provider_response_id = (
                    transport_result
                    .provider_response_id
                )

                retryable = bool(
                    transport_result.retryable
                )

                error_type = (
                    transport_result.error_type
                )

                error_message = (
                    transport_result.error_message
                )

                started_at = (
                    transport_result.started_at
                )

                completed_at = (
                    transport_result.completed_at
                )
            else:
                provider_executed = False
                network_performed = False
                status = (
                    "CONSUMED_AFTER_FAILURE"
                )

                request_sha256 = (
                    self._canonical_sha256(
                        request_payload
                    )
                )

                response_sha256 = None
                provider_response_id = None
                retryable = False
                error_type = (
                    type(error).__name__
                    if error is not None
                    else "UnknownError"
                )

                error_message = (
                    str(error)
                    if error is not None
                    else "Unknown invocation error."
                )

                started_at = (
                    reservation.reserved_at
                )

                completed_at = utc_now_iso()

            receipt = InvocationReceipt(
                schema_version="1.0",
                reservation_id=(
                    reservation.reservation_id
                ),
                invocation_id=(
                    reservation.invocation_id
                ),
                gate_id=self.gate_id,
                provider_id=self.PROVIDER_ID,
                audit_id=reservation.audit_id,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                package_readiness_sha256=(
                    reservation
                    .package_readiness_sha256
                ),
                payload_sha256=(
                    reservation.payload_sha256
                ),
                request_sha256=request_sha256,
                response_sha256=response_sha256,
                provider_response_id=(
                    provider_response_id
                ),
                transport_mode=(
                    reservation.transport_mode
                ),
                network_invocation_performed=(
                    network_performed
                ),
                provider_executed=(
                    provider_executed
                ),
                gate_consumed=True,
                retryable=retryable,
                error_type=error_type,
                error_message=error_message,
                metadata={
                    "coordinator_version": (
                        self.COORDINATOR_VERSION
                    ),
                    "single_use": True,
                    "automatic_remediation": False,
                    "source_writes": False,
                    "live_trading": False,
                },
            )

            atomic_write_json(
                invocation_dir
                / "invocation_receipt.json",
                receipt.to_dict(),
            )

            atomic_write_json(
                self.gate_dir
                / "execution_gate_receipt.json",
                {
                    "schema_version": "1.0",
                    "gate_id": self.gate_id,
                    "provider_id": (
                        self.PROVIDER_ID
                    ),
                    "audit_id": (
                        reservation.audit_id
                    ),
                    "status": status,
                    "consumed_at": completed_at,
                    "package_readiness_sha256": (
                        reservation
                        .package_readiness_sha256
                    ),
                    "payload_sha256": (
                        reservation.payload_sha256
                    ),
                    "execution_reference": (
                        reservation.invocation_id
                    ),
                    "provider_executed": (
                        provider_executed
                    ),
                    "automatic_remediation": False,
                    "metadata": {
                        "reservation_id": (
                            reservation.reservation_id
                        ),
                        "transport_mode": (
                            reservation.transport_mode
                        ),
                        "network_invocation_performed": (
                            network_performed
                        ),
                    },
                },
            )

            state.update(
                {
                    "status": status,
                    "consumed": True,
                    "consumed_at": completed_at,
                    "provider_executed": (
                        provider_executed
                    ),
                    "network_invocation_performed": (
                        network_performed
                    ),
                    "automatic_remediation": False,
                    "request_sha256": (
                        request_sha256
                    ),
                    "response_sha256": (
                        response_sha256
                    ),
                    "provider_response_id": (
                        provider_response_id
                    ),
                    "error_type": error_type,
                    "error_message": (
                        error_message
                    ),
                }
            )

            atomic_write_json(
                self.state_path,
                state,
            )

            return receipt

    def invoke(
        self,
        *,
        request: ProviderTransportRequest,
        transport: ProviderTransport,
    ) -> InvocationReceipt:
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

        try:
            result = transport.invoke(
                request
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
