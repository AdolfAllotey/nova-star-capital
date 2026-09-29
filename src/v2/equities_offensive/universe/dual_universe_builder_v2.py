from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CorePolicy:
    min_average_dollar_volume20: float = 500_000_000.0
    # Restored from the certified historical
    # offensive_dual_universe_builder_v1 contract.
    min_relative_strength_6m: float = 40.0
    min_return60: float = -0.02
    max_atr_pct14: float = 0.06
    minimum_history_rows: int = 200


@dataclass(frozen=True)
class TacticalPolicy:
    min_average_dollar_volume20: float = 1_000_000_000.0
    min_relative_strength_6m: float = 80.0
    min_return60: float = 0.30
    max_atr_pct14: float = 0.10
    minimum_history_rows: int = 200


def percentile_ranks(
    values: Mapping[str, float],
) -> dict[str, float]:
    """
    Tie-safe percentile ranks on [0, 100].

    Equal values receive the same average rank.

    For N > 1:
        percentile = average_zero_based_rank / (N - 1) * 100

    For a singleton population, return 100 because the only
    valid member is simultaneously the strongest member.
    """
    if not values:
        return {}

    ordered = sorted(
        (
            (str(symbol).upper(), float(value))
            for symbol, value in values.items()
        ),
        key=lambda item: (item[1], item[0]),
    )

    if len(ordered) == 1:
        return {ordered[0][0]: 100.0}

    denominator = len(ordered) - 1
    result: dict[str, float] = {}

    index = 0

    while index < len(ordered):
        end = index

        while (
            end + 1 < len(ordered)
            and ordered[end + 1][1] == ordered[index][1]
        ):
            end += 1

        average_rank = (index + end) / 2.0
        percentile = round(
            average_rank / denominator * 100.0,
            2,
        )

        for position in range(index, end + 1):
            symbol = ordered[position][0]
            result[symbol] = percentile

        index = end + 1

    return result


def derive_metrics(
    provider_symbols: Mapping[str, Any],
    *,
    expected_symbols: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Derive universe-selection metrics from a certified provider
    artifact. Missing economic inputs remain missing; they are
    never coerced to zero.

    Relative strength is cross-sectional. When expected_symbols
    is supplied, the provider population must match it exactly
    and every expected member must be available with a valid
    return126 before percentile ranks are computed.
    """
    normalized_provider_symbols = {
        str(symbol).strip().upper()
        for symbol in provider_symbols
        if str(symbol).strip()
    }

    normalized_expected = (
        {
            str(symbol).strip().upper()
            for symbol in expected_symbols
            if str(symbol).strip()
        }
        if expected_symbols is not None
        else None
    )

    if normalized_expected is not None:
        missing = normalized_expected - normalized_provider_symbols
        unexpected = normalized_provider_symbols - normalized_expected

        if missing or unexpected:
            raise RuntimeError(
                "RS population mismatch: "
                f"missing={sorted(missing)}, "
                f"unexpected={sorted(unexpected)}"
            )

    valid_return126: dict[str, float] = {}

    for raw_symbol, raw_row in provider_symbols.items():
        symbol = str(raw_symbol).strip().upper()

        if not symbol or not isinstance(raw_row, Mapping):
            continue

        if raw_row.get("available") is not True:
            continue

        value = raw_row.get("return126")

        if isinstance(value, (int, float)):
            valid_return126[symbol] = float(value)

    if normalized_expected is not None:
        missing_rs_inputs = (
            normalized_expected
            - set(valid_return126)
        )

        if missing_rs_inputs:
            raise RuntimeError(
                "Incomplete RS inputs: "
                + ", ".join(sorted(missing_rs_inputs))
            )

    relative_strength = percentile_ranks(
        valid_return126
    )

    metrics: dict[str, dict[str, Any]] = {}

    for raw_symbol, raw_row in provider_symbols.items():
        symbol = str(raw_symbol).strip().upper()

        if not symbol or not isinstance(raw_row, Mapping):
            continue

        if raw_row.get("available") is not True:
            continue

        close = raw_row.get("close")
        atr14 = raw_row.get("atr14")

        atr_pct14 = None

        if (
            isinstance(close, (int, float))
            and float(close) > 0.0
            and isinstance(atr14, (int, float))
        ):
            atr_pct14 = float(atr14) / float(close)

        metrics[symbol] = {
            "close": raw_row.get("close"),
            "average_dollar_volume20": (
                raw_row.get("average_dollar_volume20")
            ),
            "relative_strength_6m": (
                relative_strength.get(symbol)
            ),
            "return20": raw_row.get("return20"),
            "return60": raw_row.get("return60"),
            "return126": raw_row.get("return126"),
            "atr14": raw_row.get("atr14"),
            "atr_pct14": atr_pct14,
            "history_rows": raw_row.get("history_rows"),
            "last_session_date": (
                raw_row.get("last_session_date")
            ),
            "source": raw_row.get("provider"),
        }

    return metrics


def _passes_policy(
    metric: Mapping[str, Any],
    policy: CorePolicy | TacticalPolicy,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    adv = metric.get("average_dollar_volume20")
    rs = metric.get("relative_strength_6m")
    ret60 = metric.get("return60")
    atr_pct = metric.get("atr_pct14")
    rows = metric.get("history_rows")

    if not isinstance(rows, int):
        reasons.append("missing_history_rows")
    elif rows < policy.minimum_history_rows:
        reasons.append("insufficient_history")

    if not isinstance(adv, (int, float)):
        reasons.append("missing_average_dollar_volume20")
    elif adv < policy.min_average_dollar_volume20:
        reasons.append("low_dollar_volume")

    if not isinstance(rs, (int, float)):
        reasons.append("missing_relative_strength_6m")
    elif rs < policy.min_relative_strength_6m:
        reasons.append("weak_relative_strength")

    if not isinstance(ret60, (int, float)):
        reasons.append("missing_return60")
    elif ret60 < policy.min_return60:
        reasons.append("weak_60d_return")

    if not isinstance(atr_pct, (int, float)):
        reasons.append("missing_atr_pct14")
    elif atr_pct > policy.max_atr_pct14:
        reasons.append("excessive_volatility")

    return not reasons, reasons


def select_dual_universe(
    metrics: Mapping[str, Mapping[str, Any]],
    *,
    core_policy: CorePolicy | None = None,
    tactical_policy: TacticalPolicy | None = None,
) -> dict[str, Any]:
    """
    Produce disjoint Core and Tactical selections.

    Core has precedence. Tactical is evaluated only for symbols
    that did not qualify for Core.

    This preserves the voting invariant:
        Core ∩ Tactical == empty set.
    """
    core_policy = core_policy or CorePolicy()
    tactical_policy = tactical_policy or TacticalPolicy()

    core: list[str] = []
    tactical: list[str] = []
    rejected: dict[str, dict[str, list[str]]] = {}

    for symbol in sorted(metrics):
        metric = metrics[symbol]

        core_ok, core_reasons = _passes_policy(
            metric,
            core_policy,
        )

        if core_ok:
            core.append(symbol)
            continue

        tactical_ok, tactical_reasons = _passes_policy(
            metric,
            tactical_policy,
        )

        if tactical_ok:
            tactical.append(symbol)
            continue

        rejected[symbol] = {
            "core_reasons": core_reasons,
            "tactical_reasons": tactical_reasons,
        }

    overlap = set(core) & set(tactical)

    if overlap:
        raise RuntimeError(
            "Core/Tactical overlap detected: "
            + ", ".join(sorted(overlap))
        )

    return {
        "core": core,
        "tactical": tactical,
        "rejected": rejected,
    }
