from datetime import datetime
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger(__name__)

BASE_PATH = "/opt/nsc/app/data/equities_offensive"

EXECUTION_PLAN_PATH = f"{BASE_PATH}/execution/execution_plan.json"
ENTRY_CANDIDATES_PATH = f"{BASE_PATH}/risk/execution_candidates.json"
EXIT_CANDIDATES_PATH = f"{BASE_PATH}/risk/exit_candidates.json"
OUTPUT_PATH = "/opt/nsc/app/data/explainability/explainability_report.json"


def norm_symbol(value):
    return str(value or "").strip().upper()


def classify_order(order):
    if not order:
        return None

    reason = str(order.get("reason") or "").lower()
    side = str(order.get("side") or "").upper()

    if "take_profit" in reason or "stop" in reason or side == "SELL":
        return "EXIT_EXECUTED"
    return "ENTRY_EXECUTED"


def infer_entry_not_executed_reason(candidate, execution_plan, orders_by_symbol):
    symbol = norm_symbol(candidate.get("symbol"))
    vetos = candidate.get("vetos") or []
    governance_mode = str(execution_plan.get("audit", {}).get("governance_mode") or "").lower()
    plan_reasons = [str(x).lower() for x in execution_plan.get("reasons", [])]
    caps = execution_plan.get("audit", {}).get("caps", {}) or {}
    matching_orders = orders_by_symbol.get(symbol, [])
    has_exit_order = any(str(o.get("side") or "").upper() == "SELL" for o in matching_orders)

    if vetos:
      return "veto_present", "signal carries one or more vetoes"

    if "hard_block" in governance_mode or "blocked" in governance_mode:
      return "blocked_by_governance", "governance mode blocks execution"

    if has_exit_order:
      return "exit_prioritized", "symbol has an exit order prioritized over a new entry"

    if caps.get("max_orders_per_run") == 0 or caps.get("max_notional_eur_per_run") == 0:
      return "blocked_by_caps", "execution caps prevent any new entry"

    if any("policy=" in r for r in plan_reasons):
      return "not_selected_by_plan", "candidate not retained in final execution plan"

    return "not_selected_by_plan", "candidate not retained in final execution plan"


def infer_exit_not_executed_reason(candidate, execution_plan):
    governance_mode = str(execution_plan.get("audit", {}).get("governance_mode") or "").lower()

    if "hard_block" in governance_mode or "blocked" in governance_mode:
        return "blocked_by_governance", "governance mode blocks exit execution"

    return "not_selected_by_plan", "exit candidate not retained in final execution plan"


def build_entry_explanation(candidate, order, context, execution_plan, orders_by_symbol):
    executed = order is not None
    decision = classify_order(order) if executed else "ENTRY_NOT_EXECUTED"

    if executed:
        decision_class = "executed_entry"
        decision_reason = order.get("reason") or "entry executed"
    else:
        decision_class, decision_reason = infer_entry_not_executed_reason(
            candidate, execution_plan, orders_by_symbol
        )

    payload = {
        "symbol": candidate.get("symbol"),
        "decision": decision,
        "decision_class": decision_class,
        "family": "entry",
        "narrative": {
            "context": {
                "regime": context.get("regime"),
                "governance_mode": context.get("governance_mode"),
                "policy": context.get("policy"),
            },
            "signal": {
                "score": candidate.get("meta_score"),
                "setup": candidate.get("setup"),
                "side": candidate.get("direction"),
            },
            "decision": {
                "type": order.get("type") if order else None,
                "qty": order.get("qty") if order else None,
                "side": order.get("side") if order else None,
                "reason": decision_reason,
            },
        },
    }

    if candidate.get("vetos"):
        payload["narrative"]["risk"] = {"vetos": candidate.get("vetos")}

    return payload


def build_exit_explanation(candidate, order, context, execution_plan):
    executed = order is not None
    decision = "EXIT_EXECUTED" if executed else "EXIT_NOT_EXECUTED"

    if executed:
        decision_class = "executed_exit"
        decision_reason = order.get("reason") or "exit executed"
    else:
        decision_class, decision_reason = infer_exit_not_executed_reason(candidate, execution_plan)

    return {
        "symbol": candidate.get("symbol"),
        "decision": decision,
        "decision_class": decision_class,
        "family": "exit",
        "narrative": {
            "context": {
                "regime": context.get("regime"),
                "governance_mode": context.get("governance_mode"),
                "policy": context.get("policy"),
            },
            "signal": {
                "score": candidate.get("score"),
                "setup": candidate.get("reason"),
                "side": "exit",
            },
            "decision": {
                "type": order.get("type") if order else None,
                "qty": order.get("qty") if order else None,
                "side": order.get("side") if order else None,
                "reason": decision_reason,
            },
        },
    }


def summarize_explanations(explanations):
    summary = {
        "entries_executed": 0,
        "entries_not_executed": 0,
        "exits_executed": 0,
        "exits_not_executed": 0,
        "total_symbols": 0,
        "total_events": len(explanations),
        "decision_classes": {},
    }

    symbols = set()

    for item in explanations:
        decision = item.get("decision")
        symbol = norm_symbol(item.get("symbol"))
        decision_class = item.get("decision_class") or "unknown"

        if symbol:
            symbols.add(symbol)

        summary["decision_classes"][decision_class] = summary["decision_classes"].get(decision_class, 0) + 1

        if decision == "ENTRY_EXECUTED":
            summary["entries_executed"] += 1
        elif decision == "ENTRY_NOT_EXECUTED":
            summary["entries_not_executed"] += 1
        elif decision == "EXIT_EXECUTED":
            summary["exits_executed"] += 1
        elif decision == "EXIT_NOT_EXECUTED":
            summary["exits_not_executed"] += 1

    summary["total_symbols"] = len(symbols)
    return summary


def build_by_symbol(explanations):
    grouped = {}

    for item in explanations:
        symbol = norm_symbol(item.get("symbol"))
        if not symbol:
            continue

        grouped.setdefault(symbol, {
            "symbol": symbol,
            "timeline": [],
        })

        grouped[symbol]["timeline"].append(item)

    for symbol in grouped:
        grouped[symbol]["timeline"].sort(
            key=lambda x: (
                0 if x.get("family") == "entry" else 1,
                x.get("decision") or "",
            )
        )

    return grouped


def generate_explainability_report():
    try:
        execution_plan = load_json_file(EXECUTION_PLAN_PATH, default={})
        entry_candidates_data = load_json_file(ENTRY_CANDIDATES_PATH, default={})
        exit_candidates_data = load_json_file(EXIT_CANDIDATES_PATH, default={})

        entry_candidates = entry_candidates_data.get("candidates", [])
        exit_candidates = exit_candidates_data.get("candidates", [])
        orders = execution_plan.get("orders", [])

        orders_by_symbol = {}
        for order in orders:
            sym = norm_symbol(order.get("symbol"))
            if sym:
                orders_by_symbol.setdefault(sym, []).append(order)

        explanations = []

        for candidate in entry_candidates:
            symbol = norm_symbol(candidate.get("symbol"))
            matching_orders = orders_by_symbol.get(symbol, [])
            matching_order = next(
                (o for o in matching_orders if str(o.get("side") or "").upper() == "BUY"),
                None,
            )

            context = {
                "regime": candidate.get("regime"),
                "governance_mode": execution_plan.get("audit", {}).get("governance_mode"),
                "policy": execution_plan.get("action_policy"),
            }

            explanations.append(
                build_entry_explanation(candidate, matching_order, context, execution_plan, orders_by_symbol)
            )

        for candidate in exit_candidates:
            symbol = norm_symbol(candidate.get("symbol"))
            matching_orders = orders_by_symbol.get(symbol, [])
            matching_order = next(
                (o for o in matching_orders if str(o.get("side") or "").upper() == "SELL"),
                None,
            )

            context = {
                "regime": execution_plan.get("audit", {}).get("governance_mode"),
                "governance_mode": execution_plan.get("audit", {}).get("governance_mode"),
                "policy": execution_plan.get("action_policy"),
            }

            explanations.append(
                build_exit_explanation(candidate, matching_order, context, execution_plan)
            )

        output = {
            "generated_at": datetime.utcnow().isoformat(),
            "count": len(explanations),
            "summary": summarize_explanations(explanations),
            "explanations": explanations,
            "by_symbol": build_by_symbol(explanations),
        }

        save_json_file(OUTPUT_PATH, output)
        logger.info(f"Explainability report generated ({len(explanations)} items)")
        return output

    except Exception as e:
        logger.error(f"Explainability generation failed: {e}")
        return {}
