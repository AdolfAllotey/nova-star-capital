from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class PriceDataUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class PriceSnapshot:
    sleeve: str
    prices: dict[str, float]
    updated_at: datetime
    age_seconds: float
    engine: str
    status: str


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PriceDataUnavailableError(
            f"unable to read {path}: {type(exc).__name__}"
        ) from exc


def load_fresh_prices(
    *,
    sleeve: str,
    prices_path: Path,
    expected_symbols: Iterable[str],
    max_age_seconds: int,
    now: datetime | None = None,
) -> PriceSnapshot:
    meta_path = prices_path.with_name("prices_meta.json")

    if not prices_path.exists():
        raise PriceDataUnavailableError(
            f"{sleeve}: prices file missing"
        )

    if not meta_path.exists():
        raise PriceDataUnavailableError(
            f"{sleeve}: prices metadata missing"
        )

    prices = _load_json(prices_path)
    meta = _load_json(meta_path)

    if not isinstance(prices, dict):
        raise PriceDataUnavailableError(
            f"{sleeve}: invalid prices payload"
        )

    if not isinstance(meta, dict):
        raise PriceDataUnavailableError(
            f"{sleeve}: invalid prices metadata"
        )

    status = str(meta.get("status") or "")
    if status != "ok":
        raise PriceDataUnavailableError(
            f"{sleeve}: provider status={status or 'missing'}"
        )

    updated_raw = meta.get("updated_at")
    if not updated_raw:
        raise PriceDataUnavailableError(
            f"{sleeve}: updated_at missing"
        )

    try:
        updated_at = datetime.fromisoformat(
            str(updated_raw).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise PriceDataUnavailableError(
            f"{sleeve}: invalid updated_at"
        ) from exc

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    reference = now or datetime.now(timezone.utc)
    age_seconds = (reference - updated_at).total_seconds()

    if age_seconds < 0:
        raise PriceDataUnavailableError(
            f"{sleeve}: price snapshot timestamp is in the future"
        )

    if age_seconds > max_age_seconds:
        raise PriceDataUnavailableError(
            f"{sleeve}: stale prices age={age_seconds:.0f}s "
            f"max={max_age_seconds}s"
        )

    expected = set(expected_symbols)
    available = {
        str(symbol)
        for symbol, value in prices.items()
        if isinstance(value, (int, float)) and value > 0
    }

    missing = sorted(expected - available)
    if missing:
        raise PriceDataUnavailableError(
            f"{sleeve}: missing prices={','.join(missing)}"
        )

    normalized = {
        str(symbol): float(value)
        for symbol, value in prices.items()
        if isinstance(value, (int, float)) and value > 0
    }

    return PriceSnapshot(
        sleeve=sleeve,
        prices=normalized,
        updated_at=updated_at,
        age_seconds=age_seconds,
        engine=str(meta.get("engine") or ""),
        status=status,
    )
