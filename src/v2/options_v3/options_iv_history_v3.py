import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from providers.yfinance_option_chain_provider_v3 import (
    fetch_normalized_option_chain,
)

from src.v2.equities_offensive.ops.us_market_session import (
    build_with_exchange_calendars,
)


IV_HISTORY_VERSION = "3.0.0"
IV_OBSERVATION_TARGET_DTE = 30
IV_MINIMUM_DTE = 7
IV_MAXIMUM_DTE = 90
IV_CACHE_MAXIMUM_AGE_MINUTES = 60

IV_PROVISIONAL_MIN_OBSERVATIONS = 20
IV_AVAILABLE_MIN_OBSERVATIONS = 60


class IVObservationError(RuntimeError):
    """Fail-closed error for canonical IV observation."""


def require_open_us_market_session_v3(
    now_value=None,
):
    current = (
        now_value
        if now_value is not None
        else datetime.now(timezone.utc)
    )

    if current.tzinfo is None:
        current = current.replace(
            tzinfo=timezone.utc
        )

    session = build_with_exchange_calendars(
        current
    )

    if not isinstance(session, dict):
        raise IVObservationError(
            "market_session_unavailable"
        )

    if session.get("quality") != "authoritative":
        raise IVObservationError(
            "market_session_not_authoritative"
        )

    if session.get("fallback") is not False:
        raise IVObservationError(
            "market_session_fallback_forbidden"
        )

    if session.get("is_open") is not True:
        raise IVObservationError(
            "market_session_closed"
        )

    return session


def _iso_utc():
    return datetime.now(timezone.utc).isoformat()


def _finite_positive(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise IVObservationError(
            f"{field}: invalid numeric value"
        ) from exc

    if not math.isfinite(number) or number <= 0:
        raise IVObservationError(
            f"{field}: positive finite value required"
        )

    return number


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_name, path)

    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _load_history(path):
    path = Path(path)

    if not path.exists():
        return {
            "version": IV_HISTORY_VERSION,
            "generated_at": None,
            "tickers": {},
        }

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise IVObservationError(
            f"history_parse_failure:{type(exc).__name__}:{exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise IVObservationError(
            "history_root_not_dictionary"
        )

    tickers = payload.get("tickers")

    if tickers is None:
        payload["tickers"] = {}
    elif not isinstance(tickers, dict):
        raise IVObservationError(
            "history_tickers_not_dictionary"
        )

    return payload


def _nearest_contract(contracts, option_type, spot):
    eligible = []

    for contract in contracts:
        if not isinstance(contract, dict):
            continue

        if str(
            contract.get("option_type") or ""
        ).upper() != option_type:
            continue

        try:
            strike = _finite_positive(
                contract.get("strike"),
                "strike",
            )
            iv = _finite_positive(
                contract.get("implied_volatility"),
                "implied_volatility",
            )
        except IVObservationError:
            continue

        eligible.append(
            (
                abs(strike - spot),
                strike,
                iv,
                contract,
            )
        )

    if not eligible:
        raise IVObservationError(
            f"no_valid_{option_type.lower()}_contract"
        )

    eligible.sort(
        key=lambda row: (
            row[0],
            row[1],
        )
    )

    return eligible[0]


def derive_canonical_iv_observation(
    ticker,
    *,
    cache_dir,
    valuation_datetime=None,
):
    ticker_symbol = str(
        ticker or ""
    ).strip().upper()

    if not ticker_symbol:
        raise IVObservationError("missing_ticker")

    current = (
        valuation_datetime
        if valuation_datetime is not None
        else datetime.now(timezone.utc)
    )

    require_open_us_market_session_v3(
        current
    )

    payload = fetch_normalized_option_chain(
        ticker_symbol,
        target_dte=IV_OBSERVATION_TARGET_DTE,
        minimum_dte=IV_MINIMUM_DTE,
        maximum_dte=IV_MAXIMUM_DTE,
        cache_dir=cache_dir,
        cache_maximum_age_minutes=(
            IV_CACHE_MAXIMUM_AGE_MINUTES
        ),
        force_refresh=False,
        valuation_datetime=current,
    )

    if not isinstance(payload, dict):
        raise IVObservationError(
            "provider_payload_not_dictionary"
        )

    metadata = payload.get("metadata")
    contracts = payload.get("contracts")

    if not isinstance(metadata, dict):
        raise IVObservationError(
            "provider_metadata_not_dictionary"
        )

    if not isinstance(contracts, list) or not contracts:
        raise IVObservationError(
            "provider_contracts_unavailable"
        )

    spot = _finite_positive(
        metadata.get("underlying_price"),
        "underlying_price",
    )

    call = _nearest_contract(
        contracts,
        "CALL",
        spot,
    )
    put = _nearest_contract(
        contracts,
        "PUT",
        spot,
    )

    call_distance, call_strike, call_iv, call_contract = call
    put_distance, put_strike, put_iv, put_contract = put

    representative_iv = (
        call_iv + put_iv
    ) / 2.0

    provider_timestamp = (
        metadata.get("retrieval_timestamp")
        or metadata.get("provider_timestamp")
        or _iso_utc()
    )

    expiration = (
        metadata.get("expiration")
        or call_contract.get("expiration")
        or put_contract.get("expiration")
    )

    actual_dte = (
        call_contract.get("days_to_expiry")
        or put_contract.get("days_to_expiry")
    )

    observation_date = str(
        provider_timestamp
    )[:10]

    return {
        "ticker": ticker_symbol,
        "observation_date": observation_date,
        "observed_at": _iso_utc(),
        "provider": metadata.get("provider"),
        "provider_version": metadata.get(
            "provider_version"
        ),
        "provider_timestamp": provider_timestamp,
        "cache_status": metadata.get(
            "cache_status"
        ),
        "target_dte": IV_OBSERVATION_TARGET_DTE,
        "expiration": expiration,
        "actual_dte": actual_dte,
        "underlying_price": round(spot, 8),
        "call_strike": round(call_strike, 8),
        "put_strike": round(put_strike, 8),
        "call_distance_to_spot": round(
            call_distance,
            8,
        ),
        "put_distance_to_spot": round(
            put_distance,
            8,
        ),
        "call_iv": round(call_iv, 10),
        "put_iv": round(put_iv, 10),
        "representative_iv": round(
            representative_iv,
            10,
        ),
        "method": (
            "mean_nearest_liquid_call_put_iv_"
            "target_30dte"
        ),
        "provenance_status": (
            "CERTIFIED_PROVIDER_BACKED_OBSERVATION"
        ),
    }


def _metrics(observations):
    values = []

    for item in observations:
        if not isinstance(item, dict):
            continue

        try:
            value = _finite_positive(
                item.get("representative_iv"),
                "representative_iv",
            )
        except IVObservationError:
            continue

        values.append(value)

    count = len(values)

    result = {
        "observation_count": count,
        "iv_rank": None,
        "iv_percentile": None,
        "iv_rank_status": "WARMING_UP",
        "iv_percentile_status": "WARMING_UP",
    }

    if count == 0:
        return result

    current = values[-1]
    minimum = min(values)
    maximum = max(values)

    result.update({
        "current_iv": round(current, 10),
        "observed_min_iv": round(
            minimum,
            10,
        ),
        "observed_max_iv": round(
            maximum,
            10,
        ),
    })

    if count < IV_PROVISIONAL_MIN_OBSERVATIONS:
        return result

    if maximum == minimum:
        rank = 50.0
    else:
        rank = (
            (current - minimum)
            / (maximum - minimum)
            * 100.0
        )

    percentile = (
        sum(
            1
            for value in values
            if value <= current
        )
        / count
        * 100.0
    )

    if count < IV_AVAILABLE_MIN_OBSERVATIONS:
        status = "PROVISIONAL"
    else:
        status = "AVAILABLE"

    result.update({
        "iv_rank": round(rank, 4),
        "iv_percentile": round(
            percentile,
            4,
        ),
        "iv_rank_status": status,
        "iv_percentile_status": status,
    })

    return result


def observe_and_update_iv_history(
    ticker,
    *,
    history_path,
    cache_dir,
):
    observation = derive_canonical_iv_observation(
        ticker,
        cache_dir=cache_dir,
    )

    history = _load_history(history_path)

    ticker_symbol = observation["ticker"]

    ticker_payload = history[
        "tickers"
    ].setdefault(
        ticker_symbol,
        {
            "observations": [],
        },
    )

    observations = ticker_payload.get(
        "observations"
    )

    if not isinstance(observations, list):
        raise IVObservationError(
            "ticker_observations_not_list"
        )

    observation_date = observation[
        "observation_date"
    ]

    existing_index = None

    for index, item in enumerate(observations):
        if (
            isinstance(item, dict)
            and item.get("observation_date")
            == observation_date
        ):
            existing_index = index
            break

    if existing_index is None:
        observations.append(observation)
    else:
        observations[
            existing_index
        ] = observation

    observations.sort(
        key=lambda item: (
            str(item.get("observation_date") or ""),
            str(item.get("observed_at") or ""),
        )
    )

    metrics = _metrics(observations)

    ticker_payload.update({
        "observations": observations,
        "metrics": metrics,
        "last_observation": observation,
    })

    history.update({
        "version": IV_HISTORY_VERSION,
        "generated_at": _iso_utc(),
    })

    _atomic_write_json(
        history_path,
        history,
    )

    return {
        **metrics,
        "iv_provenance_status": (
            "CERTIFIED_PROVIDER_BACKED_HISTORY"
        ),
        "last_observation": observation,
    }


__all__ = [
    "IVObservationError",
    "observe_and_update_iv_history",
]
