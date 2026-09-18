from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter()

HISTORY_PATH = Path(
    "/opt/nsc/data/preprod/long_term/reporting/nav_history.json"
)


def _read_history():
    if not HISTORY_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="lt nav history unavailable",
        )

    try:
        payload = json.loads(
            HISTORY_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"invalid lt nav history: {exc}",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail="invalid lt nav history payload",
        )

    rows = payload.get("history") or []

    if not isinstance(rows, list):
        raise HTTPException(
            status_code=500,
            detail="invalid lt nav history rows",
        )

    return payload, rows


@router.get(
    "/lt-curve",
    summary="NSC LT PnL curve v2",
)
def get_lt_curve():
    payload, rows = _read_history()

    points = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        ts = (
            row.get("ts")
            or row.get("timestamp")
            or row.get("date")
        )

        if not ts:
            continue

        pnl = float(
            row.get(
                "unrealized_pnl_eur",
                0.0,
            )
            or 0.0
        )

        points.append({
            "date": str(ts),
            "cumulative_profit": round(
                pnl,
                2,
            ),
            "market_value_eur": round(
                float(
                    row.get(
                        "market_value_eur",
                        0.0,
                    )
                    or 0.0
                ),
                2,
            ),
            "cost_basis_eur": round(
                float(
                    row.get(
                        "cost_basis_eur",
                        0.0,
                    )
                    or 0.0
                ),
                2,
            ),
        })

    final_pnl = (
        float(
            points[-1][
                "cumulative_profit"
            ]
        )
        if points
        else 0.0
    )

    updated_at = (
        points[-1]["date"]
        if points
        else None
    )

    return {
        "status": "ok",
        "engine": "lt_curve_v2",
        "metric": "unrealized_pnl_eur",
        "points": points,
        "final_cumulative_profit": round(
            final_pnl,
            2,
        ),
        "updated_at": updated_at,
        "source": str(HISTORY_PATH),
        "source_engine": payload.get(
            "engine"
        ),
    }
