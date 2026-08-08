from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .models import FXRate
from .validator import parse_iso_timestamp, validate_rate


DEFAULT_CACHE_PATH = Path(
    os.getenv(
        "NSC_FX_CACHE_PATH",
        "/opt/nsc/data/preprod/core/fx/rates.json",
    )
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FXCache:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or DEFAULT_CACHE_PATH)

    def _load_document(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {
                "engine": "core_fx_cache_v1",
                "rates": {},
            }

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )

            if not isinstance(payload, dict):
                return {
                    "engine": "core_fx_cache_v1",
                    "rates": {},
                }

            if not isinstance(payload.get("rates"), dict):
                payload["rates"] = {}

            return payload

        except Exception:
            return {
                "engine": "core_fx_cache_v1",
                "rates": {},
            }

    def _atomic_save(self, payload: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(tmp_name, self.path)

        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    @staticmethod
    def pair_key(base: str, quote: str) -> str:
        return f"{base.upper()}_{quote.upper()}"

    def put(self, rate: FXRate) -> None:
        validated = validate_rate(rate)
        document = self._load_document()

        document["engine"] = "core_fx_cache_v1"
        document["updated_at"] = utc_now().isoformat().replace(
            "+00:00",
            "Z",
        )
        document["rates"][
            self.pair_key(
                validated.base_currency,
                validated.quote_currency,
            )
        ] = validated.to_dict()

        self._atomic_save(document)

    def get(
        self,
        base: str,
        quote: str,
        max_age_seconds: float,
    ) -> Optional[FXRate]:
        document = self._load_document()

        raw = document.get("rates", {}).get(
            self.pair_key(base, quote)
        )

        if not isinstance(raw, dict):
            return None

        retrieved_at = parse_iso_timestamp(
            raw.get("retrieved_at")
        )

        if retrieved_at is None:
            return None

        age = max(
            0.0,
            (utc_now() - retrieved_at).total_seconds(),
        )

        if age > float(max_age_seconds):
            return None

        try:
            cached_rate = FXRate(
                base_currency=str(
                    raw["base_currency"]
                ).upper(),
                quote_currency=str(
                    raw["quote_currency"]
                ).upper(),
                rate=float(raw["rate"]),
                provider=str(raw["provider"]),
                market_timestamp=str(
                    raw["market_timestamp"]
                ),
                retrieved_at=str(raw["retrieved_at"]),
                is_cached=True,
                cache_age_seconds=round(age, 3),
                inverted=bool(raw.get("inverted", False)),
            )

            return validate_rate(cached_rate)

        except Exception:
            return None
