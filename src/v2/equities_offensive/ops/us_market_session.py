from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRADING_WINDOW_OUT = Path("/opt/nsc/data/preprod/ops/trading_window.json")
HOLIDAYS_OUT = Path("/opt/nsc/data/preprod/ops/us_holidays.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def build_with_exchange_calendars(now: datetime) -> dict[str, Any] | None:
    try:
        import exchange_calendars as xcals
        import pandas as pd

        calendar = xcals.get_calendar("XNYS")
        minute = pd.Timestamp(now).floor("min")

        is_open = bool(calendar.is_open_on_minute(minute))

        session = None
        market_open = None
        market_close = None

        try:
            session = calendar.minute_to_session(minute, direction="previous")
            market_open = calendar.session_open(session)
            market_close = calendar.session_close(session)
        except Exception:
            pass

        return {
            "ts": utc_now_iso(),
            "engine": "us_market_session_v2",
            "calendar_engine": "exchange_calendars",
            "calendar": "XNYS",
            "market": "US",
            "is_open": is_open,
            "session": str(session) if session is not None else None,
            "open_utc": market_open.isoformat() if market_open is not None else None,
            "close_utc": market_close.isoformat() if market_close is not None else None,
            "quality": "authoritative",
            "fallback": False,
            "reasons": [],
        }
    except Exception:
        return None


def build_with_pandas_market_calendars(now: datetime) -> dict[str, Any] | None:
    try:
        import pandas_market_calendars as mcal
        import pandas as pd

        calendar = mcal.get_calendar("NYSE")
        day = now.date().isoformat()
        schedule = calendar.schedule(start_date=day, end_date=day)

        if schedule.empty:
            return {
                "ts": utc_now_iso(),
                "engine": "us_market_session_v2",
                "calendar_engine": "pandas_market_calendars",
                "calendar": "NYSE",
                "market": "US",
                "is_open": False,
                "session": day,
                "open_utc": None,
                "close_utc": None,
                "quality": "authoritative",
                "fallback": False,
                "reasons": ["non_trading_day"],
            }

        row = schedule.iloc[0]
        market_open = pd.Timestamp(row["market_open"]).to_pydatetime()
        market_close = pd.Timestamp(row["market_close"]).to_pydatetime()

        return {
            "ts": utc_now_iso(),
            "engine": "us_market_session_v2",
            "calendar_engine": "pandas_market_calendars",
            "calendar": "NYSE",
            "market": "US",
            "is_open": bool(market_open <= now <= market_close),
            "session": day,
            "open_utc": market_open.isoformat(),
            "close_utc": market_close.isoformat(),
            "quality": "authoritative",
            "fallback": False,
            "reasons": [],
        }
    except Exception:
        return None


def main() -> int:
    now = datetime.now(timezone.utc)

    payload = build_with_exchange_calendars(now)
    if payload is None:
        payload = build_with_pandas_market_calendars(now)

    if payload is None:
        payload = {
            "ts": utc_now_iso(),
            "engine": "us_market_session_v2",
            "calendar_engine": "unavailable",
            "calendar": "XNYS",
            "market": "US",
            "is_open": False,
            "session": None,
            "open_utc": None,
            "close_utc": None,
            "quality": "degraded",
            "fallback": True,
            "reasons": ["calendar_dependency_unavailable"],
        }

    write_json(TRADING_WINDOW_OUT, payload)

    write_json(
        HOLIDAYS_OUT,
        {
            "ts": utc_now_iso(),
            "engine": "us_market_session_v2",
            "calendar": payload.get("calendar"),
            "calendar_engine": payload.get("calendar_engine"),
            "quality": payload.get("quality"),
            "delegated_to_exchange_calendar": True,
        },
    )

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0 if payload.get("quality") == "authoritative" else 2


if __name__ == "__main__":
    raise SystemExit(main())
