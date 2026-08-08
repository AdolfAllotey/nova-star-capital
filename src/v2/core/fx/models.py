from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class FXRate:
    base_currency: str
    quote_currency: str
    rate: float
    provider: str
    market_timestamp: str
    retrieved_at: str
    is_cached: bool = False
    cache_age_seconds: float = 0.0
    inverted: bool = False

    @property
    def pair(self) -> str:
        return f"{self.base_currency}/{self.quote_currency}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FXConversion:
    source_amount: float
    source_currency: str
    target_currency: str
    rate: float
    converted_amount: float
    rate_metadata: FXRate

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["rate_metadata"] = self.rate_metadata.to_dict()
        return payload
