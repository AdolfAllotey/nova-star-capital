from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from src.v2.precious_metals import macro_provider_integration as integration


DEFAULT_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_READ_TIMEOUT_SECONDS = 20
DEFAULT_TOTAL_TIMEOUT_SECONDS = 30
DEFAULT_MAXIMUM_ATTEMPTS = 3
DEFAULT_RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_BACKOFF_SECONDS = (1, 3)
DEFAULT_USER_AGENT = "NovaStarCapital-RC2-PreciousMetals/1.0"
DEFAULT_MAXIMUM_RESPONSE_BYTES = 5_000_000
DEFAULT_TARGET_PATH = Path("/opt/nsc/data/preprod/metals/macro_inputs.json")


class MacroProviderRuntimeError(RuntimeError):
    """Base provider runtime error."""


class RuntimeAuthorizationError(MacroProviderRuntimeError):
    """Raised when runtime execution is not explicitly authorized."""


class RuntimeTransportError(MacroProviderRuntimeError):
    """Raised when the outbound provider transport fails."""


class RuntimeResponseError(MacroProviderRuntimeError):
    """Raised when a provider response violates the runtime contract."""


@dataclass(frozen=True)
class FredRuntimeConfig:
    api_key_env: str = "FRED_API_KEY"
    connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS
    read_timeout_seconds: int = DEFAULT_READ_TIMEOUT_SECONDS
    total_timeout_seconds: int = DEFAULT_TOTAL_TIMEOUT_SECONDS
    maximum_attempts: int = DEFAULT_MAXIMUM_ATTEMPTS
    retry_status_codes: frozenset[int] = DEFAULT_RETRY_STATUS_CODES
    retry_backoff_seconds: tuple[int, ...] = DEFAULT_RETRY_BACKOFF_SECONDS
    user_agent: str = DEFAULT_USER_AGENT
    verify_tls: bool = True
    allow_redirects: bool = False
    maximum_response_bytes: int = DEFAULT_MAXIMUM_RESPONSE_BYTES


def validate_runtime_execution_authorization(
    *,
    runtime_execution_authorized: bool,
) -> None:
    if runtime_execution_authorized is not True:
        raise RuntimeAuthorizationError(
            "precious-metals runtime execution is not authorized"
        )


def validate_runtime_config(config: FredRuntimeConfig) -> None:
    if config.connect_timeout_seconds <= 0:
        raise RuntimeTransportError(
            "connect timeout must be greater than zero"
        )

    if config.read_timeout_seconds <= 0:
        raise RuntimeTransportError(
            "read timeout must be greater than zero"
        )

    if config.total_timeout_seconds <= 0:
        raise RuntimeTransportError(
            "total timeout must be greater than zero"
        )

    if config.maximum_attempts < 1 or config.maximum_attempts > 3:
        raise RuntimeTransportError(
            "maximum attempts must be between one and three"
        )

    if config.maximum_response_bytes < 1:
        raise RuntimeTransportError(
            "maximum response bytes must be greater than zero"
        )

    if config.verify_tls is not True:
        raise RuntimeTransportError(
            "TLS verification must remain enabled"
        )

    if config.allow_redirects is not False:
        raise RuntimeTransportError(
            "HTTP redirects must remain disabled"
        )


def build_fred_url(request_contract: Mapping[str, Any]) -> str:
    base_url = str(request_contract.get("base_url", "")).strip()
    series_id = str(request_contract.get("series_id", "")).strip()
    api_key_env = str(
        request_contract.get("api_key_env", "FRED_API_KEY")
    ).strip()

    if not base_url.startswith("https://"):
        raise RuntimeTransportError(
            "FRED base URL must use HTTPS"
        )

    if series_id not in {"CPIAUCSL", "DFII10", "NFCI", "DTWEXBGS"}:
        raise RuntimeTransportError(
            f"runtime request contains an unapproved series: {series_id}"
        )

    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        raise RuntimeAuthorizationError(
            f"required provider API key is missing: {api_key_env}"
        )

    query = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "asc",
        }
    )

    return f"{base_url}?{query}"


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _read_bounded_response(
    response: Any,
    *,
    maximum_response_bytes: int,
) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except Exception as exc:
            raise RuntimeResponseError(
                "provider Content-Length is invalid"
            ) from exc

        if declared_size > maximum_response_bytes:
            raise RuntimeResponseError(
                "provider response exceeds maximum allowed size"
            )

    payload = response.read(maximum_response_bytes + 1)

    if len(payload) > maximum_response_bytes:
        raise RuntimeResponseError(
            "provider response exceeds maximum allowed size"
        )

    return payload


def urllib_fred_transport(
    request_contract: Mapping[str, Any],
    *,
    network_authorized: bool = False,
    config: FredRuntimeConfig | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
) -> Mapping[str, Any]:
    integration.contract.validate_network_authorization(
        network_authorized=network_authorized
    )

    runtime_config = config or FredRuntimeConfig()
    validate_runtime_config(runtime_config)

    url = build_fred_url(request_contract)

    ssl_context = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context),
        _NoRedirectHandler(),
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": runtime_config.user_agent,
        },
        method="GET",
    )

    last_error: Exception | None = None

    for attempt in range(1, runtime_config.maximum_attempts + 1):
        try:
            with opener.open(
                request,
                timeout=runtime_config.total_timeout_seconds,
            ) as response:
                status_code = int(response.getcode())

                if status_code != 200:
                    raise RuntimeTransportError(
                        f"unexpected provider HTTP status: {status_code}"
                    )

                raw_payload = _read_bounded_response(
                    response,
                    maximum_response_bytes=(
                        runtime_config.maximum_response_bytes
                    ),
                )

                try:
                    payload = json.loads(raw_payload.decode("utf-8"))
                except Exception as exc:
                    raise RuntimeResponseError(
                        "provider response is not valid UTF-8 JSON"
                    ) from exc

                if not isinstance(payload, Mapping):
                    raise RuntimeResponseError(
                        "provider response root must be a mapping"
                    )

                return payload

        except urllib.error.HTTPError as exc:
            last_error = exc

            if (
                exc.code not in runtime_config.retry_status_codes
                or attempt >= runtime_config.maximum_attempts
            ):
                raise RuntimeTransportError(
                    f"provider HTTP request failed with status {exc.code}"
                ) from exc

        except urllib.error.URLError as exc:
            last_error = exc

            if attempt >= runtime_config.maximum_attempts:
                raise RuntimeTransportError(
                    f"provider connection failed: {exc.reason}"
                ) from exc

        except TimeoutError as exc:
            last_error = exc

            if attempt >= runtime_config.maximum_attempts:
                raise RuntimeTransportError(
                    "provider request timed out"
                ) from exc

        if attempt < runtime_config.maximum_attempts:
            backoff_index = min(
                attempt - 1,
                len(runtime_config.retry_backoff_seconds) - 1,
            )
            sleep_function(
                runtime_config.retry_backoff_seconds[backoff_index]
            )

    raise RuntimeTransportError(
        f"provider request failed: {last_error}"
    )


def collect_macro_provider_payload(
    *,
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    network_authorized: bool = False,
    provisioning_authorized: bool = False,
    target_path: str | Path | None = None,
    as_of: Any = None,
) -> dict[str, Any]:
    return integration.run_macro_provider_integration(
        transport=transport,
        network_authorized=network_authorized,
        provisioning_authorized=provisioning_authorized,
        target_path=target_path,
        as_of=as_of,
    )


def collect_and_provision_macro_inputs(
    *,
    network_authorized: bool = False,
    provisioning_authorized: bool = False,
    target_path: str | Path = DEFAULT_TARGET_PATH,
    config: FredRuntimeConfig | None = None,
    as_of: Any = None,
) -> dict[str, Any]:
    runtime_config = config or FredRuntimeConfig()

    def transport(
        request_contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return urllib_fred_transport(
            request_contract,
            network_authorized=network_authorized,
            config=runtime_config,
        )

    return collect_macro_provider_payload(
        transport=transport,
        network_authorized=network_authorized,
        provisioning_authorized=provisioning_authorized,
        target_path=target_path,
        as_of=as_of,
    )


def execute_precious_metals_runtime(
    *,
    network_authorized: bool = False,
    provisioning_authorized: bool = False,
    runtime_execution_authorized: bool = False,
    certified_input_authorized: bool = False,
    target_path: str | Path = DEFAULT_TARGET_PATH,
    config: FredRuntimeConfig | None = None,
    pipeline_callable: Callable[[], Any] | None = None,
    as_of: Any = None,
) -> dict[str, Any]:
    validate_runtime_execution_authorization(
        runtime_execution_authorized=runtime_execution_authorized
    )

    if certified_input_authorized:
        if network_authorized:
            raise RuntimeAuthorizationError(
                "certified-input runtime forbids provider network authorization"
            )

        if provisioning_authorized:
            raise RuntimeAuthorizationError(
                "certified-input runtime forbids macro input provisioning"
            )

        from src.v2.precious_metals.metals_utils import (
            load_and_validate_macro_inputs,
        )

        payload = load_and_validate_macro_inputs(
            target_path
        )

    else:
        payload = collect_and_provision_macro_inputs(
            network_authorized=network_authorized,
            provisioning_authorized=provisioning_authorized,
            target_path=target_path,
            config=config,
            as_of=as_of,
        )

    if pipeline_callable is None:
        from src.v2.precious_metals.run_metals_pipeline import (
            run_metals_pipeline,
        )

        pipeline_callable = run_metals_pipeline

    pipeline_result = pipeline_callable()

    return {
        "macro_payload": payload,
        "pipeline_result": pipeline_result,
    }


def runtime_contract_summary() -> dict[str, Any]:
    config = FredRuntimeConfig()

    return {
        "runtime": "precious_metals_macro_provider_runtime_v1",
        "provider": "fred",
        "api_key_env": config.api_key_env,
        "approved_series": [
            "CPIAUCSL",
            "DFII10",
            "NFCI",
            "DTWEXBGS",
        ],
        "connect_timeout_seconds": config.connect_timeout_seconds,
        "read_timeout_seconds": config.read_timeout_seconds,
        "total_request_timeout_seconds": (
            config.total_timeout_seconds
        ),
        "maximum_attempts": config.maximum_attempts,
        "retry_status_codes": sorted(config.retry_status_codes),
        "retry_backoff_seconds": list(
            config.retry_backoff_seconds
        ),
        "user_agent": config.user_agent,
        "tls_verification_required": config.verify_tls,
        "redirects_allowed": config.allow_redirects,
        "maximum_response_bytes": config.maximum_response_bytes,
        "network_authorized_by_default": False,
        "provisioning_authorized_by_default": False,
        "runtime_execution_authorized_by_default": False,
    }
