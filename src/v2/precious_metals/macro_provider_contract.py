from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = "1.0"
PROVIDER_CONTRACT_VERSION = "1.0"
PRIMARY_PROVIDER = "fred"
DEFAULT_FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

PRODUCTION_NETWORK_CALLS_AUTHORIZED = False
MACRO_INPUT_PROVISIONING_AUTHORIZED = False

DERIVED_METALS_OUTPUTS_FORBIDDEN_AS_PRIMARY_SOURCES = True
SELF_REFERENTIAL_REUSE_FORBIDDEN = True
ATOMIC_WRITE_REQUIRED = True
PARTIAL_WRITE_FORBIDDEN = True
PRESERVE_PREVIOUS_VALID_INPUT_ON_FAILURE = True


class MacroProviderContractError(RuntimeError):
    """Base exception for the precious-metals provider contract."""


class ProviderAuthorizationError(MacroProviderContractError):
    """Raised when a network or provisioning action is not authorized."""


class ProviderResponseError(MacroProviderContractError):
    """Raised when provider data does not satisfy the approved contract."""


class ProvenanceValidationError(MacroProviderContractError):
    """Raised when provenance is missing, incomplete or inconsistent."""


class MacroPayloadValidationError(MacroProviderContractError):
    """Raised when the final macro payload fails closed validation."""


@dataclass(frozen=True)
class FieldContract:
    field: str
    provider: str
    series: str
    unit: str
    max_age_days: int
    minimum: float
    maximum: float
    derivation: str
    semantic_qualification: str | None = None


FIELD_CONTRACTS: dict[str, FieldContract] = {
    "inflation.cpi_yoy": FieldContract(
        field="inflation.cpi_yoy",
        provider="fred",
        series="CPIAUCSL",
        unit="percent_year_over_year",
        max_age_days=45,
        minimum=-10.0,
        maximum=30.0,
        derivation="year_over_year_percent_change",
    ),
    "inflation.inflation_trend_3m": FieldContract(
        field="inflation.inflation_trend_3m",
        provider="fred",
        series="CPIAUCSL",
        unit="percentage_points",
        max_age_days=45,
        minimum=-10.0,
        maximum=10.0,
        derivation="three_month_change_in_yoy_inflation",
    ),
    "inflation.central_bank_credibility_score": FieldContract(
        field="inflation.central_bank_credibility_score",
        provider="derived_multi_series",
        series="central_bank_credibility_composite_v1",
        unit="normalized_score_0_to_1",
        max_age_days=45,
        minimum=0.0,
        maximum=1.0,
        derivation="central_bank_credibility_composite_v1",
    ),
    "real_rates.us_10y_real": FieldContract(
        field="real_rates.us_10y_real",
        provider="fred",
        series="DFII10",
        unit="percent",
        max_age_days=7,
        minimum=-10.0,
        maximum=15.0,
        derivation="latest_observation",
    ),
    "real_rates.real_rate_trend_1m": FieldContract(
        field="real_rates.real_rate_trend_1m",
        provider="fred",
        series="DFII10",
        unit="percentage_points",
        max_age_days=7,
        minimum=-10.0,
        maximum=10.0,
        derivation="latest_minus_observation_approximately_one_month_prior",
    ),
    "systemic_stress.stress_score": FieldContract(
        field="systemic_stress.stress_score",
        provider="derived_multi_series",
        series="systemic_stress_composite_v1",
        unit="normalized_score_0_to_1",
        max_age_days=7,
        minimum=0.0,
        maximum=1.0,
        derivation="systemic_stress_composite_v1",
    ),
    "systemic_stress.liquidity_stress": FieldContract(
        field="systemic_stress.liquidity_stress",
        provider="fred",
        series="NFCI",
        unit="normalized_score_0_to_1",
        max_age_days=14,
        minimum=0.0,
        maximum=1.0,
        derivation="nfci_to_bounded_stress_score_v1",
        semantic_qualification=(
            "NFCI is used as a broad financial-conditions proxy and is not "
            "represented as a direct market-liquidity measurement."
        ),
    ),
    "systemic_stress.banking_stress": FieldContract(
        field="systemic_stress.banking_stress",
        provider="derived_multi_series",
        series="banking_stress_composite_v1",
        unit="normalized_score_0_to_1",
        max_age_days=7,
        minimum=0.0,
        maximum=1.0,
        derivation="banking_stress_composite_v1",
    ),
    "usd.dxy": FieldContract(
        field="usd.dxy",
        provider="fred",
        series="DTWEXBGS",
        unit="index_points",
        max_age_days=7,
        minimum=50.0,
        maximum=200.0,
        derivation="latest_observation",
        semantic_qualification=(
            "DTWEXBGS is a broad trade-weighted US dollar index proxy. "
            "It is not ICE DXY and must not be labelled as ICE DXY."
        ),
    ),
    "usd.dxy_trend_1m": FieldContract(
        field="usd.dxy_trend_1m",
        provider="fred",
        series="DTWEXBGS",
        unit="percent_change",
        max_age_days=7,
        minimum=-50.0,
        maximum=50.0,
        derivation="one_month_percent_change",
        semantic_qualification=(
            "Trend is derived from DTWEXBGS, not from the ICE DXY instrument."
        ),
    ),
}


REQUIRED_FIELDS = tuple(FIELD_CONTRACTS)
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "inflation": (
        "cpi_yoy",
        "inflation_trend_3m",
        "central_bank_credibility_score",
    ),
    "real_rates": (
        "us_10y_real",
        "real_rate_trend_1m",
    ),
    "systemic_stress": (
        "stress_score",
        "liquidity_stress",
        "banking_stress",
    ),
    "usd": (
        "dxy",
        "dxy_trend_1m",
    ),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ProvenanceValidationError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceValidationError("timestamp must be a non-empty string")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ProvenanceValidationError(
            f"invalid timestamp: {value}"
        ) from exc
    if parsed.tzinfo is None:
        raise ProvenanceValidationError(
            f"timestamp is not timezone-aware: {value}"
        )
    return parsed.astimezone(timezone.utc)


def finite_number(
    value: Any,
    *,
    field: str,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderResponseError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ProviderResponseError(f"{field} must be finite")
    if number < minimum or number > maximum:
        raise ProviderResponseError(
            f"{field} is outside the approved range "
            f"[{minimum}, {maximum}]: {number}"
        )
    return number


def bounded_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 6)


def validate_network_authorization(
    *,
    network_authorized: bool,
) -> None:
    if not network_authorized:
        raise ProviderAuthorizationError(
            "production provider network calls are not authorized"
        )


def validate_provisioning_authorization(
    *,
    provisioning_authorized: bool,
) -> None:
    if not provisioning_authorized:
        raise ProviderAuthorizationError(
            "macro input provisioning is not authorized"
        )


def build_fred_request_contract(
    series_id: str,
    *,
    api_key_env: str = "FRED_API_KEY",
    base_url: str = DEFAULT_FRED_BASE_URL,
) -> dict[str, Any]:
    approved_series = {
        contract.series
        for contract in FIELD_CONTRACTS.values()
        if contract.provider == "fred"
    }
    if series_id not in approved_series:
        raise ProviderAuthorizationError(
            f"FRED series is not approved: {series_id}"
        )

    api_key_present = bool(os.environ.get(api_key_env))
    return {
        "provider": "fred",
        "base_url": base_url,
        "series_id": series_id,
        "api_key_env": api_key_env,
        "api_key_present": api_key_present,
        "file_type": "json",
        "sort_order": "asc",
        "network_executed": False,
    }


def execute_provider_request(
    request_contract: Mapping[str, Any],
    *,
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    network_authorized: bool = False,
) -> Mapping[str, Any]:
    validate_network_authorization(
        network_authorized=network_authorized
    )
    response = transport(request_contract)
    if not isinstance(response, Mapping):
        raise ProviderResponseError(
            "provider transport must return a mapping"
        )
    return response


def parse_fred_observations(
    payload: Mapping[str, Any],
    *,
    series_id: str,
) -> list[dict[str, Any]]:
    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ProviderResponseError(
            f"FRED payload has no observations for {series_id}"
        )

    parsed: list[dict[str, Any]] = []
    for row in observations:
        if not isinstance(row, Mapping):
            continue

        date_value = row.get("date")
        raw_value = row.get("value")

        if not isinstance(date_value, str) or not date_value:
            continue
        if raw_value in {None, "", "."}:
            continue

        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            continue

        if not math.isfinite(number):
            continue

        parsed.append(
            {
                "date": date_value,
                "value": number,
            }
        )

    if not parsed:
        raise ProviderResponseError(
            f"FRED payload contains no usable observations for {series_id}"
        )

    parsed.sort(key=lambda item: item["date"])
    return parsed


def latest_observation(
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not observations:
        raise ProviderResponseError("observation sequence is empty")
    latest = observations[-1]
    return {
        "date": str(latest["date"]),
        "value": float(latest["value"]),
    }


def observation_at_or_before(
    observations: Sequence[Mapping[str, Any]],
    target_date: datetime,
) -> dict[str, Any]:
    eligible: list[Mapping[str, Any]] = []
    target_day = target_date.date().isoformat()

    for item in observations:
        date_value = str(item["date"])
        if date_value <= target_day:
            eligible.append(item)

    if not eligible:
        raise ProviderResponseError(
            f"no observation exists at or before {target_day}"
        )

    selected = eligible[-1]
    return {
        "date": str(selected["date"]),
        "value": float(selected["value"]),
    }


def percent_change(current: float, previous: float) -> float:
    if previous == 0:
        raise ProviderResponseError(
            "percent change denominator must not be zero"
        )
    return ((current / previous) - 1.0) * 100.0


def derive_cpi_yoy(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[float, dict[str, Any]]:
    latest = latest_observation(observations)
    latest_date = datetime.fromisoformat(latest["date"]).replace(
        tzinfo=timezone.utc
    )
    prior = observation_at_or_before(
        observations,
        latest_date - timedelta(days=350),
    )

    value = percent_change(latest["value"], prior["value"])
    value = finite_number(
        value,
        field="inflation.cpi_yoy",
        minimum=FIELD_CONTRACTS["inflation.cpi_yoy"].minimum,
        maximum=FIELD_CONTRACTS["inflation.cpi_yoy"].maximum,
    )

    return round(value, 6), {
        "latest": latest,
        "comparison": prior,
        "method": "year_over_year_percent_change",
    }


def derive_inflation_trend_3m(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[float, dict[str, Any]]:
    latest = latest_observation(observations)
    latest_date = datetime.fromisoformat(latest["date"]).replace(
        tzinfo=timezone.utc
    )

    current_yoy, current_meta = derive_cpi_yoy(observations)

    three_month_anchor = observation_at_or_before(
        observations,
        latest_date - timedelta(days=80),
    )
    anchor_date = datetime.fromisoformat(
        three_month_anchor["date"]
    ).replace(tzinfo=timezone.utc)

    anchor_prior = observation_at_or_before(
        observations,
        anchor_date - timedelta(days=350),
    )

    anchor_yoy = percent_change(
        three_month_anchor["value"],
        anchor_prior["value"],
    )

    trend = current_yoy - anchor_yoy
    trend = finite_number(
        trend,
        field="inflation.inflation_trend_3m",
        minimum=FIELD_CONTRACTS[
            "inflation.inflation_trend_3m"
        ].minimum,
        maximum=FIELD_CONTRACTS[
            "inflation.inflation_trend_3m"
        ].maximum,
    )

    return round(trend, 6), {
        "current_yoy": current_meta,
        "three_month_anchor": three_month_anchor,
        "three_month_anchor_prior": anchor_prior,
        "three_month_anchor_yoy": round(anchor_yoy, 6),
        "method": "three_month_change_in_yoy_inflation",
    }


def derive_real_rate_fields(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, float], dict[str, Any]]:
    latest = latest_observation(observations)
    latest_date = datetime.fromisoformat(latest["date"]).replace(
        tzinfo=timezone.utc
    )
    prior = observation_at_or_before(
        observations,
        latest_date - timedelta(days=28),
    )

    level = finite_number(
        latest["value"],
        field="real_rates.us_10y_real",
        minimum=FIELD_CONTRACTS[
            "real_rates.us_10y_real"
        ].minimum,
        maximum=FIELD_CONTRACTS[
            "real_rates.us_10y_real"
        ].maximum,
    )

    trend = finite_number(
        latest["value"] - prior["value"],
        field="real_rates.real_rate_trend_1m",
        minimum=FIELD_CONTRACTS[
            "real_rates.real_rate_trend_1m"
        ].minimum,
        maximum=FIELD_CONTRACTS[
            "real_rates.real_rate_trend_1m"
        ].maximum,
    )

    return {
        "us_10y_real": round(level, 6),
        "real_rate_trend_1m": round(trend, 6),
    }, {
        "latest": latest,
        "comparison": prior,
        "method": (
            "latest_level_and_latest_minus_observation_"
            "approximately_one_month_prior"
        ),
    }


def derive_usd_fields(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, float], dict[str, Any]]:
    latest = latest_observation(observations)
    latest_date = datetime.fromisoformat(latest["date"]).replace(
        tzinfo=timezone.utc
    )
    prior = observation_at_or_before(
        observations,
        latest_date - timedelta(days=28),
    )

    level = finite_number(
        latest["value"],
        field="usd.dxy",
        minimum=FIELD_CONTRACTS["usd.dxy"].minimum,
        maximum=FIELD_CONTRACTS["usd.dxy"].maximum,
    )

    trend = finite_number(
        percent_change(latest["value"], prior["value"]),
        field="usd.dxy_trend_1m",
        minimum=FIELD_CONTRACTS[
            "usd.dxy_trend_1m"
        ].minimum,
        maximum=FIELD_CONTRACTS[
            "usd.dxy_trend_1m"
        ].maximum,
    )

    return {
        "dxy": round(level, 6),
        "dxy_trend_1m": round(trend, 6),
    }, {
        "latest": latest,
        "comparison": prior,
        "method": "broad_trade_weighted_usd_proxy_and_one_month_change",
        "semantic_qualification": FIELD_CONTRACTS[
            "usd.dxy"
        ].semantic_qualification,
    }


def nfci_to_liquidity_stress(nfci: float) -> float:
    value = finite_number(
        nfci,
        field="NFCI",
        minimum=-10.0,
        maximum=10.0,
    )
    return bounded_score(0.5 + value / 4.0)


def derive_central_bank_credibility_score(
    *,
    inflation_gap_abs: float,
    inflation_acceleration_abs: float,
    real_rate_instability_abs: float,
) -> tuple[float, dict[str, Any]]:
    gap = finite_number(
        inflation_gap_abs,
        field="inflation_gap_abs",
        minimum=0.0,
        maximum=30.0,
    )
    acceleration = finite_number(
        inflation_acceleration_abs,
        field="inflation_acceleration_abs",
        minimum=0.0,
        maximum=20.0,
    )
    instability = finite_number(
        real_rate_instability_abs,
        field="real_rate_instability_abs",
        minimum=0.0,
        maximum=20.0,
    )

    penalty = (
        min(gap / 8.0, 1.0) * 0.50
        + min(acceleration / 4.0, 1.0) * 0.25
        + min(instability / 4.0, 1.0) * 0.25
    )
    score = bounded_score(1.0 - penalty)

    return score, {
        "method": "central_bank_credibility_composite_v1",
        "components": {
            "inflation_gap_abs": gap,
            "inflation_acceleration_abs": acceleration,
            "real_rate_instability_abs": instability,
        },
        "weights": {
            "inflation_gap": 0.50,
            "inflation_acceleration": 0.25,
            "real_rate_instability": 0.25,
        },
    }


def derive_systemic_stress_score(
    *,
    liquidity_stress: float,
    banking_stress: float,
    market_stress: float,
) -> tuple[float, dict[str, Any]]:
    liquidity = finite_number(
        liquidity_stress,
        field="liquidity_stress",
        minimum=0.0,
        maximum=1.0,
    )
    banking = finite_number(
        banking_stress,
        field="banking_stress",
        minimum=0.0,
        maximum=1.0,
    )
    market = finite_number(
        market_stress,
        field="market_stress",
        minimum=0.0,
        maximum=1.0,
    )

    score = bounded_score(
        liquidity * 0.35
        + banking * 0.35
        + market * 0.30
    )

    return score, {
        "method": "systemic_stress_composite_v1",
        "components": {
            "liquidity_stress": liquidity,
            "banking_stress": banking,
            "market_stress": market,
        },
        "weights": {
            "liquidity_stress": 0.35,
            "banking_stress": 0.35,
            "market_stress": 0.30,
        },
    }


def derive_banking_stress_score(
    *,
    bank_equity_drawdown: float,
    bank_credit_spread_stress: float,
    deposit_stress: float,
) -> tuple[float, dict[str, Any]]:
    equity = finite_number(
        bank_equity_drawdown,
        field="bank_equity_drawdown",
        minimum=0.0,
        maximum=1.0,
    )
    credit = finite_number(
        bank_credit_spread_stress,
        field="bank_credit_spread_stress",
        minimum=0.0,
        maximum=1.0,
    )
    deposits = finite_number(
        deposit_stress,
        field="deposit_stress",
        minimum=0.0,
        maximum=1.0,
    )

    score = bounded_score(
        equity * 0.35
        + credit * 0.40
        + deposits * 0.25
    )

    return score, {
        "method": "banking_stress_composite_v1",
        "components": {
            "bank_equity_drawdown": equity,
            "bank_credit_spread_stress": credit,
            "deposit_stress": deposits,
        },
        "weights": {
            "bank_equity_drawdown": 0.35,
            "bank_credit_spread_stress": 0.40,
            "deposit_stress": 0.25,
        },
    }


def make_provenance_entry(
    *,
    field: str,
    provider: str,
    series: str,
    observed_at: str,
    retrieved_at: str,
    source_url: str,
    source_value: Any,
    transformation: str,
    semantic_qualification: str | None = None,
    components: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if field not in FIELD_CONTRACTS:
        raise ProvenanceValidationError(
            f"unknown macro field: {field}"
        )

    contract = FIELD_CONTRACTS[field]

    if provider != contract.provider:
        raise ProvenanceValidationError(
            f"unexpected provider for {field}: {provider}"
        )
    if series != contract.series:
        raise ProvenanceValidationError(
            f"unexpected series for {field}: {series}"
        )

    parse_timestamp(observed_at)
    parse_timestamp(retrieved_at)

    if not isinstance(source_url, str) or not source_url:
        raise ProvenanceValidationError(
            f"source URL is missing for {field}"
        )
    if not isinstance(transformation, str) or not transformation:
        raise ProvenanceValidationError(
            f"transformation is missing for {field}"
        )

    return {
        "field": field,
        "provider": provider,
        "series": series,
        "unit": contract.unit,
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "source_url": source_url,
        "source_value": source_value,
        "transformation": transformation,
        "semantic_qualification": (
            semantic_qualification
            if semantic_qualification is not None
            else contract.semantic_qualification
        ),
        "components": dict(components or {}),
        "max_age_days": contract.max_age_days,
    }


def validate_provenance_entry(
    field: str,
    entry: Mapping[str, Any],
    *,
    as_of: datetime | None = None,
) -> None:
    if field not in FIELD_CONTRACTS:
        raise ProvenanceValidationError(
            f"unknown field in provenance: {field}"
        )

    contract = FIELD_CONTRACTS[field]

    if entry.get("field") != field:
        raise ProvenanceValidationError(
            f"provenance field mismatch for {field}"
        )
    if entry.get("provider") != contract.provider:
        raise ProvenanceValidationError(
            f"provider mismatch for {field}"
        )
    if entry.get("series") != contract.series:
        raise ProvenanceValidationError(
            f"series mismatch for {field}"
        )
    if entry.get("unit") != contract.unit:
        raise ProvenanceValidationError(
            f"unit mismatch for {field}"
        )

    observed_at = parse_timestamp(str(entry.get("observed_at", "")))
    retrieved_at = parse_timestamp(str(entry.get("retrieved_at", "")))

    if observed_at > retrieved_at + timedelta(minutes=5):
        raise ProvenanceValidationError(
            f"observation occurs after retrieval for {field}"
        )

    reference_time = as_of or utc_now()
    max_age = timedelta(days=contract.max_age_days)

    if reference_time - observed_at > max_age:
        raise ProvenanceValidationError(
            f"stale observation for {field}: "
            f"maximum age is {contract.max_age_days} days"
        )

    source_url = entry.get("source_url")
    if not isinstance(source_url, str) or not source_url:
        raise ProvenanceValidationError(
            f"source URL missing for {field}"
        )

    transformation = entry.get("transformation")
    if not isinstance(transformation, str) or not transformation:
        raise ProvenanceValidationError(
            f"transformation missing for {field}"
        )

    if (
        contract.semantic_qualification
        and entry.get("semantic_qualification")
        != contract.semantic_qualification
    ):
        raise ProvenanceValidationError(
            f"semantic qualification mismatch for {field}"
        )


def get_nested(payload: Mapping[str, Any], dotted_field: str) -> Any:
    current: Any = payload
    for part in dotted_field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise MacroPayloadValidationError(
                f"required macro field is missing: {dotted_field}"
            )
        current = current[part]
    return current


def validate_macro_payload(
    payload: Mapping[str, Any],
    *,
    as_of: datetime | None = None,
) -> None:
    if not isinstance(payload, Mapping):
        raise MacroPayloadValidationError(
            "macro payload must be a mapping"
        )

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise MacroPayloadValidationError(
            "macro payload schema_version is invalid"
        )

    if payload.get("status") != "valid":
        raise MacroPayloadValidationError(
            "macro payload status must be valid"
        )

    generated_at = parse_timestamp(
        str(payload.get("generated_at", ""))
    )
    reference_time = as_of or utc_now()

    if generated_at > reference_time + timedelta(minutes=5):
        raise MacroPayloadValidationError(
            "macro payload generated_at is in the future"
        )

    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise MacroPayloadValidationError(
            "macro payload source metadata is missing"
        )

    if source.get("provider_contract_version") != PROVIDER_CONTRACT_VERSION:
        raise MacroPayloadValidationError(
            "provider contract version is invalid"
        )

    if source.get("derived_metals_outputs_used") is not False:
        raise MacroPayloadValidationError(
            "derived metals outputs must not be used as primary sources"
        )

    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping):
        raise MacroPayloadValidationError(
            "macro payload provenance is missing"
        )

    for field, contract in FIELD_CONTRACTS.items():
        raw_value = get_nested(payload, field)
        finite_number(
            raw_value,
            field=field,
            minimum=contract.minimum,
            maximum=contract.maximum,
        )

        entry = provenance.get(field)
        if not isinstance(entry, Mapping):
            raise MacroPayloadValidationError(
                f"provenance is missing for {field}"
            )

        validate_provenance_entry(
            field,
            entry,
            as_of=reference_time,
        )


def atomic_write_macro_payload(
    target_path: str | Path,
    payload: Mapping[str, Any],
    *,
    provisioning_authorized: bool = False,
    as_of: datetime | None = None,
) -> None:
    validate_provisioning_authorization(
        provisioning_authorized=provisioning_authorized
    )
    validate_macro_payload(payload, as_of=as_of)

    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    previous_bytes = target.read_bytes() if target.exists() else None
    temporary_name: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary_path = Path(temporary_name)

        with temporary_path.open("r", encoding="utf-8") as handle:
            reloaded = json.load(handle)

        validate_macro_payload(reloaded, as_of=as_of)

        os.replace(temporary_path, target)
        temporary_name = None

    except Exception:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)

        if previous_bytes is not None and not target.exists():
            target.write_bytes(previous_bytes)

        raise


def provider_contract_summary() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provider_contract_version": PROVIDER_CONTRACT_VERSION,
        "production_network_calls_authorized": (
            PRODUCTION_NETWORK_CALLS_AUTHORIZED
        ),
        "macro_input_provisioning_authorized": (
            MACRO_INPUT_PROVISIONING_AUTHORIZED
        ),
        "primary_provider": PRIMARY_PROVIDER,
        "required_field_count": len(REQUIRED_FIELDS),
        "required_fields": list(REQUIRED_FIELDS),
        "field_contracts": {
            name: {
                "provider": contract.provider,
                "series": contract.series,
                "unit": contract.unit,
                "max_age_days": contract.max_age_days,
                "minimum": contract.minimum,
                "maximum": contract.maximum,
                "derivation": contract.derivation,
                "semantic_qualification": (
                    contract.semantic_qualification
                ),
            }
            for name, contract in FIELD_CONTRACTS.items()
        },
    }
