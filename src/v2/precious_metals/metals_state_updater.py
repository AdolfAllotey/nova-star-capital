from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SIGNAL_PATH = Path("/opt/nsc/data/preprod/metals/metals_signal.json")
STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")
PRICES_PATH = Path("/opt/nsc/data/preprod/metals/prices.json")
OUT_PATH = Path("/opt/nsc/data/preprod/metals/metals_state.json")


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


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    signal = load_json(SIGNAL_PATH, {}) or {}
    portfolio_state = load_json(STATE_PATH, {}) or {}
    prices = load_json(PRICES_PATH, {}) or {}

    metals = (portfolio_state.get("bricks", {}) or {}).get("precious_metals", {}) or {}
    target_amount = float(metals.get("target_amount_eur", 0.0) or 0.0)
    allocation = signal.get("allocation", {}) or {}

    positions = []
    total_value = 0.0

    for symbol, weight in allocation.items():
        try:
            w = float(weight or 0.0)
            px = float(prices.get(symbol, 0.0) or 0.0)
            if w <= 0 or px <= 0:
                continue

            amount_eur = round(target_amount * w, 2)
            qty = round(amount_eur / px, 8)

            previous_positions = load_json(OUT_PATH, {}) or {}
            previous_rows = previous_positions.get("positions", []) if isinstance(previous_positions, dict) else []
            previous_by_symbol = {
                str(r.get("symbol", "")).upper(): r
                for r in previous_rows
                if isinstance(r, dict)
            }
            prev = previous_by_symbol.get(symbol, {})
            avg_price = float(prev.get("avg_price", prev.get("price", px)) or px)
            cost_basis = round(qty * avg_price, 2)
            current_value = round(qty * px, 2)
            unrealized_pnl = round(current_value - cost_basis, 2)
            pnl_pct = round((unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0, 6)

            positions.append({
                "symbol": symbol,
                "weight": round(w, 6),
                "price": px,
                "avg_price": round(avg_price, 6),
                "qty": qty,
                "cost_basis_eur": cost_basis,
                "value_eur": current_value,
                "unrealized_pnl_eur": unrealized_pnl,
                "pnl_pct": pnl_pct,
            })
            total_value += current_value
        except Exception:
            continue

    payload = {
        "status": "ok",
        "engine": "metals_state_updater_v1",
        "generated_at": now_iso(),
        "brick": "precious_metals",
        "regime": signal.get("regime", "unknown"),
        "confidence": signal.get("confidence", 0.0),
        "target_exposure": signal.get("target_exposure", 0.0),
        "target_amount_eur": round(target_amount, 2),
        "current_exposure_eur": round(total_value, 2),
        "cost_basis_eur": round(sum(float(p.get("cost_basis_eur", 0.0) or 0.0) for p in positions), 2),
        "realized_pnl_eur": 0.0,
        "unrealized_pnl_eur": round(sum(float(p.get("unrealized_pnl_eur", 0.0) or 0.0) for p in positions), 2),
        "pnl_eur": round(sum(float(p.get("unrealized_pnl_eur", 0.0) or 0.0) for p in positions), 2),
        "mark_to_market": True,
        "positions": positions,
    }

    save_json(OUT_PATH, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
