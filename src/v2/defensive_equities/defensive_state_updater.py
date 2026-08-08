from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import os

ROOT = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

SIGNAL_PATH = ROOT / "defensive/defensive_signal.json"
STATE_PATH = ROOT / "portfolio/state/portfolio_state.json"
PRICES_PATH = ROOT / "defensive/prices.json"
OUT_PATH = ROOT / "defensive/defensive_state.json"


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

    defensive = (portfolio_state.get("bricks", {}) or {}).get("equities_defensive", {}) or {}
    target_exposure = float(signal.get("target_exposure", 0.0) or 0.0)

    target_amount = float(defensive.get("target_amount_eur", 0.0) or 0.0)

    # Fallback robuste : si le master state est stale ou à zéro,
    # on calcule le montant cible depuis le capital observé.
    if target_amount <= 0 and target_exposure > 0:
        capital_state = load_json(ROOT / "portfolio/capital_state.json", {}) or {}
        total_capital = float(
            capital_state.get("total_capital_eur")
            or capital_state.get("deployable_capital_eur")
            or portfolio_state.get("total_value_eur")
            or 10000.0
        )
        target_amount = round(total_capital * target_exposure, 2)

    proposed_assets = signal.get("proposed_assets", []) or []

    positions = []
    total_value = 0.0

    for row in proposed_assets:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("ticker", "")).strip().upper()
        if not symbol:
            continue
        try:
            weight = float(row.get("weight", 0.0) or 0.0)
            px = float(prices.get(symbol, 0.0) or 0.0)
            if weight <= 0 or px <= 0:
                continue

            amount_eur = round(target_amount * weight, 2)
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
                "weight": round(weight, 6),
                "price": px,
                "avg_price": round(avg_price, 6),
                "qty": qty,
                "cost_basis_eur": cost_basis,
                "value_eur": current_value,
                "unrealized_pnl_eur": unrealized_pnl,
                "pnl_pct": pnl_pct,
                "type": row.get("type"),
                "sector": row.get("sector"),
                "region": row.get("region"),
            })
            total_value += current_value
        except Exception:
            continue

    payload = {
        "status": "ok",
        "engine": "defensive_state_updater_v1",
        "generated_at": now_iso(),
        "brick": "defensive_equities",
        "regime": defensive.get("regime", signal.get("mode", "stabilization_active")),
        "confidence": float(defensive.get("confidence", signal.get("confidence", 0.0)) or 0.0),
        "target_exposure": target_exposure,
        "target_amount_eur": round(target_amount, 2),
        "current_exposure_eur": round(total_value, 2),
        "cost_basis_eur": round(sum(float(p.get("cost_basis_eur", 0.0) or 0.0) for p in positions), 2),
        "realized_pnl_eur": 0.0,
        "unrealized_pnl_eur": round(sum(float(p.get("unrealized_pnl_eur", 0.0) or 0.0) for p in positions), 2),
        "pnl_eur": round(sum(float(p.get("unrealized_pnl_eur", 0.0) or 0.0) for p in positions), 2),
        "mark_to_market": True,
        "positions": positions,
        "constraints_respected": (signal.get("score_summary", {}) or {}).get("constraints_respected"),
        "portfolio_beta_estimate": (signal.get("score_summary", {}) or {}).get("portfolio_beta_estimate"),
        "positions_count": len(positions),
    }

    save_json(OUT_PATH, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
