#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Stooq Market Data Refresher V1.1

Seconde source indépendante de données de marché.

Cette version utilise directement l'export CSV de Stooq et ne dépend pas
du provider Stooq de pandas_datareader.

Sécurité :
- artefact séparé ;
- aucune modification des fichiers canoniques ;
- erreur isolée par symbole ;
- écriture atomique ;
- aucune moyenne entre Stooq et YFinance.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


LOGGER = logging.getLogger("nsc.stooq_market_data_refresher")

ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

DEFAULT_OUTPUT = ROOT / "market/market_data_stooq_v1.json"

DEFAULT_SYMBOLS = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "META",
    "NFLX",
    "GOOGL",
    "GOOG",
    "AVGO",
    "AMD",
    "TSLA",
    "CRM",
    "ORCL",
    "ADBE",
    "NOW",
]

HISTORY_DAYS = 550
MINIMUM_HISTORY_ROWS = 200
MAXIMUM_RETRIES = 2
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_PAUSE_SECONDS = 0.30

STOOQ_DOWNLOAD_URL = "https://stooq.com/q/d/l/"


@dataclass
class SymbolResult:
    symbol: str
    provider_symbol: str
    provider: str = "stooq"
    provider_transport: str = "native_csv"
    status: str = "unavailable"
    available: bool = False
    currency: str = "USD"

    last_session_date: str | None = None
    fetched_at: str | None = None

    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adjusted_close: float | None = None
    volume: float | None = None

    history_rows: int = 0
    history_start: str | None = None
    history_end: str | None = None

    ma20: float | None = None
    ma50: float | None = None
    ma200: float | None = None

    high20: float | None = None
    low20: float | None = None

    return20: float | None = None
    return60: float | None = None
    return126: float | None = None

    atr14: float | None = None
    average_volume20: float | None = None
    relative_volume: float | None = None
    average_dollar_volume20: float | None = None

    adjusted_price_available: bool = False
    insufficient_history: bool = False

    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def rounded(value: Any, digits: int = 8) -> float | None:
    result = safe_float(value)

    if result is None:
        return None

    return round(result, digits)


def normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def to_stooq_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)

    mappings = {
        "BRK.B": "BRK-B.US",
        "BRK-B": "BRK-B.US",
        "BF.B": "BF-B.US",
        "BF-B": "BF-B.US",
    }

    if normalized in mappings:
        return mappings[normalized].lower()

    if normalized.endswith(".US"):
        return normalized.lower()

    return f"{normalized.lower()}.us"


def compute_return(series: pd.Series, sessions: int) -> float | None:
    if len(series) <= sessions:
        return None

    current = safe_float(series.iloc[-1])
    previous = safe_float(series.iloc[-1 - sessions])

    if current is None or previous in (None, 0):
        return None

    return rounded((current / previous) - 1.0)


def compute_atr14(frame: pd.DataFrame) -> float | None:
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

    atr = true_range.rolling(window=14, min_periods=14).mean().iloc[-1]

    return rounded(atr)


def create_http_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/126 Safari/537.36 "
                "Nova-Star-Capital-Market-Data/1.1"
            ),
            "Accept": "text/csv,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )

    return session


def download_stooq_csv(
    session: requests.Session,
    provider_symbol: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    params = {
        "s": provider_symbol,
        "d1": start_date.strftime("%Y%m%d"),
        "d2": end_date.strftime("%Y%m%d"),
        "i": "d",
    }

    response = session.get(
        STOOQ_DOWNLOAD_URL,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    text = response.text.strip()

    if not text:
        raise ValueError("Réponse Stooq vide.")

    lowered = text.lower()

    if "no data" in lowered:
        raise ValueError("Stooq ne retourne aucune donnée pour ce symbole.")

    if "<html" in lowered or "<!doctype" in lowered:
        raise ValueError(
            "Stooq a retourné une page HTML au lieu d'un fichier CSV."
        )

    frame = pd.read_csv(io.StringIO(text))

    if frame.empty:
        raise ValueError("Le CSV Stooq ne contient aucune ligne.")

    return frame


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = {
        str(column).strip().lower(): column
        for column in frame.columns
    }

    required_mapping = {
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }

    missing = [
        source_name
        for source_name in required_mapping
        if source_name not in normalized_columns
    ]

    if missing:
        raise ValueError(
            "Colonnes absentes du CSV Stooq : " + ", ".join(missing)
        )

    rename_mapping = {
        normalized_columns[source_name]: target_name
        for source_name, target_name in required_mapping.items()
    }

    frame = frame.rename(columns=rename_mapping).copy()

    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["Date", "Close"])
    frame = frame.sort_values("Date")
    frame = frame.drop_duplicates(subset=["Date"], keep="last")
    frame = frame.set_index("Date")

    invalid_prices = (
        (frame["Close"] <= 0)
        | (frame["High"] <= 0)
        | (frame["Low"] <= 0)
    )

    frame = frame.loc[~invalid_prices]

    if frame.empty:
        raise ValueError(
            "Aucune ligne Stooq exploitable après normalisation."
        )

    return frame


def fetch_symbol(
    session: requests.Session,
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    minimum_history_rows: int,
    maximum_retries: int,
) -> SymbolResult:
    normalized_symbol = normalize_symbol(symbol)
    provider_symbol = to_stooq_symbol(normalized_symbol)
    fetched_at = utc_now_iso()

    last_error: Exception | None = None

    for attempt in range(1, maximum_retries + 2):
        try:
            LOGGER.info(
                "Téléchargement Stooq %s, tentative %s/%s",
                provider_symbol,
                attempt,
                maximum_retries + 1,
            )

            raw_frame = download_stooq_csv(
                session=session,
                provider_symbol=provider_symbol,
                start_date=start_date,
                end_date=end_date,
            )

            frame = normalize_frame(raw_frame)

            close = frame["Close"].astype(float)
            volume = frame["Volume"].astype(float)
            last_row = frame.iloc[-1]

            history_rows = len(frame)
            warnings: list[str] = []

            insufficient_history = history_rows < minimum_history_rows

            if insufficient_history:
                warnings.append(
                    f"Historique insuffisant : {history_rows} lignes ; "
                    f"minimum attendu : {minimum_history_rows}."
                )

            warnings.append(
                "Stooq ne fournit pas de champ Adjusted Close distinct "
                "dans cet export. Close n'est pas déclaré comme ajusté."
            )

            average_volume20 = (
                volume.tail(20).mean()
                if len(volume) >= 1
                else None
            )

            current_volume = safe_float(last_row.get("Volume"))
            relative_volume = None

            if (
                current_volume is not None
                and safe_float(average_volume20) not in (None, 0)
            ):
                relative_volume = (
                    current_volume / float(average_volume20)
                )

            dollar_volume = close * volume

            average_dollar_volume20 = (
                dollar_volume.tail(20).mean()
                if len(dollar_volume) >= 1
                else None
            )

            return SymbolResult(
                symbol=normalized_symbol,
                provider_symbol=provider_symbol,
                status="available",
                available=True,
                currency="USD",
                last_session_date=frame.index[-1].date().isoformat(),
                fetched_at=fetched_at,
                open=rounded(last_row.get("Open")),
                high=rounded(last_row.get("High")),
                low=rounded(last_row.get("Low")),
                close=rounded(last_row.get("Close")),
                adjusted_close=None,
                volume=rounded(last_row.get("Volume")),
                history_rows=history_rows,
                history_start=frame.index[0].date().isoformat(),
                history_end=frame.index[-1].date().isoformat(),
                ma20=(
                    rounded(close.rolling(20).mean().iloc[-1])
                    if history_rows >= 20
                    else None
                ),
                ma50=(
                    rounded(close.rolling(50).mean().iloc[-1])
                    if history_rows >= 50
                    else None
                ),
                ma200=(
                    rounded(close.rolling(200).mean().iloc[-1])
                    if history_rows >= 200
                    else None
                ),
                high20=(
                    rounded(frame["High"].tail(20).max())
                    if history_rows >= 20
                    else None
                ),
                low20=(
                    rounded(frame["Low"].tail(20).min())
                    if history_rows >= 20
                    else None
                ),
                return20=compute_return(close, 20),
                return60=compute_return(close, 60),
                return126=compute_return(close, 126),
                atr14=compute_atr14(frame),
                average_volume20=rounded(average_volume20),
                relative_volume=rounded(relative_volume),
                average_dollar_volume20=rounded(
                    average_dollar_volume20
                ),
                adjusted_price_available=False,
                insufficient_history=insufficient_history,
                warnings=warnings,
                error=None,
            )

        except Exception as exc:
            last_error = exc

            LOGGER.warning(
                "Échec Stooq pour %s à la tentative %s : %s",
                provider_symbol,
                attempt,
                exc,
            )

            if attempt <= maximum_retries:
                time.sleep(min(2 ** attempt, 5))

    return SymbolResult(
        symbol=normalized_symbol,
        provider_symbol=provider_symbol,
        status="unavailable",
        available=False,
        fetched_at=fetched_at,
        error=str(last_error) if last_error else "Erreur inconnue.",
    )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    os.replace(temporary_path, path)


def load_symbols_from_file(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    symbols: list[str] = []

    if isinstance(payload, list):
        source_items = payload

    elif isinstance(payload, dict):
        source_items = (
            payload.get("symbols")
            or payload.get("shortlist")
            or payload.get("universe")
            or payload.get("tickers")
            or []
        )

        if isinstance(source_items, dict):
            source_items = list(source_items.keys())

    else:
        source_items = []

    for item in source_items:
        if isinstance(item, str):
            symbols.append(normalize_symbol(item))

        elif isinstance(item, dict):
            candidate = item.get("symbol") or item.get("ticker")

            if candidate:
                symbols.append(normalize_symbol(candidate))

    return list(dict.fromkeys(symbols))


def build_payload(
    symbols: list[str],
    history_days: int,
    minimum_history_rows: int,
    maximum_retries: int,
    request_pause_seconds: float,
) -> dict[str, Any]:
    generated_at = utc_now_iso()

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=history_days)

    session = create_http_session()

    results: dict[str, dict[str, Any]] = {}

    try:
        for index, symbol in enumerate(symbols):
            result = fetch_symbol(
                session=session,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                minimum_history_rows=minimum_history_rows,
                maximum_retries=maximum_retries,
            )

            results[symbol] = asdict(result)

            if index < len(symbols) - 1:
                time.sleep(max(request_pause_seconds, 0.0))

    finally:
        session.close()

    available_symbols = [
        symbol
        for symbol, result in results.items()
        if result.get("available") is True
    ]

    unavailable_symbols = [
        symbol
        for symbol, result in results.items()
        if result.get("available") is not True
    ]

    insufficient_history_symbols = [
        symbol
        for symbol, result in results.items()
        if result.get("insufficient_history") is True
    ]

    requested_count = len(symbols)
    available_count = len(available_symbols)

    coverage_ratio = (
        available_count / requested_count
        if requested_count
        else 0.0
    )

    if (
        requested_count > 0
        and available_count == requested_count
        and not insufficient_history_symbols
    ):
        overall_status = "healthy"

    elif coverage_ratio >= 0.80:
        overall_status = "degraded"

    else:
        overall_status = "blocked"

    return {
        "schema_version": "1.1",
        "artifact_type": (
            "offensive_equities_stooq_market_data"
        ),
        "generated_at": generated_at,
        "provider": "stooq",
        "provider_transport": "native_csv",
        "provider_role": "secondary_validation_source",
        "market": "US_EQUITIES",
        "currency": "USD",
        "status": overall_status,
        "configuration": {
            "history_days": history_days,
            "minimum_history_rows": minimum_history_rows,
            "maximum_retries": maximum_retries,
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "request_pause_seconds": request_pause_seconds,
            "canonical_write_enabled": False,
            "adjusted_close_assumed": False,
        },
        "summary": {
            "symbols_requested": requested_count,
            "symbols_available": available_count,
            "symbols_unavailable": len(unavailable_symbols),
            "coverage_ratio": round(coverage_ratio, 8),
            "coverage_percent": round(
                coverage_ratio * 100.0,
                4,
            ),
            "available_symbols": available_symbols,
            "unavailable_symbols": unavailable_symbols,
            "insufficient_history_symbols": (
                insufficient_history_symbols
            ),
        },
        "symbols": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collecte indépendante Stooq via téléchargement CSV natif."
        )
    )

    parser.add_argument(
        "--symbols",
        nargs="*",
    )

    parser.add_argument(
        "--symbols-file",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--history-days",
        type=int,
        default=HISTORY_DAYS,
    )

    parser.add_argument(
        "--minimum-history-rows",
        type=int,
        default=MINIMUM_HISTORY_ROWS,
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAXIMUM_RETRIES,
    )

    parser.add_argument(
        "--request-pause-seconds",
        type=float,
        default=REQUEST_PAUSE_SECONDS,
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    if args.symbols_file:
        symbols = load_symbols_from_file(args.symbols_file)

    elif args.symbols:
        symbols = [
            normalize_symbol(symbol)
            for symbol in args.symbols
            if str(symbol).strip()
        ]

    else:
        symbols = DEFAULT_SYMBOLS.copy()

    symbols = list(dict.fromkeys(symbols))

    if not symbols:
        LOGGER.error("Aucun symbole fourni.")
        return 2

    payload = build_payload(
        symbols=symbols,
        history_days=max(args.history_days, 30),
        minimum_history_rows=max(
            args.minimum_history_rows,
            1,
        ),
        maximum_retries=max(args.max_retries, 0),
        request_pause_seconds=max(
            args.request_pause_seconds,
            0.0,
        ),
    )

    atomic_write_json(args.output, payload)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "output": str(args.output),
                "provider": payload["provider"],
                "provider_transport": payload[
                    "provider_transport"
                ],
                "coverage_percent": payload["summary"][
                    "coverage_percent"
                ],
                "symbols_available": payload["summary"][
                    "symbols_available"
                ],
                "symbols_requested": payload["summary"][
                    "symbols_requested"
                ],
                "unavailable_symbols": payload["summary"][
                    "unavailable_symbols"
                ],
                "canonical_files_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if payload["status"] in {
        "healthy",
        "degraded",
    } else 1


if __name__ == "__main__":
    sys.exit(main())
