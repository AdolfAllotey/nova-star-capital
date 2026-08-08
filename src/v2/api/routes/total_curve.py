from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter()

CRYPTO_PATH = Path("/opt/nsc/app/data/crypto/reporting/equity_curve.json")
OFFENSIVE_PATH = Path("/opt/nsc/data/preprod/equities_offensive/reporting/equity_curve.json")
DEFENSIVE_PATH = Path("/opt/nsc/app/data/defensive/reporting/equity_curve.json")
BONDS_PATH = Path("/opt/nsc/app/data/bonds/reporting/equity_curve.json")
METALS_PATH = Path("/opt/nsc/app/data/metals/reporting/equity_curve.json")
LT_VAL_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _points_to_map(points):
    out = {}
    for row in points or []:
        date = row.get("date")
        if not date:
            continue
        out[str(date)[:10]] = float(row.get("cumulative_profit", 0.0) or 0.0)
    return out


def _carry_forward(dates, value_map):
    carried = {}
    last_val = 0.0
    for d in dates:
        if d in value_map:
            last_val = float(value_map[d])
        carried[d] = round(last_val, 2)
    return carried


def _add_daily_change(points):
    prev = None
    out = []
    for p in points:
        cur = float(p.get("cumulative_profit", 0.0))
        if prev is None:
            change = 0.0
        else:
            change = round(cur - prev, 2)
        row = dict(p)
        row["daily_change"] = change
        out.append(row)
        prev = cur
    return out


@router.get("/total-curve", summary="NSC total curve v7")
def get_total_curve():
    crypto = _load_json(CRYPTO_PATH) or {}
    offensive = _load_json(OFFENSIVE_PATH) or {}
    defensive = _load_json(DEFENSIVE_PATH) or {}
    bonds = _load_json(BONDS_PATH) or {}
    metals = _load_json(METALS_PATH) or {}
    lt_val = _load_json(LT_VAL_PATH) or {}

    crypto_raw = _points_to_map(crypto.get("points", []))
    offensive_raw = _points_to_map(offensive.get("points", []))
    defensive_raw = _points_to_map(defensive.get("points", []))
    bonds_raw = _points_to_map(bonds.get("points", []))
    metals_raw = _points_to_map(metals.get("points", []))

    lt_totals = lt_val.get("totals", {}) or {}
    lt_market_value = float(lt_totals.get("market_value_eur", 0.0) or 0.0)
    lt_updated_at = str(lt_val.get("updated_at") or lt_val.get("timestamp") or "")[:10]

    lt_raw = {}
    if lt_market_value and lt_updated_at:
        lt_raw[lt_updated_at] = lt_market_value

    options_us_raw = {}

    all_dates = sorted(
        set(crypto_raw)
        | set(offensive_raw)
        | set(defensive_raw)
        | set(bonds_raw)
        | set(metals_raw)
        | set(lt_raw)
        | set(options_us_raw)
    )

    crypto_map = _carry_forward(all_dates, crypto_raw)
    offensive_map = _carry_forward(all_dates, offensive_raw)
    defensive_map = _carry_forward(all_dates, defensive_raw)
    bonds_map = _carry_forward(all_dates, bonds_raw)
    metals_map = _carry_forward(all_dates, metals_raw)
    lt_map = _carry_forward(all_dates, lt_raw)
    options_us_map = _carry_forward(all_dates, options_us_raw)

    points = []
    for d in all_dates:
        crypto_val = float(crypto_map.get(d, 0.0))
        offensive_val = float(offensive_map.get(d, 0.0))
        defensive_val = float(defensive_map.get(d, 0.0))
        bonds_val = float(bonds_map.get(d, 0.0))
        metals_val = float(metals_map.get(d, 0.0))
        lt_val_d = float(lt_map.get(d, 0.0))
        options_us_val = float(options_us_map.get(d, 0.0))

        total_val = (
            crypto_val
            + offensive_val
            + defensive_val
            + bonds_val
            + metals_val
            + lt_val_d
            + options_us_val
        )

        points.append({
            "date": d,
            "cumulative_profit": round(total_val, 2),
            "components": {
                "crypto": round(crypto_val, 2),
                "offensive": round(offensive_val, 2),
                "defensive": round(defensive_val, 2),
                "bonds": round(bonds_val, 2),
                "metals": round(metals_val, 2),
                "lt": round(lt_val_d, 2),
                "options_us": round(options_us_val, 2),
            },
        })

    points = _add_daily_change(points)
    final_val = float(points[-1]["cumulative_profit"]) if points else 0.0

    return {
        "status": "ok",
        "engine": "total_curve_v7",
        "points": points,
        "final_cumulative_profit": round(final_val, 2),
        "sources": {
            "crypto": str(CRYPTO_PATH),
            "offensive": str(OFFENSIVE_PATH),
            "defensive": str(DEFENSIVE_PATH),
            "bonds": str(BONDS_PATH),
            "metals": str(METALS_PATH),
            "lt": str(LT_VAL_PATH),
            "options_us": "placeholder_zero_until_brick_ready",
        },
        "source_status": {
            "real": ["crypto", "offensive", "lt"],
            "pending": ["defensive", "bonds", "metals", "options_us"],
        },
        "notes": [
            "TOTAL v7 uses carry-forward by date for each brick.",
            "TOTAL = crypto + offensive + defensive + bonds + metals + long_term + options_us(placeholder=0)"
        ],
    }
