from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

GLOBAL_REGIME_PATH = Path("/opt/nsc/data/preprod/market/market_regime.json")
LOCAL_REGIME_PATH  = Path("/opt/nsc/data/preprod/equities_offensive/market/market_regime.json")

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main() -> int:
    reg = read_json(GLOBAL_REGIME_PATH, default={}) or {}

    if not isinstance(reg, dict) or not reg:
        reg = {
            "ts": utc_now_iso(),
            "engine": "equ_regime_sync_v1",
            "regime": "unknown",
            "confidence": 0.0,
            "note": "global regime missing/empty; wrote fallback unknown",
        }
    else:
        reg = dict(reg)
        reg.setdefault("ts", utc_now_iso())
        reg.setdefault("engine", "equ_regime_sync_v1")
        reg["synced_from"] = str(GLOBAL_REGIME_PATH)

    # normalize confidence to float
    try:
        c = reg.get("confidence", 0.0)
        reg["confidence"] = float(c) if c is not None else 0.0
    except Exception:
        reg["confidence"] = 0.0

    write_json(LOCAL_REGIME_PATH, reg)
    print({"saved": str(LOCAL_REGIME_PATH), "regime": reg.get("regime"), "confidence": reg.get("confidence")})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
