from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

CRYPTO_CURVE_PATH = Path("/opt/nsc/app/data/crypto/reporting/equity_curve.json")
OFFENSIVE_CURVE_PATH = Path("/opt/nsc/data/preprod/equities_offensive/reporting/equity_curve.json")


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


@router.get("/brick-curve/{brick}", summary="NSC brick curve v1")
def get_brick_curve(brick: str):
    brick = (brick or "").strip().lower()

    if brick == "crypto":
        data = _load_json(CRYPTO_CURVE_PATH)
        if not data:
            raise HTTPException(status_code=404, detail="crypto curve source unavailable")

        return {
            "status": "ok",
            "engine": "brick_curve_v1",
            "brick": "crypto",
            "points": data.get("points", []) or [],
            "final_cumulative_profit": float(data.get("final_cumulative_profit", 0.0) or 0.0),
            "source_file": str(CRYPTO_CURVE_PATH),
        }

    if brick == "offensive":
        data = _load_json(OFFENSIVE_CURVE_PATH)
        if not data:
            raise HTTPException(status_code=404, detail="offensive curve source unavailable")

        return {
            "status": "ok",
            "engine": "brick_curve_v1",
            "brick": "offensive",
            "points": data.get("points", []) or [],
            "final_cumulative_profit": float(data.get("final_cumulative_profit", 0.0) or 0.0),
            "source_file": str(OFFENSIVE_CURVE_PATH),
        }

    raise HTTPException(status_code=404, detail="unsupported brick")
