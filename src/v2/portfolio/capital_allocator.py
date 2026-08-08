from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("capital_allocator")

POLICY_PATH = Path("/opt/nsc/app/data/portfolio/capital_flow_policy.json")
MASTER_CASH_PATH = Path("/opt/nsc/data/preprod/portfolio/capital_state.json")
POCKETS_PATH = Path("/opt/nsc/data/preprod/portfolio/pockets.json")

TRANSFERS_JSONL = Path("/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl")
EVENTS_TRANSFERS_JSONL = Path("/opt/nsc/data/preprod/events/capital_transfers.jsonl")

BRICKS = [
    "crypto",
    "equities_offensive",
    "equities_defensive",
    "bonds",
    "metals",
    "options_us",
]

TAX_POCKET = "tax_reserve"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def _float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def load_policy() -> Dict[str, Any]:
    pol = load_json_file(str(POLICY_PATH), default={}) or {}
    if not isinstance(pol, dict):
        return {}
    return pol

def pick_phase(policy: Dict[str, Any], total_usd: float) -> Dict[str, Any]:
    phases = policy.get("phases", [])
    if not isinstance(phases, list):
        return {}
    for ph in phases:
        if not isinstance(ph, dict):
            continue
        mn = _float(ph.get("min_total_usd", ph.get("min_total_eur", 0)))
        mx = _float(ph.get("max_total_usd", ph.get("max_total_eur", 1e18)))
        if mn <= total_usd < mx:
            return ph
    return phases[-1] if phases else {}

def load_master_cash() -> Dict[str, Any]:
    return load_json_file(str(MASTER_CASH_PATH), default={"total_capital_eur": 0.0, "currency": "EUR"}) or {}

def load_pockets() -> Dict[str, Any]:
    default = {"currency": "EUR", "pockets": {b: {"budget_eur": 0.0} for b in BRICKS}}
    p = load_json_file(str(POCKETS_PATH), default=default) or default
    if "pockets" not in p or not isinstance(p.get("pockets"), dict):
        p["pockets"] = {b: {"budget_eur": 0.0} for b in BRICKS}
    return p

def compute_targets(total_usd: float, phase: Dict[str, Any]) -> Dict[str, float]:
    targets = phase.get("targets", {}) if isinstance(phase.get("targets"), dict) else {}
    out = {b: 0.0 for b in BRICKS}
    for b in BRICKS:
        out[b] = _float(targets.get(b, 0.0), 0.0)
    # normalize if needed
    s = sum(out.values())
    if s > 0 and abs(s - 1.0) > 1e-6:
        out = {k: v / s for k, v in out.items()}
    return {b: total_usd * out[b] for b in BRICKS}

def compute_transfers(
    current: Dict[str, float],
    target: Dict[str, float],
    tolerance_pct: float,
    min_transfer_usd: float,
) -> List[Dict[str, Any]]:
    """
    Produce simple transfers between pockets to move toward target.
    We compute deltas and match surplus -> deficit.
    """
    deltas = {b: target[b] - current.get(b, 0.0) for b in BRICKS}
    total = max(1.0, sum(current.values()))
    tol_abs = tolerance_pct * total

    deficits = [(b, d) for b, d in deltas.items() if d > max(tol_abs, min_transfer_usd)]
    surpluses = [(b, -d) for b, d in deltas.items() if d < -max(tol_abs, min_transfer_usd)]

    deficits.sort(key=lambda x: x[1], reverse=True)
    surpluses.sort(key=lambda x: x[1], reverse=True)

    transfers: List[Dict[str, Any]] = []
    i = j = 0
    while i < len(surpluses) and j < len(deficits):
        src, avail = surpluses[i]
        dst, need = deficits[j]
        amt = min(avail, need)
        if amt >= min_transfer_usd:
            transfers.append({"from": src, "to": dst, "amount_eur": round(amt, 2)})
        avail -= amt
        need -= amt
        surpluses[i] = (src, avail)
        deficits[j] = (dst, need)
        if avail <= min_transfer_usd:
            i += 1
        if need <= min_transfer_usd:
            j += 1

    return transfers

def run() -> Dict[str, Any]:
    policy = load_policy()
    master = load_master_cash()
    pockets = load_pockets()

    currency = master.get("currency", pockets.get("currency", "EUR"))
    cash_total = _float(master.get("deployable_capital_eur", master.get("total_capital_eur", master.get("cash_total", 0.0))))

    # In ARCH-005, total_usd is master cash only (positions reconciliation later).
    total_usd = cash_total

    phase = pick_phase(policy, total_usd)
    phase_name = phase.get("name", "UNKNOWN")

    rb = policy.get("rebalance", {}) if isinstance(policy.get("rebalance"), dict) else {}
    tolerance_pct = _float(rb.get("tolerance_pct", 0.02), 0.02)
    min_transfer_usd = _float(rb.get("min_transfer_usd", 50), 50)

    # Current budgets
    cur_pockets = pockets.get("pockets", {})
    current = {b: _float(cur_pockets.get(b, {}).get("budget_eur", cur_pockets.get(b, {}).get("budget_usd", 0.0))) for b in BRICKS}

    # Targets
    targets = compute_targets(total_usd, phase)

    transfers = compute_transfers(current, targets, tolerance_pct, min_transfer_usd)

    ts = utc_now()
    snapshot = {
        "ts": ts,
        "engine": "capital_allocator_v1",
        "currency": currency,
        "total_eur": round(total_usd, 2),
        "phase": phase_name,
        "targets_eur": {b: round(targets[b], 2) for b in BRICKS},
        "current_eur": {b: round(current[b], 2) for b in BRICKS},
        "transfers": transfers,
        "notes": [
            "ARCH-005: targets computed from master cash only (positions reconciliation will be added later).",
            "Transfers are instructions; execution is handled by broker/treasury layer later."
        ]
    }

    # Apply targets immediately to pockets (budget view), and record transfers as instructions.
    new_pockets = {
        "ts": ts,
        "engine": "pockets_v1",
        "currency": currency,
        "pockets": {b: {"budget_eur": round(targets[b], 2)} for b in BRICKS},
    }
    save_json_file(str(POCKETS_PATH), new_pockets)

    for t in transfers:
        instr = {"ts": ts, "engine": "transfer_instruction_v1", **t, "phase": phase_name}
        append_jsonl(TRANSFERS_JSONL, instr)
        append_jsonl(EVENTS_TRANSFERS_JSONL, instr)

    logger.info("capital_allocator done: phase=%s transfers=%d", phase_name, len(transfers))
    return snapshot

if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2, ensure_ascii=False))
