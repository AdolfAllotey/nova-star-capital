from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

SUMMARY_PATH = DATA_DIR / "discovery" / "persistence_summary.json"
OUT_PATH = DATA_DIR / "discovery" / "persistence_opportunities.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    raw = load_json(SUMMARY_PATH, default={}) or {}
    items = raw.get("top_persistent", [])
    if not isinstance(items, list):
        items = []

    opportunities = []

    for row in items:
        try:
            symbol = str(row.get("symbol") or "").upper().strip()
            chg = float(row.get("last_chg_24h") or 0.0)
            gain_delta = float(row.get("gain_delta") or 0.0)
            persistence_score = float(row.get("persistence_score") or 0.0)
            sources_count = int(row.get("sources_count") or len(row.get("sources") or []))
        except Exception:
            continue

        if not symbol:
            continue

        if chg < 15.0:
            continue
        if chg > 60.0:
            continue
        if gain_delta < 0.0:
            continue

        opportunity_score = min(
            100.0,
            persistence_score
            + min(max(chg, 0.0), 60.0) * 0.35
            + min(sources_count, 5) * 4.0
            + min(gain_delta, 15.0) * 1.2
        )

        opportunities.append({
            "symbol": symbol,
            "pair": f"{symbol}USDT",
            "opportunity_score": round(opportunity_score, 2),
            "persistence_score": persistence_score,
            "persistence_status": row.get("persistence_status"),
            "hours_present": row.get("hours_present"),
            "observations": row.get("observations"),
            "chg_24h": chg,
            "gain_delta": gain_delta,
            "sources": row.get("sources") or [],
            "sources_count": sources_count,
            "reason": (
                f"persistence opportunity: chg_24h={chg:.2f}%, "
                f"gain_delta={gain_delta:.2f}, sources={sources_count}, "
                f"persistence_score={persistence_score:.2f}"
            ),
        })

    opportunities.sort(
        key=lambda x: (
            x.get("opportunity_score", 0),
            x.get("persistence_score", 0),
            x.get("chg_24h", 0),
        ),
        reverse=True,
    )

    payload = {
        "status": "ok",
        "generated_at": utc_now(),
        "engine": "persistence_opportunities_v1",
        "filters": {
            "min_chg_24h": 15.0,
            "max_chg_24h": 60.0,
            "min_gain_delta": 0.0,
        },
        "count": len(opportunities),
        "items": opportunities[:50],
    }

    save_json(OUT_PATH, payload)

    print({
        "output": str(OUT_PATH),
        "engine": "persistence_opportunities_v1",
        "count": len(opportunities),
        "top": [x["symbol"] for x in opportunities[:10]],
    })


if __name__ == "__main__":
    main()
