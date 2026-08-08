from __future__ import annotations

import json
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger
from src.v2.portfolio.capital_allocator import run as run_capital_allocator

logger = get_logger("multi_asset_orchestrator")

GOV_PATH = Path("data/governance/governance_engine_pro.json")
REGIME_PATH = Path("data/market/market_regime.json")
MASTER_CASH_PATH = Path("/opt/nsc/data/preprod/portfolio/capital_state.json")
POCKETS_PATH = Path("/opt/nsc/data/preprod/portfolio/pockets.json")
TRANSFERS_JSONL = Path("/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl")
EVENTS_TRANSFERS_JSONL = Path("/opt/nsc/data/preprod/events/capital_transfers.jsonl")
ORCH_SNAPSHOT_PATH = Path("data/orchestrator/orchestrator_snapshot.json")
ORCH_AUDIT_JSONL = Path("data/orchestrator/orchestrator_audit.jsonl")

BRICKS = [
    "crypto",
    "equities_offensive",
    "equities_defensive",
    "bonds",
    "metals",
    "options_us",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_governance() -> Dict[str, Any]:
    gov = load_json_file(str(GOV_PATH), default={}) or {}
    if not isinstance(gov, dict):
        return {}
    return gov


def scope_cfg(gov: Dict[str, Any], scope: str) -> Dict[str, Any]:
    scopes = gov.get("scopes", {})
    if isinstance(scopes, dict) and isinstance(scopes.get(scope), dict):
        return scopes[scope]
    return {}


def get_policy(gov: Dict[str, Any], scope: str) -> str:
    sc = scope_cfg(gov, scope)
    return (sc.get("action_policy") or gov.get("action_policy") or "SIMULATED_ONLY")


def get_enabled(gov: Dict[str, Any], scope: str) -> bool:
    sc = scope_cfg(gov, scope)
    return bool(sc.get("enabled", True))


def read_master_cash() -> Dict[str, Any]:
    return load_json_file(str(MASTER_CASH_PATH), default={"total_capital_eur": 0.0, "currency": "EUR"}) or {}


def read_pockets() -> Dict[str, Any]:
    default = {"currency": "EUR", "pockets": {b: {"budget_eur": 0.0} for b in BRICKS}}
    return load_json_file(str(POCKETS_PATH), default=default) or default


def compute_budgets(
    gov: Dict[str, Any],
    regime: Dict[str, Any],
    master_cash: Dict[str, Any],
    pockets_prev: Dict[str, Any],
) -> Dict[str, float]:
    """
    Version minimaliste (ARCH-003):
    - budgets = pockets existants (pas de redistribution automatique ici)
    - le rôle du king: enable/disable + policy visible dans snapshot
    - la redistribution viendra dans ARCH-005 (capital allocator multi-phases)
    """
    budgets: Dict[str, float] = {}
    prev = pockets_prev.get("pockets", {}) if isinstance(pockets_prev.get("pockets"), dict) else {}
    for b in BRICKS:
        budgets[b] = float(prev.get(b, {}).get("budget_eur", prev.get(b, {}).get("budget_usd", 0.0)) or 0.0)
    return budgets


def write_pockets(budgets: Dict[str, float], currency: str = "EUR") -> None:
    obj = {
        "ts": utc_now(),
        "engine": "pockets_v1",
        "currency": currency,
        "pockets": {b: {"budget_eur": float(budgets.get(b, 0.0))} for b in BRICKS},
    }
    save_json_file(str(POCKETS_PATH), obj)


def run() -> Dict[str, Any]:
    gov = load_governance()
    regime = load_json_file(str(REGIME_PATH), default={}) or {}
    master_cash = read_master_cash()
    pockets_prev = read_pockets()

    budgets = compute_budgets(gov, regime, master_cash, pockets_prev)

    # Snapshot orchestration
    snapshot = {
        "ts": utc_now(),
        "engine": "multi_asset_orchestrator_v1",
        "regime": regime.get("regime"),
        "regime_confidence": regime.get("confidence"),
        "master_cash": {
            "currency": master_cash.get("currency", "EUR"),
            "cash_total": float(master_cash.get("deployable_capital_eur", master_cash.get("total_capital_eur", master_cash.get("cash_total", 0.0))) or 0.0),
        },
        "scopes": {
            b: {
                "enabled": get_enabled(gov, b),
                "action_policy": get_policy(gov, b),
                "budget_eur": float(budgets.get(b, 0.0)),
            }
            for b in BRICKS
        },
        "notes": [
            "ARCH-003: orchestrator computes/exports budgets only. Transfers & reallocations come in ARCH-005."
        ],
    }

    # Write outputs
    write_pockets(budgets, currency=master_cash.get("currency", "EUR"))
    save_json_file(str(ORCH_SNAPSHOT_PATH), snapshot)
    append_jsonl(ORCH_AUDIT_JSONL, {"ts": snapshot["ts"], "event": "orchestrator_run", "snapshot_path": str(ORCH_SNAPSHOT_PATH)})

    logger.info("Orchestrator snapshot written: %s", ORCH_SNAPSHOT_PATH)
    return snapshot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocate", action="store_true", help="Run capital allocator before snapshot")
    args = ap.parse_args()

    if args.allocate:
        run_capital_allocator()

    out = run()
    print(json.dumps(out, indent=2, ensure_ascii=False))
