#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Market Data Provider Base V1

Contrat commun des fournisseurs de données de marché.

Aucun provider ne doit :
- modifier les artefacts canoniques ;
- déclencher une promotion ;
- moyenner les prix de plusieurs sources ;
- masquer une erreur de collecte.
"""

from __future__ import annotations

import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MarketBar:
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    adjusted_close: float | None = None


@dataclass
class ProviderSymbolResult:
    symbol: str
    provider: str
    status: str
    available: bool

    provider_symbol: str | None = None
    currency: str = "USD"

    fetched_at: str | None = None
    last_session_date: str | None = None

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


class MarketDataProvider(ABC):
    provider_name: str
    provider_role: str
    requires_api_key: bool = False

    @abstractmethod
    def is_configured(self) -> bool:
        """Indique si le provider peut être utilisé."""

    @abstractmethod
    def fetch_symbol(
        self,
        symbol: str,
        history_days: int,
        minimum_history_rows: int,
    ) -> ProviderSymbolResult:
        """Récupère et normalise un symbole."""

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "provider_role": self.provider_role,
            "requires_api_key": self.requires_api_key,
            "configured": self.is_configured(),
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def rounded(value: Any, digits: int = 8) -> float | None:
    converted = safe_float(value)

    if converted is None:
        return None

    return round(converted, digits)


def normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


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


def serialize_result(
    result: ProviderSymbolResult,
) -> dict[str, Any]:
    return asdict(result)
