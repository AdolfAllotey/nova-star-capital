from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from options_risk_free_rate_v3 import (
    PROVIDER,
    SERIES_ID,
    build_certified_risk_free_rate_v3,
)

FRED_BASE_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
)


class OptionsRiskFreeRateRuntimeError(RuntimeError):
    pass


class OptionsRiskFreeRateAuthorizationError(
    OptionsRiskFreeRateRuntimeError
):
    pass


@dataclass(frozen=True)
class FredRiskFreeRuntimeConfigV3:
    api_key_env: str = "FRED_API_KEY"
    timeout_seconds: float = 10.0
    maximum_response_bytes: int = 1_000_000
    user_agent: str = "NSC-Options-V3/1.0"


class _NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self, req, fp, code, msg, headers, newurl
    ):
        return None


def build_request_contract_v3(
    *,
    config: FredRiskFreeRuntimeConfigV3 | None = None,
) -> dict[str, Any]:
    cfg = config or FredRiskFreeRuntimeConfigV3()

    return {
        "provider": PROVIDER,
        "series_id": SERIES_ID,
        "base_url": FRED_BASE_URL,
        "api_key_env": cfg.api_key_env,
        "api_key_present": bool(
            os.environ.get(cfg.api_key_env)
        ),
        "network_executed": False,
    }


def build_fred_url_v3(
    request_contract: Mapping[str, Any],
) -> str:
    if request_contract.get("provider") != PROVIDER:
        raise OptionsRiskFreeRateRuntimeError(
            "unexpected provider"
        )

    if request_contract.get("series_id") != SERIES_ID:
        raise OptionsRiskFreeRateRuntimeError(
            "unexpected FRED series"
        )

    base_url = str(
        request_contract.get("base_url") or ""
    )

    if not base_url.startswith("https://"):
        raise OptionsRiskFreeRateRuntimeError(
            "FRED base URL must use HTTPS"
        )

    api_key_env = str(
        request_contract.get("api_key_env")
        or "FRED_API_KEY"
    )
    api_key = os.environ.get(api_key_env)

    if not api_key:
        raise OptionsRiskFreeRateRuntimeError(
            f"{api_key_env} is not configured"
        )

    query = urllib.parse.urlencode({
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10,
    })

    return f"{base_url}?{query}"


def urllib_fred_transport_v3(
    request_contract: Mapping[str, Any],
    *,
    network_authorized: bool = False,
    config: FredRiskFreeRuntimeConfigV3 | None = None,
) -> Mapping[str, Any]:
    if not network_authorized:
        raise OptionsRiskFreeRateAuthorizationError(
            "risk-free provider network call is not authorized"
        )

    cfg = config or FredRiskFreeRuntimeConfigV3()

    if cfg.timeout_seconds <= 0:
        raise OptionsRiskFreeRateRuntimeError(
            "timeout must be positive"
        )

    if cfg.maximum_response_bytes <= 0:
        raise OptionsRiskFreeRateRuntimeError(
            "maximum response size must be positive"
        )

    url = build_fred_url_v3(request_contract)

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(
            context=ssl.create_default_context()
        ),
        _NoRedirectHandler(),
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": cfg.user_agent,
        },
        method="GET",
    )

    try:
        with opener.open(
            request,
            timeout=cfg.timeout_seconds,
        ) as response:
            if int(response.getcode()) != 200:
                raise OptionsRiskFreeRateRuntimeError(
                    "unexpected FRED HTTP status"
                )

            raw = response.read(
                cfg.maximum_response_bytes + 1
            )

    except OptionsRiskFreeRateRuntimeError:
        raise
    except Exception as exc:
        raise OptionsRiskFreeRateRuntimeError(
            "FRED transport failed"
        ) from exc

    if len(raw) > cfg.maximum_response_bytes:
        raise OptionsRiskFreeRateRuntimeError(
            "FRED response exceeds maximum size"
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise OptionsRiskFreeRateRuntimeError(
            "invalid FRED JSON response"
        ) from exc

    if not isinstance(payload, Mapping):
        raise OptionsRiskFreeRateRuntimeError(
            "FRED response must be a mapping"
        )

    return payload


def fetch_certified_risk_free_rate_v3(
    *,
    transport: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    retrieved_at: Any = None,
) -> dict[str, Any]:
    contract = build_request_contract_v3()
    payload = transport(contract)

    if not isinstance(payload, Mapping):
        raise OptionsRiskFreeRateRuntimeError(
            "provider transport must return a mapping"
        )

    timestamp = (
        retrieved_at
        if retrieved_at is not None
        else datetime.now(timezone.utc)
    )

    return build_certified_risk_free_rate_v3(
        payload,
        retrieved_at=timestamp,
    )


def fetch_certified_risk_free_rate_network_v3(
    *,
    network_authorized: bool = False,
    config: FredRiskFreeRuntimeConfigV3 | None = None,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    cfg = config or FredRiskFreeRuntimeConfigV3()

    def transport(
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return urllib_fred_transport_v3(
            contract,
            network_authorized=network_authorized,
            config=cfg,
        )

    return fetch_certified_risk_free_rate_v3(
        transport=transport,
        retrieved_at=retrieved_at,
    )
