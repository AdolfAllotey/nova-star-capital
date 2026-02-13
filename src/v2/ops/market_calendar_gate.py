#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone, time as dtime
from pathlib import Path
from typing import Any, Dict
import subprocess

# Europe/Paris without external libs:
# We'll approximate by reading system local time (server should be set to Europe/Paris).
# If your server is UTC, set TZ=Europe/Paris in systemd unit, or adapt later.

DEFAULT_OUT = Path("data/ops/trading_window.json")
DEFAULT_OVERRIDE = Path("data/ops/trading_window_override.json")
US_HOLIDAYS_PATH = Path("data/ops/us_holidays.json")

def ensure_holidays_available(now_local: datetime) -> None:
    """
    Ensure US holidays file exists and contains current year.
    Fail-safe: if generation fails, do nothing (do not block trading).
    """
    try:
        year = str(now_local.date().year)

        # If file missing -> generate (year + next year)
        if not US_HOLIDAYS_PATH.exists():
            subprocess.run(
                ["python", "src/v2/ops/generate_us_holidays.py", "--years", "2"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        doc = load_json(US_HOLIDAYS_PATH, default={}) or {}
        years = doc.get("years") or {}
        if year not in years:
            subprocess.run(
                ["python", "src/v2/ops/generate_us_holidays.py", "--years", "2"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        # absolute fail-safe: never block trading because of calendar
        pass


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def local_now() -> datetime:
    # uses server local timezone
    return datetime.now().astimezone()

def within_window(now_local: datetime, start_hm: str, end_hm: str) -> bool:
    sh, sm = map(int, start_hm.split(":"))
    eh, em = map(int, end_hm.split(":"))
    start = dtime(sh, sm)
    end = dtime(eh, em)
    t = now_local.timetz().replace(tzinfo=None)
    return (t >= start) and (t <= end)


def is_us_holiday(now_local: datetime) -> bool:
    """
    No external deps. Uses data/ops/us_holidays.json by year.
    Dates are in YYYY-MM-DD (local date). We gate by local date.
    """
    doc = load_json(US_HOLIDAYS_PATH, default=None)
    if not isinstance(doc, dict):
        return False
    years = doc.get("years") or {}
    y = str(now_local.date().year)
    days = years.get(y) or []
    if not isinstance(days, list):
        return False
    today = now_local.date().isoformat()
    return today in set(str(x) for x in days)
def compute_gate(
    window_start: str = "15:30",   # Paris time (regular session approx)
    window_end: str = "22:00",
) -> Dict[str, Any]:
    now = local_now()
    ensure_holidays_available(now)

    weekday = now.weekday()  # 0=Mon ... 6=Sun
    reasons = []
    allowed = True

    # override (manual)
    override = load_json(DEFAULT_OVERRIDE, default=None)
    if isinstance(override, dict) and override.get("enabled") is True:
        allowed = bool(override.get("allowed", False))
        reasons.append(f"override enabled => allowed={allowed}")
        if override.get("reason"):
            reasons.append(str(override["reason"]))
        return {
            "ts": utc_now_iso(),
            "local_ts": now.isoformat(),
            "engine": "market_calendar_gate_v1",
            "allowed": allowed,
            "window": {"start": window_start, "end": window_end},
            "reasons": reasons,
            "override": override,
        }

    # weekends blocked
    if weekday >= 5:
        allowed = False
        reasons.append("weekend => market closed")

    # US holidays gate
    if allowed and is_us_holiday(now):
        allowed = False
        reasons.append("US holiday => market closed")

    # trading window gate
    if allowed:
        if not within_window(now, window_start, window_end):
            allowed = False
            reasons.append(f"outside trading window {window_start}-{window_end} (local)")

    if allowed:
        reasons.append("within trading window (local)")

    return {
        "ts": utc_now_iso(),
        "local_ts": now.isoformat(),
        "engine": "market_calendar_gate_v1",
        "allowed": allowed,
        "window": {"start": window_start, "end": window_end},
        "reasons": reasons,
        "override": None,
    }

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Market calendar gate V1 (no external deps)")
    ap.add_argument("--start", default="15:30")
    ap.add_argument("--end", default="22:00")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out = compute_gate(args.start, args.end)
    save_json(Path(args.out), out)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
