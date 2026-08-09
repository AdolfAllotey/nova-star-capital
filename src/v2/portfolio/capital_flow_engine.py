#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def save_json(path: Path, data: Any) -> None:
    _ensure_parent(path)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    _ensure_parent(path)
    line = json.dumps(event, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

@dataclass
class Phase:
    name: str
    min_equity: float
    max_equity: Optional[float]
    trading_pct: float
    lt_pct: float
    tax_pct: float

def default_phases() -> List[Phase]:
    """
    Phases (example) — adjust later in governance file if needed.
    Requirements you gave:
    - tax withheld on ALL gains, even before 5K
    - after 5K: ~70% trading
    - after 10K: ~60% trading
    - 4 phases visible in UI
    """
    return [
        Phase("Accélération", 0.0, 5000.0, 1.00, 0.00, 0.30),
        Phase("Équilibrage", 5000.0, 10000.0, 0.80, 0.20, 0.30),
        Phase("Structuration", 10000.0, 20000.0, 0.70, 0.30, 0.30),
        Phase("Maturité", 20000.0, None, 0.60, 0.40, 0.30),
    ]

def pick_phase(equity: float, phases: List[Phase]) -> Phase:
    for ph in phases:
        if equity >= ph.min_equity and (ph.max_equity is None or equity < ph.max_equity):
            return ph
    return phases[-1]

def compute_tax_withholding(realized_pnl: float, tax_pct: float) -> float:
    """
    Simple withholding: tax on positive realized pnl only.
    """
    if realized_pnl <= 0:
        return 0.0
    return realized_pnl * clamp(tax_pct, 0.0, 1.0)

def compute_budgets(
    equity: float,
    cash: float,
    phases: List[Phase],
) -> Dict[str, Any]:
    ph = pick_phase(equity, phases)
    budgets = {
        "phase": ph.name,
        "equity": equity,
        "cash": cash,
        "targets": {
            "trading": round(equity * ph.trading_pct, 2),
            "lt": round(equity * ph.lt_pct, 2)
        },
        "weights": {
            "trading_pct": ph.trading_pct,
            "lt_pct": ph.lt_pct
        },
        "tax_pct": ph.tax_pct
    }
    return budgets

def apply_daily_capital_flow(
    *,
    capital_state_path: str = "data/capital/capital_state.json",
    events_path: str = "data/capital/capital_events.jsonl",
    realized_pnl_today: float = 0.0,
    unrealized_pnl_today: float = 0.0,
    deposits: float = 0.0,
    withdrawals: float = 0.0,
    phases_override: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Updates capital_state with:
    - equity, cash
    - tax_reserved (withheld)
    - budgets per phase (trading vs LT)
    Emits append-only event lines.
    """
    state_p = Path(capital_state_path)
    events_p = Path(events_path)

    state = load_json(state_p, default={}) or {}
    cash = float(state.get("cash", 0.0))
    equity = float(state.get("equity", cash))  # if first run, equity=cash

    tax_reserved = float(state.get("tax_reserved", 0.0))
    tax_paid = float(state.get("tax_paid", 0.0))

    # Phase config
    phases: List[Phase] = []
    if phases_override:
        for d in phases_override:
            phases.append(
                Phase(
                    name=str(d["name"]),
                    min_equity=float(d["min_equity"]),
                    max_equity=(None if d.get("max_equity") is None else float(d["max_equity"])),
                    trading_pct=float(d["trading_pct"]),
                    lt_pct=float(d["lt_pct"]),
                    tax_pct=float(d.get("tax_pct", 0.30)),
                )
            )
    else:
        phases = default_phases()

    # Apply deposits/withdrawals to cash
    if deposits:
        cash += float(deposits)
        append_jsonl(events_p, {
            "ts": utc_now_iso(),
            "type": "deposit",
            "amount": deposits,
            "cash_after": cash
        })
    if withdrawals:
        cash -= float(withdrawals)
        append_jsonl(events_p, {
            "ts": utc_now_iso(),
            "type": "withdrawal",
            "amount": withdrawals,
            "cash_after": cash
        })

    # Realized PnL affects equity & cash (simplified: realized pnl is realized into cash)
    if realized_pnl_today:
        cash += float(realized_pnl_today)
        append_jsonl(events_p, {
            "ts": utc_now_iso(),
            "type": "realized_pnl",
            "amount": realized_pnl_today,
            "cash_after": cash
        })

    # Equity includes unrealized pnl (mark-to-market)
    equity = cash + float(unrealized_pnl_today)

    # Tax withholding on positive realized pnl (always, even before thresholds)
    ph_for_tax = pick_phase(equity, phases)
    tax_due = compute_tax_withholding(float(realized_pnl_today), ph_for_tax.tax_pct)
    if tax_due > 0:
        # Reserve tax from cash immediately (tax pocket)
        cash -= tax_due
        tax_reserved += tax_due
        append_jsonl(events_p, {
            "ts": utc_now_iso(),
            "type": "tax_withheld",
            "tax_pct": ph_for_tax.tax_pct,
            "amount": round(tax_due, 2),
            "tax_reserved_after": round(tax_reserved, 2),
            "cash_after": round(cash, 2)
        })

    # Recompute equity after tax reserve move
    equity = cash + float(unrealized_pnl_today)

    budgets = compute_budgets(equity, cash, phases)

    out = {
        "ts": utc_now_iso(),
        "equity": round(equity, 2),
        "cash": round(cash, 2),
        "unrealized_pnl_today": round(float(unrealized_pnl_today), 2),
        "realized_pnl_today": round(float(realized_pnl_today), 2),
        "tax_reserved": round(tax_reserved, 2),
        "tax_paid": round(tax_paid, 2),
        "phase": budgets["phase"],
        "budgets": budgets,
        "phases": [
            {
                "name": p.name,
                "min_equity": p.min_equity,
                "max_equity": p.max_equity,
                "trading_pct": p.trading_pct,
                "lt_pct": p.lt_pct,
                "tax_pct": p.tax_pct
            } for p in phases
        ]
    }

    save_json(state_p, out)

    append_jsonl(events_p, {
        "ts": utc_now_iso(),
        "type": "capital_state_updated",
        "phase": out["phase"],
        "equity": out["equity"],
        "cash": out["cash"],
        "tax_reserved": out["tax_reserved"],
        "budgets": out["budgets"]["targets"]
    })

    return out

# --- CLI

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NSC Capital Flow Engine (tax + phases + budgets)")
    ap.add_argument("--realized", type=float, default=0.0, help="Realized PnL today (USD/EUR consistent)")
    ap.add_argument("--unrealized", type=float, default=0.0, help="Unrealized PnL today")
    ap.add_argument("--deposit", type=float, default=0.0, help="Deposit amount")
    ap.add_argument("--withdraw", type=float, default=0.0, help="Withdraw amount")
    ap.add_argument("--state", default="data/capital/capital_state.json", help="Capital state path")
    ap.add_argument("--events", default="data/capital/capital_events.jsonl", help="Events jsonl path")
    args = ap.parse_args()

    out = apply_daily_capital_flow(
        capital_state_path=args.state,
        events_path=args.events,
        realized_pnl_today=args.realized,
        unrealized_pnl_today=args.unrealized,
        deposits=args.deposit,
        withdrawals=args.withdraw
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()


# ==========================
# NSC PROFIT FLOW V2
# ==========================

from pathlib import Path

POLICY_PATH = Path("/opt/nsc/app/src/v2/config/profit_distribution_policy.json")


def load_policy():
    with open(POLICY_PATH, "r") as f:
        return json.load(f)


def get_applicable_tier(capital, tiers):
    applicable = tiers[0]
    for tier in tiers:
        if capital >= tier["min_capital_eur"]:
            applicable = tier
    return applicable


def compute_profit_flow(brick, profit_eur, capital_eur):
    policy = load_policy()

    tax_rate = policy["tax"]["rate"]
    tiers = policy["tiers"]
    split = policy["distribution_split"]

    # Fail-safe contract:
    # losses and zero profit never generate tax withholding,
    # reinvestment or downstream distributions.
    if profit_eur <= 0:
        return {
            "brick": brick,
            "input_profit": profit_eur,
            "tax": 0.0,
            "net_profit": 0.0,
            "trading_reinvested": 0.0,
            "distributed": {
                "lt": 0.0,
                "bfr": 0.0,
                "security": 0.0,
            },
        }

    # 1. TAX
    tax_amount = profit_eur * tax_rate
    net_profit = profit_eur - tax_amount

    # 2. TIER
    tier = get_applicable_tier(capital_eur, tiers)

    trading_part = net_profit * tier["trading"]
    distribution_part = net_profit * tier["distribution"]

    # 3. SPLIT
    flows = {
        "brick": brick,
        "input_profit": profit_eur,
        "tax": tax_amount,
        "net_profit": net_profit,
        "trading_reinvested": trading_part,
        "distributed": {
            "lt": distribution_part * split["lt"],
            "bfr": distribution_part * split["bfr"],
            "security": distribution_part * split["security"]
        }
    }

    return flows

