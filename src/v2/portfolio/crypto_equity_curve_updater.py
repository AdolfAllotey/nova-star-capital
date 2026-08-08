from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SRC_PATH = Path("/opt/nsc/src/v2/data/simulation/global_performance.json")
DST_PATH = Path("/opt/nsc/app/data/crypto/reporting/equity_curve.json")


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def build_curve(data: dict):
    history = data.get("history", []) or []
    cumulative = 0.0
    points = []

    for row in history:
        daily = float(row.get("daily_profit", 0.0) or 0.0)
        cumulative += daily
        points.append(
            {
                "date": row.get("date"),
                "daily_profit": round(daily, 2),
                "cumulative_profit": round(cumulative, 2),
            }
        )

    return points, round(cumulative, 2)


def run():
    src = load_json(SRC_PATH, {})
    points, final_val = build_curve(src)

    payload = {
        "status": "ok",
        "engine": "crypto_equity_curve_v1",
        "brick": "crypto",
        "points": points,
        "final_cumulative_profit": final_val,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SRC_PATH),
    }

    save_json(DST_PATH, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    run()
