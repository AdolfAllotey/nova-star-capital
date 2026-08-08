from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

POSITIONS_PATH = Path("/opt/nsc/data/preprod/equities_offensive/state/positions.json")
PRICES_PATH = Path("/opt/nsc/data/preprod/equities_offensive/market/prices.json")
FILLS_PATH = Path("/opt/nsc/data/preprod/equities_offensive/execution/simulated_fills.jsonl")
CURVE_PATH = Path("/opt/nsc/data/preprod/equities_offensive/reporting/equity_curve.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except Exception:
                    continue
    except Exception:
        pass
    return rows


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_prices(doc: Any) -> Dict[str, float]:
    if isinstance(doc, dict) and isinstance(doc.get("prices"), dict):
        src = doc.get("prices") or {}
    elif isinstance(doc, dict):
        src = doc
    else:
        src = {}

    out: Dict[str, float] = {}
    for k, v in src.items():
        try:
            px = float(v)
            if px > 0:
                out[str(k).upper()] = px
        except Exception:
            continue
    return out


def normalize_positions(doc: Any) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}

    if isinstance(doc, dict):
        for sym, row in doc.items():
            if not isinstance(row, dict):
                continue
            try:
                qty = float(row.get("qty", 0) or 0)
                avg = float(row.get("avg_price", 0) or 0)
            except Exception:
                continue
            if qty > 0 and avg > 0:
                out[str(sym).upper()] = {"qty": qty, "avg_price": avg}
        return out

    if isinstance(doc, list):
        for row in doc:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or row.get("token") or "").strip().upper()
            if not sym:
                continue
            try:
                qty = float(row.get("qty", row.get("quantity", 0)) or 0)
                avg = float(row.get("avg_price", row.get("entry_price", 0)) or 0)
            except Exception:
                continue
            if qty > 0 and avg > 0:
                out[sym] = {"qty": qty, "avg_price": avg}

    return out


def compute_realized_pnl_from_fills(rows: List[Dict[str, Any]]) -> float:
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        for field in ("realized_pnl", "realized_pnl_usd", "realized_pnl_eur", "pnl", "pnl_usd", "pnl_eur"):
            try:
                val = row.get(field)
                if val is not None:
                    total += float(val)
                    break
            except Exception:
                continue
    return round(total, 2)


def run() -> None:
    positions_doc = load_json(POSITIONS_PATH, {})
    prices_doc = load_json(PRICES_PATH, {})
    fills = load_jsonl(FILLS_PATH)

    positions = normalize_positions(positions_doc)
    prices = normalize_prices(prices_doc)

    unrealized = 0.0
    open_notional = 0.0
    used_symbols = []

    for sym, pos in positions.items():
        qty = float(pos["qty"])
        avg_price = float(pos["avg_price"])
        current_price = float(prices.get(sym, avg_price))
        open_notional += qty * current_price
        unrealized += (current_price - avg_price) * qty
        used_symbols.append(
            {
                "symbol": sym,
                "qty": round(qty, 10),
                "avg_price": round(avg_price, 6),
                "current_price": round(current_price, 6),
                "unrealized_pnl": round((current_price - avg_price) * qty, 2),
            }
        )

    realized = compute_realized_pnl_from_fills(fills)
    cumulative_profit = round(realized + unrealized, 2)

    curve = load_json(
        CURVE_PATH,
        {
            "status": "ok",
            "engine": "offensive_equity_curve_v2",
            "brick": "offensive",
            "points": [],
            "final_cumulative_profit": 0.0,
        },
    )

    today = datetime.now(timezone.utc).date().isoformat()
    points = curve.get("points", [])
    if not isinstance(points, list):
        points = []

    updated = False
    for row in points:
        if isinstance(row, dict) and row.get("date") == today:
            row["cumulative_profit"] = cumulative_profit
            updated = True
            break

    if not updated:
        points.append({"date": today, "cumulative_profit": cumulative_profit})

    curve["status"] = "ok"
    curve["engine"] = "offensive_equity_curve_v2"
    curve["brick"] = "offensive"
    curve["points"] = points
    curve["final_cumulative_profit"] = cumulative_profit
    curve["updated_at"] = utc_now_iso()
    curve["breakdown"] = {
        "positions_count": len(positions),
        "open_notional_usd": round(open_notional, 2),
        "realized_pnl": round(realized, 2),
        "unrealized_pnl": round(unrealized, 2),
        "symbols": used_symbols,
    }

    save_json(CURVE_PATH, curve)
    print(json.dumps(curve, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
