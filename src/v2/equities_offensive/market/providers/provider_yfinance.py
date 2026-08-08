#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — YFinance Provider V1

Source primaire de recherche en préproduction.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from provider_base import (
    MarketDataProvider,
    ProviderSymbolResult,
    normalize_symbol,
    rounded,
    safe_float,
    utc_now_iso,
)


class YFinanceProvider(MarketDataProvider):
    provider_name = "yfinance"
    provider_role = "primary_research_source"
    requires_api_key = False

    def is_configured(self) -> bool:
        return True

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

    def fetch_symbol(
        self,
        symbol: str,
        history_days: int,
        minimum_history_rows: int,
    ) -> ProviderSymbolResult:
        normalized = normalize_symbol(symbol)
        fetched_at = utc_now_iso()

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(
                days=max(history_days, 30)
            )

            frame = yf.download(
                normalized,
                start=start_date.date().isoformat(),
                end=(end_date + timedelta(days=1))
                .date()
                .isoformat(),
                interval="1d",
                auto_adjust=True,
                actions=False,
                progress=False,
                threads=False,
            )

            if frame is None or frame.empty:
                raise ValueError(
                    "YFinance n'a retourné aucune donnée."
                )

            if isinstance(frame.columns, pd.MultiIndex):
                if normalized in frame.columns.get_level_values(-1):
                    frame = frame.xs(
                        normalized,
                        axis=1,
                        level=-1,
                    )
                else:
                    frame.columns = frame.columns.get_level_values(0)

            frame = frame.copy()
            frame.index = pd.to_datetime(
                frame.index,
                errors="coerce",
            )

            frame = frame[~frame.index.isna()]
            frame = frame.sort_index()
            frame = frame[
                ~frame.index.duplicated(keep="last")
            ]

            required_columns = {
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            }

            missing = required_columns.difference(
                frame.columns
            )

            if missing:
                raise ValueError(
                    "Colonnes YFinance manquantes : "
                    + ", ".join(sorted(missing))
                )

            for column in required_columns:
                frame[column] = pd.to_numeric(
                    frame[column],
                    errors="coerce",
                )

            frame = frame.dropna(subset=["Close"])

            frame = frame.loc[
                (frame["Close"] > 0)
                & (frame["High"] > 0)
                & (frame["Low"] > 0)
            ]

            if frame.empty:
                raise ValueError(
                    "Aucune ligne YFinance exploitable."
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
