from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SIGNAL_PATH = Path("/opt/nsc/app/data/metals/metals_signal.json")
PRICES_PATH = Path("/opt/nsc/data/preprod/metals/prices.json")
FILLS_PATH = Path("/opt/nsc/app/data/metals/execution/simulated_fills.jsonl")
POSITIONS_PATH = Path("/opt/nsc/app/data/metals/state/positions.json")
EXPOSURE_PATH = Path("/opt/nsc/app/data/metals/state/exposure_snapshot.json")
PORTFOLIO_STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_positions():
    return load_json(POSITIONS_PATH, default={}) or {}


def save_positions(doc):
    save_json(POSITIONS_PATH, doc)


def build_exposure_snapshot(positions: dict, prices: dict):
    total = 0.0
    lines = []
    for sym, row in positions.items():
        try:
            qty = float(row.get("qty", 0.0) or 0.0)
            avg = float(row.get("avg_price", 0.0) or 0.0)
            px = float(prices.get(sym, avg) or avg)
        except Exception:
            continue
        if qty <= 0:
            continue
        notional = round(qty * px, 2)
        total += notional
        lines.append({
            "symbol": sym,
            "qty": qty,
            "avg_price": avg,
            "price": px,
            "notional_eur": notional,
        })

    snap = {
        "ts": now_iso(),
        "engine": "metals_simulated_broker_v1",
        "open_positions": len(lines),
        "total_notional_eur": round(total, 2),
        "positions": lines,
    }
    save_json(EXPOSURE_PATH, snap)
    return snap


def main():
    signal = load_json(SIGNAL_PATH, default={}) or {}
    prices = load_json(PRICES_PATH, default={}) or {}
    portfolio_state = load_json(PORTFOLIO_STATE_PATH, default={}) or {}
    positions = load_positions()
    portfolio_regime = str(portfolio_state.get("portfolio_regime", "unknown")).lower()

    metals = ((portfolio_state.get("bricks", {}) or {}).get("precious_metals", {}) or {})
    target_amount = float(metals.get("target_amount_eur", 0.0) or 0.0)
    allocation = signal.get("allocation", {}) or {}
    target_exposure = float(signal.get("target_exposure", 0.0) or 0.0)

    if portfolio_regime != "risk_off":
        for sym, prev in positions.items():
            try:
                prev_qty = float(prev.get("qty", 0.0) or 0.0)
                px = float(prices.get(sym, prev.get("avg_price", 0.0)) or prev.get("avg_price", 0.0) or 0.0)
            except Exception:
                continue
            if prev_qty > 0 and px > 0:
                append_jsonl(FILLS_PATH, {
                    "ts": now_iso(),
                    "engine": "regime_gate_flatten_v1",
                    "symbol": sym,
                    "side": "SELL",
                    "qty": round(prev_qty, 8),
                    "fill_price": px,
                    "status": "FILLED",
                    "regime": portfolio_regime,
                    "reason": "portfolio_regime_not_risk_off",
                })
        positions = {}
        save_positions(positions)
        snap = build_exposure_snapshot(positions, prices)
        print(json.dumps({
            "status": "ok",
            "action": "gated_flat",
            "portfolio_regime": portfolio_regime,
            "allowed_regime": "risk_off",
            "snapshot": snap
        }, indent=2, ensure_ascii=False))
        return

    if target_exposure <= 0:
        positions = {}
        save_positions(positions)
        snap = build_exposure_snapshot(positions, prices)
        print(json.dumps({"status": "ok", "action": "flat", "snapshot": snap}, indent=2, ensure_ascii=False))
        return

    new_positions = {}

    for sym, weight in allocation.items():
        try:
            w = float(weight or 0.0)
            px = float(prices.get(sym, 0.0) or 0.0)
        except Exception:
            continue
        if w <= 0 or px <= 0:
            continue

        amount = round(target_amount * w, 2)
        qty = round(amount / px, 8)

        prev = positions.get(sym, {})
        prev_qty = float(prev.get("qty", 0.0) or 0.0)

        if abs(qty - prev_qty) > 1e-9:
            side = "BUY" if qty > prev_qty else "SELL"
            fill_qty = round(abs(qty - prev_qty), 8)

            append_jsonl(FILLS_PATH, {
                "ts": now_iso(),
                "engine": "metals_simulated_broker_v1",
                "symbol": sym,
                "side": side,
                "qty": fill_qty,
                "fill_price": px,
                "status": "FILLED",
                "regime": signal.get("regime", "unknown"),
            })

        new_positions[sym] = {
            "qty": qty,
            "avg_price": px if qty > 0 else float(prev.get("avg_price", 0.0) or 0.0),
        }

    save_positions(new_positions)
    snap = build_exposure_snapshot(new_positions, prices)

    print(json.dumps({
        "status": "ok",
        "engine": "metals_simulated_broker_v1",
        "target_amount_eur": target_amount,
        "positions_written": len(new_positions),
        "snapshot": snap,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
