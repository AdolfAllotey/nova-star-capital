from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import FXRate
from .validator import normalize_currency, validate_rate


class FXProviderError(RuntimeError):
    pass


def utc_iso_from_epoch(value: int) -> str:
    return datetime.fromtimestamp(
        int(value),
        tz=timezone.utc,
    ).isoformat().replace("+00:00", "Z")


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat().replace("+00:00", "Z")


class YahooFXProvider:
    name = "yahoo_finance_chart_v1"

    def __init__(self, timeout_seconds: float | None = None):
        configured = os.getenv(
            "NSC_FX_HTTP_TIMEOUT_SEC",
            "8",
        )

        self.timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else configured
        )

    def _request_json(self, url: str) -> Dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "NovaStarCapital-CoreFX/1.0"
                ),
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                return json.loads(
                    response.read().decode("utf-8")
                )

        except Exception as exc:
            raise FXProviderError(
                f"Yahoo FX request failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    def fetch_rate(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> FXRate:
        base = normalize_currency(base_currency)
        quote_currency = normalize_currency(
            quote_currency
        )

        if base == quote_currency:
            now = utc_now_iso()

            return FXRate(
                base_currency=base,
                quote_currency=quote_currency,
                rate=1.0,
                provider="identity",
                market_timestamp=now,
                retrieved_at=now,
            )

        ticker = f"{base}{quote_currency}=X"

        url = (
            "https://query1.finance.yahoo.com/"
            f"v8/finance/chart/{quote(ticker)}"
            "?range=1d&interval=5m"
        )

        payload = self._request_json(url)

        try:
            chart = payload["chart"]
            error = chart.get("error")

            if error:
                raise FXProviderError(
                    f"Yahoo returned error for {ticker}: "
                    f"{error}"
                )

            result = chart["result"][0]
            timestamps = result.get("timestamp") or []
            closes = (
                result.get("indicators", {})
                .get("quote", [{}])[0]
                .get("close", [])
            )

            candidates = [
                (timestamp, close)
                for timestamp, close in zip(
                    timestamps,
                    closes,
                )
                if close is not None
                and float(close) > 0
            ]

            if not candidates:
                raise FXProviderError(
                    f"No valid FX observations for {ticker}"
                )

            market_epoch, close = candidates[-1]

            rate = FXRate(
                base_currency=base,
                quote_currency=quote_currency,
                rate=float(close),
                provider=self.name,
                market_timestamp=utc_iso_from_epoch(
                    market_epoch
                ),
                retrieved_at=utc_now_iso(),
            )

            return validate_rate(rate)

        except FXProviderError:
            raise

        except Exception as exc:
            raise FXProviderError(
                f"Invalid Yahoo payload for {ticker}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
