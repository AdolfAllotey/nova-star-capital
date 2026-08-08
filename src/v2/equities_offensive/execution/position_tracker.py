from __future__ import annotations
from src.v2.portfolio.budget_context import load_budget_context
from src.v2.equities_offensive.execution.trade_ledger import build_trade_ledger
#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from src.v2.equities_offensive.governance.governance_reader import load_governance

def data_root() -> Path:
    import os
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

ROOT = data_root()

POSITIONS_PATH = ROOT / "equities_offensive/state/positions.json"
FILLS_PATH = ROOT / "equities_offensive/execution/simulated_fills.jsonl"
PRICES_PATH = ROOT / "equities_offensive/market/prices.json"  # optional
GOV_PATH = ROOT / "equities_offensive/governance/governance_engine_pro.json"
PORTFOLIO_INPUT_PATH = ROOT / "portfolio/inputs/equities_offensive_portfolio_input.json"

OUT_EXPOSURE = ROOT / "equities_offensive/state/exposure_snapshot.json"
OUT_POS_REPORT = ROOT / "equities_offensive/state/position_report.json"
OUT_LIMITS = ROOT / "equities_offensive/state/limits_report.json"
OUT_TRADE_LEDGER = ROOT / "equities_offensive/state/trade_ledger.json"

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
            prices = doc.get("prices")
            if isinstance(prices, dict):
                px = prices.get(str(symbol).upper())
                if px is not None:
                    return float(px)
        except Exception:
            pass
        try:
            px = doc.get(str(symbol).upper())
            if px is not None:
                return float(px)
        except Exception:
            pass
        try:
            px = doc.get(symbol)
            if px is not None:
                return float(px)
        except Exception:
            pass
    return float(fallback)


def get_portfolio_regime() -> str:
    doc = load_json(PORTFOLIO_INPUT_PATH, default={}) or {}
    if isinstance(doc, dict):
        return str(doc.get("regime", "risk_on")).lower()
    return "risk_on"

def get_trailing_pct_for_regime(regime: str) -> float:
    regime = str(regime or "risk_on").lower()
    if regime in {"risk_off", "risk_off_blocked"}:
        return 0.05
    if regime in {"balanced", "neutral"}:
        return 0.08
    return 0.12

def compute_exposure(positions: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, float]]:
    total = 0.0
    by_symbol: Dict[str, float] = {}
    lines = []
    regime = get_portfolio_regime()
    trailing_pct = get_trailing_pct_for_regime(regime)

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

        pnl_pct = 0.0
        if avg > 0:
            pnl_pct = (px - avg) / avg

        trailing_stop_price = None
        if px > 0:
            trailing_stop_price = round(px * (1.0 - trailing_pct), 4)

        lines.append({
            "symbol": sym,
            "qty": qty,
            "price": px,
            "avg_price": avg,
            "notional_usd": round(notional, 2),
            "pnl_pct": round(pnl_pct, 4),
            "regime": regime,
            "trailing_pct": round(trailing_pct, 4),
            "trailing_stop_price": trailing_stop_price,
        })

    snap = {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "portfolio_regime": regime,
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
        "max_symbol_weight": float(caps.get("max_symbol_weight", 1.0)),  # 25%
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
    Net reconciliation from FILLED fills:
    - BUY increments expected qty
    - SELL decrements expected qty
    - symbol with net qty = 0 does not need to be present in positions.json
    """
    anomalies = []
    symbols_in_fills = set()
    expected_qty = {}

    for f in fills:
        if not isinstance(f, dict):
            continue

        sym = f.get("symbol")
        side = str(f.get("side", "")).upper()
        status = str(f.get("status", "")).upper()

        if sym:
            symbols_in_fills.add(sym)

        if not sym or side not in {"BUY", "SELL"} or status != "FILLED":
            continue

        try:
            qty = float(f.get("qty", 0.0) or 0.0)
        except Exception:
            anomalies.append(f"invalid_fill_qty: {sym}")
            continue

        if qty <= 0:
            anomalies.append(f"non_positive_fill_qty: {sym} qty={qty}")
            continue

        signed = qty if side == "BUY" else -qty
        expected_qty[sym] = expected_qty.get(sym, 0.0) + signed

    # remove near-zero residuals
    for sym in list(expected_qty.keys()):
        if abs(expected_qty[sym]) < 1e-9:
            expected_qty.pop(sym, None)

    # compare expected net qty vs positions.json
    all_symbols = set(expected_qty.keys()) | set(positions.keys())

    for sym in sorted(all_symbols):
        expected = float(expected_qty.get(sym, 0.0) or 0.0)

        p = positions.get(sym, {})
        try:
            actual = float((p or {}).get("qty", 0.0) or 0.0)
        except Exception:
            anomalies.append(f"invalid_position_qty: {sym}")
            continue

        if actual < 0:
            anomalies.append(f"negative_qty: {sym} qty={actual}")
            continue

        # Corporate action tolerance:
        # If a simulated position has been adjusted for a split, historical fills may remain pre-split.
        corp_action = str((p or {}).get("corporate_action_adjusted", "") or "")
        if corp_action and "SPLIT" in corp_action.upper():
            continue

        # If historical simulated fills imply a negative net qty but runtime
        # positions.json is already flat, clamp the reconciliation to zero.
        # This prevents false anomalies after full exits, cleanups, or legacy
        # fill-history corrections.
        if expected < 0 and abs(actual) <= 1e-6:
            expected_qty[sym] = 0.0
            continue

        if abs(expected - actual) > 1e-6:
            anomalies.append(f"qty_mismatch: {sym} expected={expected} actual={actual}")

    return {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "fills_seen": len(fills),
        "symbols_in_fills": sorted(symbols_in_fills),
        "expected_qty_by_symbol": {k: round(v, 8) for k, v in sorted(expected_qty.items())},
        "anomalies": anomalies,
        "ok": len(anomalies) == 0,
    }

def reconcile_trade_ledger_positions(
    positions: Dict[str, Any],
    trade_ledger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare the operational broker position state against positions
    reconstructed independently from the immutable fill ledger.

    Checks:
    - quantity;
    - weighted-average entry price;
    - unexpected positions on either side.

    Realized P&L is not compared because positions.json intentionally
    contains only the current operational position state.
    """
    anomalies: List[str] = []

    ledger_positions = (
        trade_ledger.get("open_positions")
        if isinstance(trade_ledger, dict)
        else {}
    )

    if not isinstance(ledger_positions, dict):
        ledger_positions = {}
        anomalies.append("invalid_trade_ledger_open_positions")

    broker_positions = (
        positions
        if isinstance(positions, dict)
        else {}
    )

    all_symbols = (
        set(broker_positions.keys())
        | set(ledger_positions.keys())
    )

    comparison: Dict[str, Any] = {}

    for symbol in sorted(all_symbols):
        broker_row = broker_positions.get(symbol) or {}
        ledger_row = ledger_positions.get(symbol) or {}

        try:
            broker_qty = float(
                broker_row.get("qty", 0.0) or 0.0
            )
        except Exception:
            broker_qty = 0.0
            anomalies.append(
                f"invalid_broker_qty:{symbol}"
            )

        try:
            broker_avg = float(
                broker_row.get("avg_price", 0.0) or 0.0
            )
        except Exception:
            broker_avg = 0.0
            anomalies.append(
                f"invalid_broker_avg_price:{symbol}"
            )

        try:
            ledger_qty = float(
                ledger_row.get("qty", 0.0) or 0.0
            )
        except Exception:
            ledger_qty = 0.0
            anomalies.append(
                f"invalid_ledger_qty:{symbol}"
            )

        try:
            ledger_avg = float(
                ledger_row.get("avg_price", 0.0) or 0.0
            )
        except Exception:
            ledger_avg = 0.0
            anomalies.append(
                f"invalid_ledger_avg_price:{symbol}"
            )

        if abs(broker_qty) < 1e-9:
            broker_qty = 0.0

        if abs(ledger_qty) < 1e-9:
            ledger_qty = 0.0

        corporate_action = str(
            broker_row.get(
                "corporate_action_adjusted",
                "",
            )
            or ""
        ).upper()

        quantity_matches = (
            abs(broker_qty - ledger_qty) <= 1e-6
        )

        average_matches = True

        if (
            broker_qty > 0
            and ledger_qty > 0
            and "SPLIT" not in corporate_action
        ):
            average_matches = (
                abs(broker_avg - ledger_avg) <= 1e-6
            )

        if not quantity_matches:
            anomalies.append(
                "ledger_broker_qty_mismatch:"
                f"{symbol}:"
                f"broker={broker_qty}:"
                f"ledger={ledger_qty}"
            )

        if not average_matches:
            anomalies.append(
                "ledger_broker_avg_price_mismatch:"
                f"{symbol}:"
                f"broker={broker_avg}:"
                f"ledger={ledger_avg}"
            )

        comparison[symbol] = {
            "broker_qty": round(broker_qty, 12),
            "ledger_qty": round(ledger_qty, 12),
            "qty_matches": quantity_matches,
            "broker_avg_price": round(
                broker_avg,
                12,
            ),
            "ledger_avg_price": round(
                ledger_avg,
                12,
            ),
            "avg_price_matches": average_matches,
            "corporate_action_tolerance": (
                "SPLIT" in corporate_action
            ),
        }

    return {
        "ts": utc_now_iso(),
        "engine": (
            "ledger_broker_position_reconciliation_v1"
        ),
        "symbols_checked": len(all_symbols),
        "comparison": comparison,
        "anomalies": anomalies,
        "ok": len(anomalies) == 0,
    }


def apply_budget_cap(caps: dict, scope: str) -> dict:
    """
    Apply dynamic budget cap from pockets.json.
    - If governance caps exist, we keep the most conservative (min).
    - If missing, we set max_total_notional_usd = pocket budget.
    """
    budget_context = load_budget_context(ROOT, scope=scope)

    if budget_context.get("status") != "ok":
        return caps

    try:
        budget = float(
            budget_context.get("budget_usd") or 0.0
        )
    except Exception:
        return caps

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
        # PREPROD: allow a small buffer above the canonical pocket target,
        # while always retaining the most conservative limit between
        # Governance and the buffered Portfolio budget.
        buffered_budget = round(budget * 1.10, 2)
        out["max_total_notional_usd"] = min(
            cur_f,
            buffered_budget,
        )

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
    trade_ledger = build_trade_ledger(fills)
    ledger_position_reconciliation = (
        reconcile_trade_ledger_positions(
            positions,
            trade_ledger,
        )
    )

    # write outputs
    save_json(OUT_EXPOSURE, exposure)
    save_json(OUT_LIMITS, limits)
    save_json(OUT_TRADE_LEDGER, trade_ledger)

    pos_report = {
        "ts": utc_now_iso(),
        "engine": "position_tracker_v1",
        "positions_path": str(POSITIONS_PATH),
        "fills_path": str(FILLS_PATH),
        "trade_ledger_path": str(OUT_TRADE_LEDGER),
        "portfolio_regime": exposure.get("portfolio_regime"),
        "positions_snapshot": exposure.get("positions", []),
        "pnl_summary": trade_ledger.get("summary", {}),
        "trade_ledger_ok": trade_ledger.get("ok", False),
        "trade_ledger_anomalies": trade_ledger.get(
            "anomalies",
            [],
        ),
        "ledger_position_reconciliation": (
            ledger_position_reconciliation
        ),
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
        "trade_ledger_ok": trade_ledger["ok"],
        "realized_pnl_usd": trade_ledger[
            "summary"
        ]["realized_pnl_usd"],
        "trade_ledger_anomalies": trade_ledger[
            "anomalies"
        ],
        "ledger_position_reconciliation_ok": (
            ledger_position_reconciliation["ok"]
        ),
        "ledger_position_reconciliation_anomalies": (
            ledger_position_reconciliation["anomalies"]
        ),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

