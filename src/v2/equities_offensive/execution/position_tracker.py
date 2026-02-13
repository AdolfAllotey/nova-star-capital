from __future__ import annotations
from src.v2.portfolio.pocket_reader import get_budget_usd
#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from src.v2.equities_offensive.governance.governance_reader import load_governance

POSITIONS_PATH = Path("data/equities_offensive/state/positions.json")
FILLS_PATH = Path("data/equities_offensive/execution/simulated_fills.jsonl")
PRICES_PATH = Path("data/equities_offensive/market/prices.json")  # optional
GOV_PATH = Path("data/governance/governance_engine_pro.json")

OUT_EXPOSURE = Path("data/equities_offensive/state/exposure_snapshot.json")
OUT_POS_REPORT = Path("data/equities_offensive/state/position_report.json")
OUT_LIMITS = Path("data/equities_offensive/state/limits_report.json")

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def read_jsonl(path: Path, limit: int = 5000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
    return out

def get_price(symbol: str, fallback: float = 100.0) -> float:
    doc = load_json(PRICES_PATH, default=None)
    if isinstance(doc, dict):
        try:
            px = doc.get(symbol)
            if px is not None:
                return float(px)
        except Exception:
            pass
    return float(fallback)

def compute_exposure(positions: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, float]]:
    total = 0.0
    by_symbol: Dict[str, float] = {}
    lines = []
    for sym, p in positions.items():
        try:
            qty = float(p.get("qty", 0.0))
            avg = float(p.get("avg_price", 0.0) or 0.0)
        except Exception:
            continue
        if qty <= 0:
            continue
        px = get_price(sym, fallback=(avg or 100.0))
        notional = px * qty
        by_symbol[sym] = notional
        total += notional
        lines.append({"symbol": sym, "qty": qty, "price": px, "avg_price": avg, "notional_usd": round(notional, 2)})

    snap = {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "open_positions": len(lines),
        "total_notional_usd": round(total, 2),
        "positions": lines,
    }
    return snap, by_symbol

def extract_caps(gov: Dict[str, Any]) -> Dict[str, Any]:
    caps = gov.get("caps") if isinstance(gov, dict) else {}
    if not isinstance(caps, dict):
        caps = {}
    # defaults (safe)
    return {
        "max_positions": int(caps.get("max_positions", 12)),
        "max_total_notional_usd": float(caps.get("max_total_notional_usd", 5000.0)),
        "max_symbol_weight": float(caps.get("max_symbol_weight", 0.25)),  # 25%
    }

def check_limits(exposure: Dict[str, Any], by_symbol: Dict[str, float], caps: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    soft_vetos = []
    ok = True

    npos = int(exposure.get("open_positions", 0))
    total = float(exposure.get("total_notional_usd", 0.0) or 0.0)

    if npos > caps["max_positions"]:
        ok = False
        soft_vetos.append("too_many_positions")
        reasons.append(f"open_positions={npos} > max_positions={caps['max_positions']}")

    if total > caps["max_total_notional_usd"]:
        ok = False
        soft_vetos.append("total_notional_cap")
        reasons.append(f"total_notional_usd={total:.2f} > cap={caps['max_total_notional_usd']:.2f}")

    # concentration
    if total > 0:
        for sym, notion in by_symbol.items():
            w = notion / total
            if w > caps["max_symbol_weight"]:
                ok = False
                soft_vetos.append("symbol_concentration")
                reasons.append(f"{sym} weight={w:.2%} > cap={caps['max_symbol_weight']:.2%}")

    return {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "ok": ok,
        "soft_vetos": sorted(set(soft_vetos)),
        "reasons": reasons or ["limits ok"],
        "caps": caps,
        "summary": {
            "open_positions": npos,
            "total_notional_usd": total,
        }
    }

def reconcile_with_fills(positions: Dict[str, Any], fills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimal reconciliation: ensure all fills symbols appear in positions dict,
    and detect orphan fills (symbol not tracked) or negative qty.
    """
    anomalies = []
    symbols_in_fills = set()
    for f in fills:
        sym = f.get("symbol")
        if sym:
            symbols_in_fills.add(sym)

    for sym in symbols_in_fills:
        if sym not in positions:
            anomalies.append(f"fill_symbol_missing_in_positions: {sym}")

    for sym, p in positions.items():
        try:
            qty = float(p.get("qty", 0.0))
        except Exception:
            anomalies.append(f"invalid_qty: {sym}")
            continue
        if qty < 0:
            anomalies.append(f"negative_qty: {sym} qty={qty}")

    return {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "fills_seen": len(fills),
        "symbols_in_fills": sorted(symbols_in_fills),
        "anomalies": anomalies,
        "ok": len(anomalies) == 0,
    }

def apply_budget_cap(caps: dict, scope: str) -> dict:
    """
    Apply dynamic budget cap from pockets.json.
    - If governance caps exist, we keep the most conservative (min).
    - If missing, we set max_total_notional_usd = pocket budget.
    """
    budget = float(get_budget_usd(scope, default=0.0))
    if budget <= 0:
        return caps

    out = dict(caps or {})
    cur = out.get("max_total_notional_usd")
    try:
        cur_f = float(cur) if cur is not None else None
    except Exception:
        cur_f = None

    if cur_f is None or cur_f <= 0:
        out["max_total_notional_usd"] = budget
    else:
        out["max_total_notional_usd"] = min(cur_f, budget)

    return out

def main():
    positions = load_json(POSITIONS_PATH, default={}) or {}
    if not isinstance(positions, dict):
        positions = {}

    fills = read_jsonl(FILLS_PATH)

    gov = load_governance("equities_offensive")
    caps = extract_caps({"caps": gov.get("caps", {})})
    caps = apply_budget_cap(caps, scope='equities_offensive')

    exposure, by_symbol = compute_exposure(positions)
    limits = check_limits(exposure, by_symbol, caps)
    reco = reconcile_with_fills(positions, fills)

    # write outputs
    save_json(OUT_EXPOSURE, exposure)
    save_json(OUT_LIMITS, limits)

    pos_report = {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "positions_path": str(POSITIONS_PATH),
        "fills_path": str(FILLS_PATH),
        "reconciliation": reco,
        "note": "limits_report.soft_vetos can be consumed as soft-veto by risk/execution",
    }
    save_json(OUT_POS_REPORT, pos_report)

    print(json.dumps({
        "open_positions": exposure["open_positions"],
        "total_notional_usd": exposure["total_notional_usd"],
        "limits_ok": limits["ok"],
        "soft_vetos": limits["soft_vetos"],
        "reco_ok": reco["ok"],
        "anomalies": reco["anomalies"],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

