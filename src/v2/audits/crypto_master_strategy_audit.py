from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "crypto_master_strategy_audit.json"


PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "crypto_portfolio_input": ROOT / "src/v2/data/portfolio/inputs/crypto_portfolio_input.json",
    "capital_allocation": PREPROD / "trading/capital_allocation.json",
    "execution_plan": PREPROD / "trading/execution_plan.json",
    "execution_plan_simulated": PREPROD / "trading/execution_plan_simulated.json",
    "sized_signals": PREPROD / "trading/sized_signals.json",
    "open_positions": PREPROD / "trading/open_positions.json",
    "selected_tokens": PREPROD / "selected_tokens.json",
    "dynamic_tokens": PREPROD / "trading/selected_tokens.dynamic.json",
    "token_exchange_map": PREPROD / "config/token_exchange_map.json",
    "exchange_filters": PREPROD / "config/exchange_filters.json",
    "market_regime": PREPROD / "analysis/market_regime_detector.json",
    "governance": PREPROD / "analysis/governance_engine_pro.json",
    "kill_switch": PREPROD / "trading/kill_switch.json",
    "worst_trades": PREPROD / "risk/worst_trades.json",
    "lt_portfolio": DATA / "portfolio/lt_portfolio.json",
    "profit_distribution_policy": ROOT / "src/v2/config/profit_distribution_policy.json",
    "capital_flow_policy": DATA / "portfolio/capital_flow_policy.json",
}


CRYPTO_LT_ALLOWLIST = {"BTC", "ETH", "SOL"}
MAJOR_OR_LT = {"BTC", "ETH", "SOL", "BNB", "XRP", "AVAX", "MATIC"}
EXPECTED_STRATEGIES = {"momentum", "sniper", "whale"}
EXPECTED_EXCHANGES = {"binance", "mexc"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def as_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for key in ("items", "tokens", "signals", "orders", "positions", "trades", "data"):
            if isinstance(x.get(key), list):
                return x.get(key)
    return []


def norm_symbol(x: Any) -> str:
    s = str(x or "").upper().strip()
    s = s.replace("-", "").replace("/", "").replace("_", "")
    for suffix in ("USDT", "USD", "EUR"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


def get_symbol(row: Dict[str, Any]) -> str:
    return norm_symbol(
        row.get("symbol")
        or row.get("token")
        or row.get("asset")
        or row.get("base")
        or row.get("coin")
    )


def get_strategy(row: Dict[str, Any]) -> str:
    return str(row.get("strategy") or row.get("source_strategy") or row.get("signal_type") or "unknown").lower()


def get_exchange(row: Dict[str, Any]) -> str:
    return str(row.get("exchange") or row.get("venue") or row.get("broker") or "unknown").lower()


def check(name: str, ok: bool, severity: str, detail: str, evidence: Any = None) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def status_from_checks(checks: List[Dict[str, Any]]) -> str:
    if any((not c["ok"]) and c["severity"] == "critical" for c in checks):
        return "critical"
    if any((not c["ok"]) and c["severity"] == "warning" for c in checks):
        return "warning"
    return "ok"


def contains_real_live_marker(payload: Any) -> bool:
    raw = json.dumps(payload).lower()
    for fp in ["missing_live_price", "live_price", "live price"]:
        raw = raw.replace(fp, "")
    dangerous = [
        '"execution_mode": "live"',
        '"action_policy": "live"',
        '"mode": "live"',
        '"real_money_enabled": true',
        '"real_broker_funding_enabled": true',
        '"live_trading": true',
    ]
    return any(d in raw for d in dangerous)


def main() -> None:
    docs = {k: read_json(p, {}) for k, p in PATHS.items()}

    capital_context = docs["capital_context"]
    portfolio_input = docs["crypto_portfolio_input"]
    execution_plan = docs["execution_plan"]
    execution_plan_simulated = docs["execution_plan_simulated"]
    sized_signals = as_list(docs["sized_signals"])
    open_positions = as_list(docs["open_positions"])
    selected_tokens = as_list(docs["selected_tokens"])
    dynamic_tokens = as_list(docs["dynamic_tokens"])
    lt_portfolio = docs["lt_portfolio"]
    profit_policy = docs["profit_distribution_policy"]
    capital_flow_policy = docs["capital_flow_policy"]
    governance = docs["governance"]
    kill_switch = docs["kill_switch"]
    market_regime = docs["market_regime"]
    token_exchange_map = docs["token_exchange_map"]

    orders = as_list(execution_plan.get("orders", [])) if isinstance(execution_plan, dict) else []
    simulated_orders = as_list(execution_plan_simulated.get("orders", [])) if isinstance(execution_plan_simulated, dict) else []

    all_trade_rows = [x for x in orders + sized_signals + open_positions if isinstance(x, dict)]
    symbols = [get_symbol(x) for x in all_trade_rows if get_symbol(x)]
    order_symbols = [get_symbol(x) for x in orders if isinstance(x, dict) and get_symbol(x)]
    position_symbols = [get_symbol(x) for x in open_positions if isinstance(x, dict) and get_symbol(x)]

    strategies = [get_strategy(x) for x in all_trade_rows if get_strategy(x)]
    order_strategies = [get_strategy(x) for x in orders if isinstance(x, dict)]

    exchanges = [get_exchange(x) for x in orders + open_positions if isinstance(x, dict)]
    exchanges = [e for e in exchanges if e and e != "unknown"]

    altcoin_symbols = [s for s in symbols if s and s not in CRYPTO_LT_ALLOWLIST]
    lt_symbols = []
    if isinstance(lt_portfolio, dict):
        positions = lt_portfolio.get("positions", {})
        if isinstance(positions, dict):
            lt_symbols = [norm_symbol(k) for k in positions.keys()]
        elif isinstance(positions, list):
            lt_symbols = [get_symbol(x) for x in positions if isinstance(x, dict)]

    token_map_keys = []
    if isinstance(token_exchange_map, dict):
        token_map_keys = [norm_symbol(k) for k in token_exchange_map.keys()]

    actions = [str(o.get("action") or o.get("side") or "").lower() for o in orders if isinstance(o, dict)]
    quote_usdt_like = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        raw = json.dumps(o).upper()
        if "USDT" in raw:
            quote_usdt_like.append(True)
        else:
            quote_usdt_like.append(False)

    checks = [
        check(
            "mission_alpha_aggressive",
            portfolio_input.get("portfolio_role") == "alpha_aggressive",
            "critical",
            "Crypto must be an aggressive alpha engine, not passive LT.",
            portfolio_input.get("portfolio_role")
        ),
        check(
            "portfolio_funding_pool_crypto",
            portfolio_input.get("funding_pool") == "crypto_exchange_pool",
            "critical",
            "Crypto trading must stay in crypto_exchange_pool.",
            portfolio_input.get("funding_pool")
        ),
        check(
            "preprod_virtual_no_real_money",
            capital_context.get("environment") == "PREPROD"
            and capital_context.get("capital_mode") == "virtual"
            and capital_context.get("real_money_enabled") is False,
            "critical",
            "Crypto audit must confirm PREPROD virtual capital only.",
            capital_context
        ),
        check(
            "no_live_execution",
            not contains_real_live_marker([execution_plan, execution_plan_simulated, governance, kill_switch]),
            "critical",
            "No real/live execution marker should be present.",
            {
                "execution_mode": execution_plan.get("execution_mode") if isinstance(execution_plan, dict) else None,
                "action_policy": execution_plan.get("action_policy") if isinstance(execution_plan, dict) else None,
            }
        ),
        check(
            "orders_are_simulated",
            all(str(o.get("execution_mode", "")).upper() in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", ""} for o in orders if isinstance(o, dict)),
            "critical",
            "Orders must remain simulated.",
            Counter([str(o.get("execution_mode", "missing")) for o in orders if isinstance(o, dict)])
        ),
        check(
            "altcoin_focus_present",
            len(altcoin_symbols) >= 1,
            "warning",
            "Crypto trading should detect/trade altcoins, not only BTC/ETH/SOL.",
            Counter(altcoin_symbols)
        ),
        check(
            "not_only_lt_assets",
            len(set(symbols) - CRYPTO_LT_ALLOWLIST) > 0,
            "warning",
            "Crypto trading universe must not be limited to crypto LT assets.",
            sorted(set(symbols))
        ),
        check(
            "dynamic_tokens_present",
            len(dynamic_tokens) > 0 or len(selected_tokens) > 0,
            "warning",
            "Crypto should have selected/dynamic token sources.",
            {"selected_tokens": len(selected_tokens), "dynamic_tokens": len(dynamic_tokens)}
        ),
        check(
            "expected_strategies_configured",
            EXPECTED_STRATEGIES.issubset(set((portfolio_input.get("allocation") or {}).keys())),
            "warning",
            "Portfolio input should allocate across momentum/sniper/whale.",
            portfolio_input.get("allocation")
        ),
        check(
            "strategy_activity_present",
            len(set(order_strategies) & EXPECTED_STRATEGIES) >= 1,
            "warning",
            "At least one core crypto strategy should produce active orders/signals.",
            Counter(order_strategies)
        ),
        check(
            "exchange_routing_present",
            len(set(exchanges) & EXPECTED_EXCHANGES) >= 1,
            "warning",
            "Orders/positions should expose Binance or MEXC routing.",
            Counter(exchanges)
        ),
        check(
            "token_exchange_map_present",
            isinstance(token_exchange_map, dict) and len(token_exchange_map) > 0,
            "warning",
            "Token exchange map should exist for Binance/MEXC routing.",
            {"tokens_in_map": len(token_map_keys)}
        ),
        check(
            "market_regime_consumed",
            isinstance(market_regime, dict) and bool(market_regime),
            "critical",
            "Crypto must consume market regime.",
            market_regime.get("regime") or market_regime.get("market_regime") if isinstance(market_regime, dict) else None
        ),
        check(
            "governance_consumed",
            isinstance(governance, dict) and bool(governance),
            "critical",
            "Crypto must consume governance.",
            governance.get("flag") or governance.get("status") if isinstance(governance, dict) else None
        ),
        check(
            "kill_switch_available",
            isinstance(kill_switch, dict) and bool(kill_switch),
            "warning",
            "Crypto kill-switch artifact should exist.",
            kill_switch
        ),
        check(
            "crypto_lt_allowlist_restricted",
            set(lt_symbols).issubset(CRYPTO_LT_ALLOWLIST) if lt_symbols else True,
            "warning",
            "Crypto LT should remain restricted to BTC/ETH/SOL unless Master changes.",
            lt_symbols
        ),
        check(
            "profit_policy_exists",
            isinstance(profit_policy, dict) and bool(profit_policy),
            "warning",
            "Profit distribution policy should exist for tax/LT/BFR/security.",
            profit_policy
        ),
        check(
            "tax_from_first_euro",
            (profit_policy.get("tax") or {}).get("apply_from_first_euro") is True
            and float((profit_policy.get("tax") or {}).get("rate", 0)) >= 0.25,
            "critical",
            "Taxes should be reserved from first euro, with 25% baseline accepted.",
            profit_policy.get("tax") if isinstance(profit_policy, dict) else None
        ),
        check(
            "distribution_split_has_lt_bfr_security",
            {"lt", "bfr", "security"}.issubset(set((profit_policy.get("distribution_split") or {}).keys())),
            "warning",
            "Distribution split should include LT, BFR and security.",
            profit_policy.get("distribution_split") if isinstance(profit_policy, dict) else None
        ),
        check(
            "capital_flow_policy_has_phases",
            isinstance(capital_flow_policy.get("phases"), list) and len(capital_flow_policy.get("phases", [])) >= 3,
            "warning",
            "Capital flow should have growth phases.",
            capital_flow_policy.get("phases") if isinstance(capital_flow_policy, dict) else None
        ),
        check(
            "usdt_exit_trace_present",
            any(quote_usdt_like) or any("usdt" in str(s).lower() for s in order_symbols),
            "warning",
            "Crypto exits/orders should preserve USDT quote trace where possible.",
            {"orders_with_usdt_trace": sum(quote_usdt_like), "orders": len(orders)}
        ),
    ]

    report = {
        "status": status_from_checks(checks),
        "engine": "crypto_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "master_intent": {
            "mission": "Generate aggressive alpha through altcoin trading, then compound gains into restricted crypto LT assets.",
            "trading_bucket": "crypto_trading",
            "lt_bucket": "crypto_lt",
            "expected_exchanges": sorted(EXPECTED_EXCHANGES),
            "expected_core_strategies": sorted(EXPECTED_STRATEGIES),
            "crypto_lt_allowlist": sorted(CRYPTO_LT_ALLOWLIST),
            "preprod_mode": "virtual / simulated only",
        },
        "summary": {
            "orders": len(orders),
            "simulated_orders": len(simulated_orders),
            "sized_signals": len(sized_signals),
            "open_positions": len(open_positions),
            "selected_tokens": len(selected_tokens),
            "dynamic_tokens": len(dynamic_tokens),
            "symbols": dict(Counter(symbols)),
            "altcoin_symbols": dict(Counter(altcoin_symbols)),
            "order_strategies": dict(Counter(order_strategies)),
            "all_strategies": dict(Counter(strategies)),
            "exchanges": dict(Counter(exchanges)),
            "lt_symbols": lt_symbols,
            "portfolio_target_weight": portfolio_input.get("target_weight"),
            "portfolio_allocation": portfolio_input.get("allocation"),
            "market_regime": market_regime.get("regime") or market_regime.get("market_regime") if isinstance(market_regime, dict) else None,
            "governance_flag": governance.get("flag") or governance.get("status") if isinstance(governance, dict) else None,
        },
        "checks": checks,
        "failed_checks": [c for c in checks if not c["ok"]],
        "files": {k: str(v) for k, v in PATHS.items()},
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "failed_checks": report["failed_checks"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
