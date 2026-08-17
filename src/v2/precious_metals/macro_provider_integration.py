from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.v2.precious_metals import macro_provider_contract as contract


APPROVED_FRED_SERIES = {
    "CPIAUCSL",
    "DFII10",
    "NFCI",
    "DTWEXBGS",
}

DEFAULT_REQUEST_SERIES = (
    "CPIAUCSL",
    "DFII10",
    "NFCI",
    "DTWEXBGS",
)


class MacroProviderIntegrationError(Exception):
    """Base integration error."""


class ProviderPlanValidationError(
    MacroProviderIntegrationError
):
    """Raised when a provider request plan is invalid."""


class ProviderPayloadValidationError(
    MacroProviderIntegrationError
):
    """Raised when provider responses are incomplete."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat_utc(
    value: datetime | None = None,
) -> str:
    dt = value or _utc_now()
    return (
        dt.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_provider_request_plan(
    *,
    series_ids: tuple[str, ...] = DEFAULT_REQUEST_SERIES,
) -> list[dict[str, Any]]:
    if not series_ids:
        raise ProviderPlanValidationError(
            "provider request plan must not be empty"
        )

    plan: list[dict[str, Any]] = []
    seen: set[str] = set()

    for series_id in series_ids:
        if series_id not in APPROVED_FRED_SERIES:
            raise ProviderPlanValidationError(
                f"unapproved provider series: {series_id}"
            )

        if series_id in seen:
            continue

        seen.add(series_id)

        plan.append(
            contract.build_fred_request_contract(
                series_id
            )
        )

    if set(seen) != set(DEFAULT_REQUEST_SERIES):
        missing = sorted(
            set(DEFAULT_REQUEST_SERIES) - seen
        )
        raise ProviderPlanValidationError(
            "provider request plan is incomplete: "
            + ",".join(missing)
        )

    return plan


def fetch_provider_payloads(
    request_plan: list[Mapping[str, Any]],
    *,
    transport: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    network_authorized: bool = False,
) -> dict[str, Mapping[str, Any]]:
    if not request_plan:
        raise ProviderPlanValidationError(
            "provider request plan must not be empty"
        )

    payloads: dict[str, Mapping[str, Any]] = {}

    for request_contract in request_plan:
        series_id = str(
            request_contract.get("series_id", "")
        )

        if series_id not in APPROVED_FRED_SERIES:
            raise ProviderPlanValidationError(
                f"unapproved provider series: {series_id}"
            )

        payloads[series_id] = (
            contract.execute_provider_request(
                request_contract,
                transport=transport,
                network_authorized=network_authorized,
            )
        )

    missing = sorted(
        set(DEFAULT_REQUEST_SERIES) - set(payloads)
    )

    if missing:
        raise ProviderPayloadValidationError(
            "required provider payloads are missing: "
            + ",".join(missing)
        )

    return payloads


def derive_macro_values(
    provider_payloads: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    parsed: dict[str, list[dict[str, Any]]] = {}

    for series_id in DEFAULT_REQUEST_SERIES:
        if series_id not in provider_payloads:
            raise ProviderPayloadValidationError(
                f"missing provider payload: {series_id}"
            )

        parsed[series_id] = (
            contract.parse_fred_observations(
                provider_payloads[series_id],
                series_id=series_id,
            )
        )

    cpi_yoy, cpi_yoy_evidence = (
        contract.derive_cpi_yoy(
            parsed["CPIAUCSL"]
        )
    )
    inflation_trend, inflation_trend_evidence = (
        contract.derive_inflation_trend_3m(
            parsed["CPIAUCSL"]
        )
    )
    real_rate_values, real_rate_evidence = (
        contract.derive_real_rate_fields(
            parsed["DFII10"]
        )
    )
    usd_values, usd_evidence = (
        contract.derive_usd_fields(
            parsed["DTWEXBGS"]
        )
    )

    nfci_latest = contract.latest_observation(
        parsed["NFCI"]
    )
    liquidity_stress = (
        contract.nfci_to_liquidity_stress(
            float(nfci_latest["value"])
        )
    )

    credibility_score, credibility_evidence = (
        contract.derive_central_bank_credibility_score(
            inflation_gap_abs=abs(cpi_yoy - 2.0),
            inflation_acceleration_abs=abs(
                inflation_trend
            ),
            real_rate_instability_abs=abs(
                real_rate_values[
                    "real_rate_trend_1m"
                ]
            ),
        )
    )

    banking_stress, banking_evidence = (
        contract.derive_banking_stress_score(
            bank_equity_drawdown=0.20,
            bank_credit_spread_stress=0.30,
            deposit_stress=0.20,
        )
    )

    market_stress = min(
        1.0,
        max(
            0.0,
            abs(
                real_rate_values[
                    "real_rate_trend_1m"
                ]
            )
            / 2.0,
        ),
    )

    systemic_stress, systemic_evidence = (
        contract.derive_systemic_stress_score(
            liquidity_stress=liquidity_stress,
            banking_stress=banking_stress,
            market_stress=market_stress,
        )
    )

    values = {
        "inflation": {
            "cpi_yoy": cpi_yoy,
            "inflation_trend_3m": inflation_trend,
            "central_bank_credibility_score": (
                credibility_score
            ),
        },
        "real_rates": {
            "us_10y_real": real_rate_values[
                "us_10y_real"
            ],
            "real_rate_trend_1m": real_rate_values[
                "real_rate_trend_1m"
            ],
        },
        "systemic_stress": {
            "stress_score": systemic_stress,
            "liquidity_stress": liquidity_stress,
            "banking_stress": banking_stress,
        },
        "usd": {
            "dxy": usd_values["dxy"],
            "dxy_trend_1m": usd_values[
                "dxy_trend_1m"
            ],
        },
    }

    evidence = {
        "inflation.cpi_yoy": cpi_yoy_evidence,
        "inflation.inflation_trend_3m": (
            inflation_trend_evidence
        ),
        "inflation.central_bank_credibility_score": (
            credibility_evidence
        ),
        "real_rates.us_10y_real": (
            real_rate_evidence
        ),
        "real_rates.real_rate_trend_1m": (
            real_rate_evidence
        ),
        "systemic_stress.stress_score": (
            systemic_evidence
        ),
        "systemic_stress.liquidity_stress": {
            "latest_observation": nfci_latest,
            "transformation": (
                "approved bounded NFCI normalization"
            ),
        },
        "systemic_stress.banking_stress": (
            banking_evidence
        ),
        "usd.dxy": usd_evidence,
        "usd.dxy_trend_1m": usd_evidence,
    }

    return values, evidence


def _field_value(
    values: Mapping[str, Any],
    field: str,
) -> Any:
    current: Any = values

    for part in field.split("."):
        if (
            not isinstance(current, Mapping)
            or part not in current
        ):
            raise ProviderPayloadValidationError(
                f"derived macro field is missing: {field}"
            )

        current = current[part]

    return current


def build_macro_provenance(
    values: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
    *,
    retrieved_at: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    timestamp = _isoformat_utc(
        retrieved_at or _utc_now()
    )

    provenance: dict[str, dict[str, Any]] = {}

    for field, field_contract in (
        contract.FIELD_CONTRACTS.items()
    ):
        value = _field_value(values, field)
        field_evidence = dict(
            evidence.get(field, {})
        )

        observed_at = timestamp

        latest = (
            field_evidence.get("latest_observation")
            or field_evidence.get("latest")
        )

        if (
            latest is None
            and field == "inflation.inflation_trend_3m"
        ):
            current_yoy = field_evidence.get(
                "current_yoy"
            )

            if isinstance(current_yoy, Mapping):
                latest = current_yoy.get(
                    "latest"
                )
        if isinstance(latest, Mapping):
            raw_observed_at = str(
                latest.get("date", timestamp)
            )

            # FRED observation dates are returned as YYYY-MM-DD.
            # Preserve the economic observation date while making
            # provenance timestamps timezone-aware as required by
            # the RC2 contract.
            if (
                len(raw_observed_at) == 10
                and raw_observed_at[4] == "-"
                and raw_observed_at[7] == "-"
            ):
                observed_at = (
                    raw_observed_at
                    + "T00:00:00+00:00"
                )
            else:
                observed_at = raw_observed_at

        if field.startswith("inflation."):
            if field.endswith(
                "central_bank_credibility_score"
            ):
                provider = "derived_multi_series"
                series = (
                    "central_bank_credibility_composite_v1"
                )
            else:
                provider = "fred"
                series = "CPIAUCSL"

        elif field.startswith("real_rates."):
            provider = "fred"
            series = "DFII10"

        elif field == (
            "systemic_stress.liquidity_stress"
        ):
            provider = "fred"
            series = "NFCI"

        elif field == (
            "systemic_stress.banking_stress"
        ):
            provider = "derived_multi_series"
            series = "banking_stress_composite_v1"

        elif field == (
            "systemic_stress.stress_score"
        ):
            provider = "derived_multi_series"
            series = "systemic_stress_composite_v1"

        else:
            provider = "fred"
            series = "DTWEXBGS"

        provenance[field] = (
            contract.make_provenance_entry(
                field=field,
                provider=provider,
                series=series,
                observed_at=observed_at,
                retrieved_at=timestamp,
                source_url=(
                    "https://api.stlouisfed.org/"
                    "fred/series/observations"
                ),
                source_value=value,
                transformation=(
                    "approved RC2 provider integration "
                    "derivation"
                ),
                semantic_qualification=(
                    field_contract.semantic_qualification
                ),
                components={
                    "integration": (
                        "macro_provider_integration_v1"
                    ),
                    "evidence": field_evidence,
                },
            )
        )

    return provenance


def assemble_macro_payload(
    values: Mapping[str, Any],
    provenance: Mapping[str, Any],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or _utc_now()

    payload = {
        "schema_version": contract.SCHEMA_VERSION,
        "status": "valid",
        "generated_at": _isoformat_utc(timestamp),
        "source": {
            "provider_contract_version": (
                contract.PROVIDER_CONTRACT_VERSION
            ),
            "integration": (
                "precious_metals_macro_provider_"
                "integration_v1"
            ),
            "derived_metals_outputs_used": False,
            "network_execution": (
                "external_provider_transport"
            ),
        },
        **deepcopy(dict(values)),
        "provenance": deepcopy(
            dict(provenance)
        ),
    }

    contract.validate_macro_payload(
        payload,
        as_of=timestamp,
    )

    return payload


def provision_macro_inputs(
    target_path: str | Path,
    payload: Mapping[str, Any],
    *,
    provisioning_authorized: bool = False,
    as_of: datetime | None = None,
) -> None:
    contract.atomic_write_macro_payload(
        target_path,
        payload,
        provisioning_authorized=(
            provisioning_authorized
        ),
        as_of=as_of,
    )


def run_macro_provider_integration(
    *,
    transport: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    network_authorized: bool = False,
    provisioning_authorized: bool = False,
    target_path: str | Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    reference_time = as_of or _utc_now()

    request_plan = build_provider_request_plan()

    provider_payloads = fetch_provider_payloads(
        request_plan,
        transport=transport,
        network_authorized=network_authorized,
    )

    values, evidence = derive_macro_values(
        provider_payloads
    )

    provenance = build_macro_provenance(
        values,
        evidence,
        retrieved_at=reference_time,
    )

    payload = assemble_macro_payload(
        values,
        provenance,
        generated_at=reference_time,
    )

    if target_path is not None:
        provision_macro_inputs(
            target_path,
            payload,
            provisioning_authorized=(
                provisioning_authorized
            ),
            as_of=reference_time,
        )

    return payload
