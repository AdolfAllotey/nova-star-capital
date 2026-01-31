import os
from pathlib import Path
import logging as _logging

from src.utils.telegram_bot import send_telegram_message

from src.v2.utils.file_utils import get_data_dir, load_json_file, load_effective_execution_plan

# Optional (preferred): central logger
try:
    from src.v2.utils.logger import get_logger  # type: ignore
    logger = get_logger("trading_executor")
except Exception:
    logger = _logging.getLogger(__name__)
    if not logger.handlers:
        _logging.basicConfig(level=_logging.INFO)

# Exchange router (single entrypoint to exchanges)
from src.v2.integrations.exchange_router import place_order as route_place_order


# Mode trading : True pour réel, False pour simulation
REAL_TRADING = os.getenv("REAL_TRADING", "False").lower() == "true"


def _as_float(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _normalize_symbol(sym: str) -> str:
    sym = (sym or "").strip()
    return sym.lower()  # your plans are lower-case (dotusdt, arbusdt)


def _normalize_side(side: str) -> str:
    s = (side or "").strip().lower()
    if s in ("buy", "b"):
        return "buy"
    if s in ("sell", "s"):
        return "sell"
    return s


def _get_qty(order: dict) -> float:
    # execution_engine_pro uses "amount" in your NSC conventions,
    # but we accept multiple synonyms
    return _as_float(
        order.get("quantity") or order.get("amount") or order.get("size") or order.get("qty"),
        0.0
    )


def _nsc_execution_hard_gate(data_dir: str):
    """Retourne (ok_to_execute: bool, reason: str). FAIL-SAFE: if error => block."""
    try:
        dd = Path(data_dir)

        # Effective execution plan (respects SIMULATED_ONLY plan file if your loader uses it)
        plan, plan_path = load_effective_execution_plan(str(dd), default={})
        gov = load_json_file(dd / "analysis" / "governance_engine_pro.json", default={})
        ks = load_json_file(dd / "trading" / "kill_switch.json", default={})

        # 0) PREPROD is ALWAYS blocked for real trading (absolute safety)
        env = str(os.getenv("NSC_ENV", "")).upper()
        if env == "PREPROD":
            return False, "env=PREPROD => real execution disabled"

        # 1) Kill-switch prioritaire
        if isinstance(ks, dict):
            if bool(ks.get("enabled")) is True and (bool(ks.get("hard_block")) or str(ks.get("mode")) == "hard_block"):
                return False, "kill_switch_hard_block"

        # 2) Gouvernance KING (source-of-truth)
        if isinstance(gov, dict):
            if bool(gov.get("hard_block")):
                return False, "governance_hard_block"

            ap = str(gov.get("action_policy") or "").upper()
            if ap in {"SIMULATED_ONLY", "PAPER", "DRY_RUN"}:
                return False, f"governance_action_policy={ap}"

        # 3) Execution plan checks
        if isinstance(plan, dict):
            st = str(plan.get("status") or "").lower()
            if st in {"blocked", "hard_block", "hard_blocked"}:
                return False, f"execution_plan_status={st}"

            mode = str(plan.get("execution_mode") or "").upper()
            if mode in {"SIMULATED_ONLY", "PAPER", "DRY_RUN"}:
                return False, f"execution_mode={mode}"

            orders = plan.get("orders")
            if isinstance(orders, list) and len(orders) == 0:
                return False, "execution_plan_orders=0"

        logger.info("[trading_executor] Hard gate OK. plan_path=%s", str(plan_path))
        return True, "ok"

    except Exception as e:
        reason = f"hard_gate_exception:{type(e).__name__}:{e}"
        logger.exception("[trading_executor] HARD GATE exception (reason=%s)", reason)
        return False, reason


def run(data_dir: str | None = None) -> dict:
    """
    Lit execution_plan et exécute les ordres si (et seulement si) autorisé.
    """
    data_dir = data_dir or get_data_dir()
    dd = Path(data_dir)

    # Hard gate first (fail-safe)
    ok, reason = _nsc_execution_hard_gate(str(dd))
    if not ok:
        logger.warning("[trading_executor] HARD GATE => no execution. reason=%s", reason)
        try:
            send_telegram_message(f"🛑 Trading Executor: aucune exécution (raison: {reason})")
        except Exception:
            pass
        return {"status": "blocked", "reason": reason, "orders_executed": 0, "orders_skipped": 0}

    # Load effective plan
    plan, plan_path = load_effective_execution_plan(str(dd), default={})
    if not isinstance(plan, dict):
        return {"status": "error", "reason": "execution_plan_not_dict", "orders_executed": 0, "orders_skipped": 0}

    orders = plan.get("orders") or []
    if not isinstance(orders, list):
        return {"status": "error", "reason": "execution_plan_orders_not_list", "orders_executed": 0, "orders_skipped": 0}

    gov = plan.get("governance") if isinstance(plan.get("governance"), dict) else {}
    action_policy = str((gov or {}).get("action_policy") or "").upper()

    # Global policy guard (in addition to hard gate)
    if action_policy == "SIMULATED_ONLY":
        logger.warning("[trading_executor] Plan action_policy=SIMULATED_ONLY => skip ALL orders")
        return {"status": "simulated_only", "plan_path": str(plan_path), "orders_executed": 0, "orders_skipped": len(orders)}

    executed = 0
    skipped = 0
    errors = 0

    for o in orders:
        if not isinstance(o, dict):
            skipped += 1
            continue

        symbol = _normalize_symbol(o.get("symbol") or "")
        side = _normalize_side(o.get("side") or "")
        qty = _get_qty(o)

        # Per-order simulated guard
        if str(o.get("action") or "").upper() == "SIMULATED_ONLY":
            logger.warning("[trading_executor] SKIP order SIMULATED_ONLY symbol=%s side=%s", symbol, side)
            skipped += 1
            continue

        if not symbol or side not in {"buy", "sell"} or qty <= 0:
            logger.warning("[trading_executor] SKIP invalid order: symbol=%s side=%s qty=%s raw=%s", symbol, side, qty, o)
            skipped += 1
            continue

        # If REAL_TRADING is False => simulate only (no API call)
        if not REAL_TRADING:
            logger.info("[trading_executor] SIMU order %s %s qty=%s (REAL_TRADING=False)", side, symbol, qty)
            try:
                send_telegram_message(f"📝 [SIMU] {side.upper()} {qty} {symbol}")
            except Exception:
                pass
            skipped += 1
            continue

        # Real execution
        try:
            # exchange_router.place_order(token_symbol, amount, side="buy")
            route_place_order(symbol, float(qty), side=side)
            executed += 1
            logger.info("[trading_executor] EXECUTED %s %s qty=%s", side, symbol, qty)
            try:
                send_telegram_message(f"🚀 [REEL] {side.upper()} {qty} {symbol}")
            except Exception:
                pass
        except Exception as e:
            errors += 1
            logger.exception("[trading_executor] EXEC ERROR symbol=%s side=%s qty=%s err=%s", symbol, side, qty, e)
            try:
                send_telegram_message(f"⚠️ [EXEC ERROR] {side.upper()} {qty} {symbol} ({type(e).__name__})")
            except Exception:
                pass

    return {
        "status": "done",
        "plan_path": str(plan_path),
        "orders_total": len(orders),
        "orders_executed": executed,
        "orders_skipped": skipped,
        "errors": errors,
        "real_trading": bool(REAL_TRADING),
    }


if __name__ == "__main__":
    out = run(get_data_dir())
    logger.info("[trading_executor] summary=%s", out)
