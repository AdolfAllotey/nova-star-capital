#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Massive / Polygon Provider V1

Provider secondaire indépendant.

Massive est le nouveau nom de Polygon.io.
La clé est recherchée dans :
- MASSIVE_API_KEY
- POLYGON_API_KEY

Aucune clé n'est journalisée.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests

from provider_base import (
    MarketDataProvider,
    ProviderSymbolResult,
    normalize_symbol,
    rounded,
    safe_float,
    utc_now_iso,
)


class MassiveProvider(MarketDataProvider):
    provider_name = "massive"
    provider_role = "secondary_validation_source"
    requires_api_key = True

    base_url = "https://api.massive.com"

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("MASSIVE_API_KEY")
            or os.getenv("POLYGON_API_KEY")
            or ""
        ).strip()

        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _compute_return(
        series: pd.Series,
        sessions: int,
    ) -> float | None:
        if len(series) <= sessions:
            return None

        current = safe_float(series.iloc[-1])
        previous = safe_float(series.iloc[-1 - sessions])

        if current is None or previous in (None, 0):
            return None

        return rounded((current / previous) - 1.0)

    @staticmethod
    def _compute_atr14(
        frame: pd.DataFrame,
    ) -> float | None:
        if len(frame) < 15:
            return None

        high = frame["High"].astype(float)
        low = frame["Low"].astype(float)
        close = frame["Close"].astype(float)
        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = true_range.rolling(
            window=14,
            min_periods=14,
        ).mean().iloc[-1]

        return rounded(atr)

    def _request(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        endpoint = (
            f"{self.base_url}/v2/aggs/ticker/"
            f"{symbol}/range/1/day/"
            f"{start_date}/{end_date}"
        )

        response = requests.get(
            endpoint,
            params={
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
                "apiKey": self.api_key,
            },
            timeout=self.timeout_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Nova-Star-Capital/"
                    "Offensive-Equities-Market-Data-V1"
                ),
            },
        )

        if response.status_code in {401, 403}:
            raise PermissionError(
                "Authentification Massive refusée."
            )

        if response.status_code == 429:
            raise RuntimeError(
                "Limite de requêtes Massive atteinte."
            )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError(
                "Réponse Massive JSON invalide."
            )

        api_status = str(
            payload.get("status", "")
        ).upper()

        if api_status not in {
            "OK",
            "DELAYED",
        }:
            error_message = (
                payload.get("error")
                or payload.get("message")
                or f"Statut Massive inattendu : "
                   f"{api_status}"
            )
            raise ValueError(str(error_message))

        return payload

    def fetch_symbol(
        self,
        symbol: str,
        history_days: int,
        minimum_history_rows: int,
    ) -> ProviderSymbolResult:
        normalized = normalize_symbol(symbol)
        fetched_at = utc_now_iso()

        if not self.is_configured():
            return ProviderSymbolResult(
                symbol=normalized,
                provider=self.provider_name,
                provider_symbol=normalized,
                status="not_configured",
                available=False,
                fetched_at=fetched_at,
                error=(
                    "MASSIVE_API_KEY ou POLYGON_API_KEY "
                    "n'est pas configurée."
                ),
            )

        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = (
                datetime.now(timezone.utc)
                - timedelta(days=max(history_days, 30))
            ).date()

            payload = self._request(
                symbol=normalized,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            rows = payload.get("results") or []

            if not rows:
                raise ValueError(
                    "Massive n'a retourné aucune barre."
                )

            frame = pd.DataFrame(rows)

            required = {
                "t",
                "o",
                "h",
                "l",
                "c",
                "v",
            }

            missing = required.difference(frame.columns)

            if missing:
                raise ValueError(
                    "Champs Massive manquants : "
                    + ", ".join(sorted(missing))
                )

            frame["Date"] = pd.to_datetime(
                frame["t"],
                unit="ms",
                utc=True,
                errors="coerce",
            )

            rename_mapping = {
                "o": "Open",
                "h": "High",
                "l": "Low",
                "c": "Close",
                "v": "Volume",
            }

            frame = frame.rename(
                columns=rename_mapping
            )

            for column in [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]:
                frame[column] = pd.to_numeric(
                    frame[column],
                    errors="coerce",
                )

            frame = frame.dropna(
                subset=[
                    "Date",
                    "Close",
                ]
            )

            frame = frame.sort_values("Date")
            frame = frame.drop_duplicates(
                subset=["Date"],
                keep="last",
            )
            frame = frame.set_index("Date")

            frame = frame.loc[
                (frame["Close"] > 0)
                & (frame["High"] > 0)
                & (frame["Low"] > 0)
            ]

            if frame.empty:
                raise ValueError(
                    "Aucune barre Massive exploitable."
                )

            close = frame["Close"].astype(float)
            volume = frame["Volume"].astype(float)
            last_row = frame.iloc[-1]

            history_rows = len(frame)
            insufficient_history = (
                history_rows < minimum_history_rows
            )

            warnings: list[str] = []

            if insufficient_history:
                warnings.append(
                    f"Historique insuffisant : "
                    f"{history_rows} lignes ; "
                    f"minimum attendu : "
                    f"{minimum_history_rows}."
                )

            average_volume20 = (
                volume.tail(20).mean()
                if len(volume) >= 1
                else None
            )

            current_volume = safe_float(
                last_row.get("Volume")
            )

            relative_volume = None

            if (
                current_volume is not None
                and safe_float(average_volume20)
                not in (None, 0)
            ):
                relative_volume = (
                    current_volume
                    / float(average_volume20)
                )

            average_dollar_volume20 = (
                (close * volume).tail(20).mean()
                if len(close) >= 1
                else None
            )

            return ProviderSymbolResult(
                symbol=normalized,
                provider=self.provider_name,
                provider_symbol=normalized,
                status="available",
                available=True,
                fetched_at=fetched_at,
                last_session_date=(
                    frame.index[-1].date().isoformat()
                ),
                open=rounded(last_row.get("Open")),
                high=rounded(last_row.get("High")),
                low=rounded(last_row.get("Low")),
                close=rounded(last_row.get("Close")),
                adjusted_close=rounded(
                    last_row.get("Close")
                ),
                volume=rounded(last_row.get("Volume")),
                history_rows=history_rows,
                history_start=(
                    frame.index[0].date().isoformat()
                ),
                history_end=(
                    frame.index[-1].date().isoformat()
                ),
                ma20=(
                    rounded(
                        close.rolling(20).mean().iloc[-1]
                    )
                    if history_rows >= 20
                    else None
                ),
                ma50=(
                    rounded(
                        close.rolling(50).mean().iloc[-1]
                    )
                    if history_rows >= 50
                    else None
                ),
                ma200=(
                    rounded(
                        close.rolling(200).mean().iloc[-1]
                    )
                    if history_rows >= 200
                    else None
                ),
                high20=(
                    rounded(
                        frame["High"].tail(20).max()
                    )
                    if history_rows >= 20
                    else None
                ),
                low20=(
                    rounded(
                        frame["Low"].tail(20).min()
                    )
                    if history_rows >= 20
                    else None
                ),
                return20=self._compute_return(
                    close,
                    20,
                ),
                return60=self._compute_return(
                    close,
                    60,
                ),
                return126=self._compute_return(
                    close,
                    126,
                ),
                atr14=self._compute_atr14(frame),
                average_volume20=rounded(
                    average_volume20
                ),
                relative_volume=rounded(
                    relative_volume
                ),
                average_dollar_volume20=rounded(
                    average_dollar_volume20
                ),
                adjusted_price_available=True,
                insufficient_history=(
                    insufficient_history
                ),
                warnings=warnings,
            )

        except Exception as exc:
            return ProviderSymbolResult(
                symbol=normalized,
                provider=self.provider_name,
                provider_symbol=normalized,
                status="unavailable",
                available=False,
                fetched_at=fetched_at,
                error=str(exc),
            )
