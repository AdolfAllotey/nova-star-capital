from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

SRC_HOL = Path("/opt/nsc/data/preprod/ops/us_holidays.json")
SRC_WIN = Path("/opt/nsc/data/preprod/ops/trading_window.json")

DST_HOL = Path("/opt/nsc/data/preprod/equities_offensive/ops/us_holidays.json")
DST_WIN = Path("/opt/nsc/data/preprod/equities_offensive/ops/trading_window.json")

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
    hol = read_json(SRC_HOL, default={}) or {}
    win = read_json(SRC_WIN, default={}) or {}

    # holidays may be dict or list depending on generator
    if not isinstance(hol, (dict, list)):
        hol = {"ts": utc_now_iso(), "engine": "equ_sync_ops_v1", "holidays": []}

    if not isinstance(win, dict) or not win:
        win = {
            "ts": utc_now_iso(),
            "engine": "equ_sync_ops_v1",
            "market": "US",
            "is_open": False,
            "note": "fallback window (global missing/invalid)",
        }

    # annotate
    if isinstance(hol, dict):
        hol.setdefault("ts", utc_now_iso())
        hol.setdefault("engine", "equ_sync_ops_v1")
        hol["synced_from"] = str(SRC_HOL)

    win = dict(win)
    win.setdefault("ts", utc_now_iso())
    win.setdefault("engine", "equ_sync_ops_v1")
    win["synced_from"] = str(SRC_WIN)

    write_json(DST_HOL, hol)
    write_json(DST_WIN, win)

    print({"saved": [str(DST_HOL), str(DST_WIN)]})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
