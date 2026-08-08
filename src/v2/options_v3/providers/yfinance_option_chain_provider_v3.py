from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import math
import os
import tempfile

import yfinance as yf


PROVIDER_NAME = "yfinance"
PROVIDER_VERSION = "v3"

DEFAULT_CACHE_DIR = Path(
    "/opt/nsc/data/preprod/options_v3/option_chain_cache"
)

DEFAULT_CACHE_MAX_AGE_MINUTES = 60
DEFAULT_MINIMUM_DTE = 7
DEFAULT_MAXIMUM_DTE = 90

DEFAULT_MINIMUM_OPEN_INTEREST = 10
DEFAULT_MINIMUM_VOLUME = 1
DEFAULT_MAXIMUM_ABSOLUTE_SPREAD_USD = 5.0
DEFAULT_MAXIMUM_RELATIVE_SPREAD = 0.50


class OptionChainProviderError(RuntimeError):
    """Base fail-closed provider exception."""


class OptionChainUnavailableError(OptionChainProviderError):
    """Raised when no usable provider response or fresh cache exists."""


class OptionChainValidationError(OptionChainProviderError):
    """Raised when provider data does not satisfy the contract."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    return current.astimezone(timezone.utc).isoformat()


def finite_float(
    value: Any,
    *,
    field: str,
    allow_zero: bool = True,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OptionChainValidationError(
            f"{field}: invalid numeric value"
        ) from exc

    if not math.isfinite(result):
        raise OptionChainValidationError(
            f"{field}: non-finite numeric value"
        )

    if allow_zero:
        if result < 0:
            raise OptionChainValidationError(
                f"{field}: negative value forbidden"
            )
    elif result <= 0:
        raise OptionChainValidationError(
            f"{field}: positive value required"
        )

    return result


def optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def parse_expiration(value: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise OptionChainValidationError(
            f"expiration: invalid ISO date {value!r}"
        ) from exc


def days_to_expiry(
    expiration: str,
    *,
    valuation_date: date | None = None,
) -> int:
    base_date = valuation_date or utc_now().date()
    expiry_date = parse_expiration(expiration)
    return (expiry_date - base_date).days


def select_expiration(
    expirations: Iterable[str],
    *,
    target_dte: int,
    minimum_dte: int = DEFAULT_MINIMUM_DTE,
    maximum_dte: int = DEFAULT_MAXIMUM_DTE,
    valuation_date: date | None = None,
) -> str:
    if target_dte <= 0:
        raise OptionChainValidationError(
            "target_dte: positive integer required"
        )

    candidates: list[tuple[int, str]] = []

    for expiration in expirations:
        try:
            dte = days_to_expiry(
                expiration,
                valuation_date=valuation_date,
            )
        except OptionChainValidationError:
            continue

        if minimum_dte <= dte <= maximum_dte:
            candidates.append((dte, str(expiration)))

    if not candidates:
        raise OptionChainUnavailableError(
            "no expiration satisfies the configured DTE window"
        )

    candidates.sort(
        key=lambda item: (
            abs(item[0] - target_dte),
            item[0],
            item[1],
        )
    )

    return candidates[0][1]


def derive_mid_and_spread(
    *,
    bid: Any,
    ask: Any,
) -> dict[str, float]:
    bid_value = finite_float(
        bid,
        field="bid",
        allow_zero=True,
    )
    ask_value = finite_float(
        ask,
        field="ask",
        allow_zero=False,
    )

    if ask_value < bid_value:
        raise OptionChainValidationError(
            "ask: lower than bid"
        )

    if bid_value == 0:
        raise OptionChainValidationError(
            "bid: zero-bid contracts are forbidden"
        )

    mid = (bid_value + ask_value) / 2.0

    if mid <= 0:
        raise OptionChainValidationError(
            "mid: positive value required"
        )

    absolute_spread = ask_value - bid_value
    relative_spread = absolute_spread / mid

    return {
        "bid": round(bid_value, 8),
        "ask": round(ask_value, 8),
        "mid": round(mid, 8),
        "absolute_spread": round(
            absolute_spread,
            8,
        ),
        "relative_spread": round(
            relative_spread,
            8,
        ),
    }


def normalize_contract(
    row: dict[str, Any],
    *,
    ticker: str,
    expiration: str,
    option_type: str,
    underlying_price: float,
    provider_timestamp: str,
    valuation_date: date | None = None,
) -> dict[str, Any]:
    normalized_type = str(option_type).upper()

    if normalized_type not in {"CALL", "PUT"}:
        raise OptionChainValidationError(
            f"option_type: unsupported value {option_type!r}"
        )

    contract_symbol = str(
        row.get("contractSymbol") or ""
    ).strip()

    if not contract_symbol:
        raise OptionChainValidationError(
            "contract_symbol: required"
        )

    dte = days_to_expiry(
        expiration,
        valuation_date=valuation_date,
    )

    if dte <= 0:
        raise OptionChainValidationError(
            "expiration: expired or same-day contract forbidden"
        )

    strike = finite_float(
        row.get("strike"),
        field="strike",
        allow_zero=False,
    )

    implied_volatility = finite_float(
        row.get("impliedVolatility"),
        field="implied_volatility",
        allow_zero=False,
    )

    spread = derive_mid_and_spread(
        bid=row.get("bid"),
        ask=row.get("ask"),
    )

    contract_size = str(
        row.get("contractSize") or ""
    ).upper()

    if contract_size != "REGULAR":
        raise OptionChainValidationError(
            "contract_size: only REGULAR contracts are accepted"
        )

    currency = str(
        row.get("currency") or ""
    ).upper()

    if currency != "USD":
        raise OptionChainValidationError(
            "currency: only USD contracts are accepted"
        )

    return {
        "ticker": str(ticker).upper(),
        "provider": PROVIDER_NAME,
        "provider_version": PROVIDER_VERSION,
        "provider_timestamp": provider_timestamp,
        "expiration": expiration,
        "days_to_expiry": dte,
        "option_type": normalized_type,
        "contract_symbol": contract_symbol,
        "strike": round(strike, 8),
        **spread,
        "last_price": optional_finite_float(
            row.get("lastPrice")
        ),
        "implied_volatility": round(
            implied_volatility,
            10,
        ),
        "volume": optional_finite_float(
            row.get("volume")
        ),
        "open_interest": optional_finite_float(
            row.get("openInterest")
        ),
        "in_the_money": bool(
            row.get("inTheMoney")
        ),
        "contract_size": contract_size,
        "currency": currency,
        "underlying_price": round(
            finite_float(
                underlying_price,
                field="underlying_price",
                allow_zero=False,
            ),
            8,
        ),
        "last_trade_date": (
            str(row.get("lastTradeDate"))
            if row.get("lastTradeDate") is not None
            else None
        ),
    }


def passes_liquidity_gate(
    contract: dict[str, Any],
    *,
    minimum_open_interest: int = DEFAULT_MINIMUM_OPEN_INTEREST,
    minimum_volume: int = DEFAULT_MINIMUM_VOLUME,
    maximum_absolute_spread_usd: float = (
        DEFAULT_MAXIMUM_ABSOLUTE_SPREAD_USD
    ),
    maximum_relative_spread: float = (
        DEFAULT_MAXIMUM_RELATIVE_SPREAD
    ),
    allow_zero_volume_when_open_interest_sufficient: bool = True,
) -> tuple[bool, str]:
    open_interest = optional_finite_float(
        contract.get("open_interest")
    )
    volume = optional_finite_float(
        contract.get("volume")
    )

    absolute_spread = finite_float(
        contract.get("absolute_spread"),
        field="absolute_spread",
        allow_zero=True,
    )

    relative_spread = finite_float(
        contract.get("relative_spread"),
        field="relative_spread",
        allow_zero=True,
    )

    if open_interest is None:
        open_interest = 0.0

    if volume is None:
        volume = 0.0

    if open_interest < minimum_open_interest:
        return False, "open_interest_below_minimum"

    if volume < minimum_volume:
        if not (
            allow_zero_volume_when_open_interest_sufficient
            and open_interest >= minimum_open_interest
        ):
            return False, "volume_below_minimum"

    if absolute_spread > maximum_absolute_spread_usd:
        return False, "absolute_spread_above_maximum"

    if relative_spread > maximum_relative_spread:
        return False, "relative_spread_above_maximum"

    return True, "PASS"


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def payload_sha256(payload: Any) -> str:
    return sha256(
        canonical_json_bytes(payload)
    ).hexdigest()


def cache_path_for(
    ticker: str,
    expiration: str,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    safe_ticker = str(ticker).upper().replace(
        "/", "_"
    )
    safe_expiration = str(expiration).replace(
        "/", "_"
    )

    return (
        cache_dir
        / safe_ticker
        / f"{safe_expiration}.json"
    )


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        finally:
            raise


def load_fresh_cache(
    path: Path,
    *,
    maximum_age_minutes: int = (
        DEFAULT_CACHE_MAX_AGE_MINUTES
    ),
    now_value: datetime | None = None,
) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    metadata = payload.get("metadata")

    if not isinstance(metadata, dict):
        return None

    retrieval_timestamp = metadata.get(
        "retrieval_timestamp"
    )

    if not isinstance(
        retrieval_timestamp,
        str,
    ):
        return None

    try:
        retrieved_at = datetime.fromisoformat(
            retrieval_timestamp.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return None

    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(
            tzinfo=timezone.utc
        )

    current = now_value or utc_now()

    if current.tzinfo is None:
        current = current.replace(
            tzinfo=timezone.utc
        )

    age_minutes = (
        current.astimezone(timezone.utc)
        - retrieved_at.astimezone(timezone.utc)
    ).total_seconds() / 60.0

    if age_minutes < 0:
        return None

    if age_minutes > maximum_age_minutes:
        return None

    expected_hash = metadata.get(
        "contracts_sha256"
    )

    contracts = payload.get("contracts")

    if not isinstance(contracts, list):
        return None

    if (
        not isinstance(expected_hash, str)
        or expected_hash
        != payload_sha256(contracts)
    ):
        return None

    return payload


def underlying_price_from_ticker(
    ticker_object: Any,
) -> float:
    candidates: list[Any] = []

    try:
        fast_info = ticker_object.fast_info

        if fast_info is not None:
            candidates.extend([
                fast_info.get("last_price"),
                fast_info.get("regular_market_price"),
                fast_info.get("previous_close"),
            ])
    except Exception:
        pass

    for value in candidates:
        number = optional_finite_float(value)

        if number is not None and number > 0:
            return number

    try:
        history = ticker_object.history(
            period="5d",
            interval="1d",
            auto_adjust=False,
        )

        if (
            history is not None
            and not history.empty
            and "Close" in history.columns
        ):
            values = history["Close"].dropna()

            if not values.empty:
                number = optional_finite_float(
                    values.iloc[-1]
                )

                if (
                    number is not None
                    and number > 0
                ):
                    return number

    except Exception:
        pass

    raise OptionChainUnavailableError(
        "underlying price unavailable"
    )


def dataframe_rows(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []

    if getattr(frame, "empty", True):
        return []

    return [
        row.to_dict()
        for _, row in frame.iterrows()
    ]


def build_cache_payload(
    *,
    ticker: str,
    expiration: str,
    target_dte: int,
    underlying_price: float,
    contracts: list[dict[str, Any]],
    retrieval_timestamp: str,
) -> dict[str, Any]:
    return {
        "metadata": {
            "provider": PROVIDER_NAME,
            "provider_version": PROVIDER_VERSION,
            "ticker": str(ticker).upper(),
            "expiration": expiration,
            "target_dte": target_dte,
            "underlying_price": round(
                underlying_price,
                8,
            ),
            "retrieval_timestamp": (
                retrieval_timestamp
            ),
            "contracts_sha256": (
                payload_sha256(contracts)
            ),
            "contract_count": len(contracts),
            "read_only_market_data": True,
            "real_execution_allowed": False,
        },
        "contracts": contracts,
    }


def fetch_normalized_option_chain(
    ticker: str,
    *,
    target_dte: int,
    minimum_dte: int = DEFAULT_MINIMUM_DTE,
    maximum_dte: int = DEFAULT_MAXIMUM_DTE,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    cache_maximum_age_minutes: int = (
        DEFAULT_CACHE_MAX_AGE_MINUTES
    ),
    force_refresh: bool = False,
    ticker_factory: Callable[[str], Any] = yf.Ticker,
    valuation_datetime: datetime | None = None,
) -> dict[str, Any]:
    ticker_symbol = str(ticker).upper().strip()

    if not ticker_symbol:
        raise OptionChainValidationError(
            "ticker: required"
        )

    current = valuation_datetime or utc_now()

    if current.tzinfo is None:
        current = current.replace(
            tzinfo=timezone.utc
        )

    provider_timestamp = iso_utc(current)

    ticker_object = ticker_factory(
        ticker_symbol
    )

    try:
        expirations = list(
            ticker_object.options or []
        )
    except Exception as exc:
        raise OptionChainUnavailableError(
            f"expiration retrieval failed: {exc}"
        ) from exc

    selected_expiration = select_expiration(
        expirations,
        target_dte=target_dte,
        minimum_dte=minimum_dte,
        maximum_dte=maximum_dte,
        valuation_date=current.date(),
    )

    path = cache_path_for(
        ticker_symbol,
        selected_expiration,
        cache_dir=cache_dir,
    )

    if not force_refresh:
        cached = load_fresh_cache(
            path,
            maximum_age_minutes=(
                cache_maximum_age_minutes
            ),
            now_value=current,
        )

        if cached is not None:
            cached["metadata"][
                "cache_status"
            ] = "FRESH_CACHE"
            return cached

    try:
        chain = ticker_object.option_chain(
            selected_expiration
        )
    except Exception as exc:
        cached = load_fresh_cache(
            path,
            maximum_age_minutes=(
                cache_maximum_age_minutes
            ),
            now_value=current,
        )

        if cached is not None:
            cached["metadata"][
                "cache_status"
            ] = "FRESH_CACHE_PROVIDER_FAILURE"
            cached["metadata"][
                "provider_failure"
            ] = f"{type(exc).__name__}: {exc}"
            return cached

        raise OptionChainUnavailableError(
            f"option chain retrieval failed: {exc}"
        ) from exc

    underlying_price = (
        underlying_price_from_ticker(
            ticker_object
        )
    )

    normalized_contracts: list[
        dict[str, Any]
    ] = []

    rejected_contracts: list[
        dict[str, Any]
    ] = []

    for option_type, frame in (
        ("CALL", chain.calls),
        ("PUT", chain.puts),
    ):
        for row in dataframe_rows(frame):
            contract_symbol = row.get(
                "contractSymbol"
            )

            try:
                normalized = normalize_contract(
                    row,
                    ticker=ticker_symbol,
                    expiration=(
                        selected_expiration
                    ),
                    option_type=option_type,
                    underlying_price=(
                        underlying_price
                    ),
                    provider_timestamp=(
                        provider_timestamp
                    ),
                    valuation_date=(
                        current.date()
                    ),
                )

                liquid, reason = (
                    passes_liquidity_gate(
                        normalized
                    )
                )

                if not liquid:
                    rejected_contracts.append({
                        "contract_symbol": (
                            contract_symbol
                        ),
                        "option_type": (
                            option_type
                        ),
                        "reason": reason,
                    })
                    continue

                normalized_contracts.append(
                    normalized
                )

            except OptionChainValidationError as exc:
                rejected_contracts.append({
                    "contract_symbol": (
                        contract_symbol
                    ),
                    "option_type": (
                        option_type
                    ),
                    "reason": str(exc),
                })

    if not normalized_contracts:
        raise OptionChainUnavailableError(
            "no contract passed validation and liquidity gates"
        )

    normalized_contracts.sort(
        key=lambda item: (
            item["option_type"],
            item["strike"],
            item["contract_symbol"],
        )
    )

    payload = build_cache_payload(
        ticker=ticker_symbol,
        expiration=selected_expiration,
        target_dte=target_dte,
        underlying_price=underlying_price,
        contracts=normalized_contracts,
        retrieval_timestamp=provider_timestamp,
    )

    payload["metadata"][
        "cache_status"
    ] = "LIVE_PROVIDER"

    payload["metadata"][
        "rejected_contract_count"
    ] = len(rejected_contracts)

    payload["rejections"] = (
        rejected_contracts
    )

    atomic_write_json(
        path,
        payload,
    )

    return payload


__all__ = [
    "OptionChainProviderError",
    "OptionChainUnavailableError",
    "OptionChainValidationError",
    "atomic_write_json",
    "build_cache_payload",
    "cache_path_for",
    "days_to_expiry",
    "derive_mid_and_spread",
    "fetch_normalized_option_chain",
    "load_fresh_cache",
    "normalize_contract",
    "passes_liquidity_gate",
    "payload_sha256",
    "select_expiration",
]
