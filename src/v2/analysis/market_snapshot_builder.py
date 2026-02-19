from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.v2.utils.logger import get_logger

logger = get_logger("market_snapshot_builder")

DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")
OUT = Path(DATA_DIR) / "market_snapshot.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _safe_default() -> Dict[str, Any]:
    # Neutral-safe snapshot (will tend to neutral/risk_off depending on rules)
    return {
        "ts": _utc_now(),
        "vix": 0.0,
        "qqq": {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0},
        "spy": {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0},
        "breadth": {"pct_above_ma200": None},
        "status": "default",
        "source": "market_snapshot_builder",
    }


def build_snapshot() -> Dict[str, Any]:
    """
    Best-effort:
    - If a market snapshot already exists, keep it but refresh ts (PREPROD OK).
    - Later: wire real fetchers (VIX/QQQ/SPY/breadth).
    """
    existing = _load_json(OUT)
    if existing:
        existing["ts"] = _utc_now()
        existing["status"] = existing.get("status") or "ok"
        existing["source"] = "market_snapshot_builder(reuse)"
        return existing
    return _safe_default()


def run() -> Dict[str, Any]:
    snap = build_snapshot()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("✅ market_snapshot written: %s status=%s vix=%s", OUT, snap.get("status"), snap.get("vix"))
    return snap


if __name__ == "__main__":
    run()
