# src/v2/intelligence/knowledge_daily_generator.py
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file, data_path, get_data_dir, load_effective_execution_plan

logger = get_logger("knowledge_daily_generator")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short(v: Any, n: int = 160) -> str:
    s = str(v) if v is not None else ""
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _read(path_parts, default=None):
    return load_json_file(data_path(*path_parts), default=default)


def _pick(d: Dict[str, Any], *keys: str, default=None):
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return default


def main() -> Dict[str, Any]:
    env = os.getenv("NSC_ENV", "PREPROD")
    resolved_data_dir = get_data_dir()
    logger.info("[knowledge_daily_generator] DATA_DIR=%s env=%s", resolved_data_dir, env)

    # sources
    sentiment = _read(("sentiment_overview.json",), default={}) or {}
    meta = _read(("analysis", "meta_score_engine_pro.json"), default={}) or {}
    risk = _read(("analysis", "risk_engine_pro.json"), default={}) or {}
    mc = _read(("analysis", "market_conditions_engine_pro.json"), default={}) or {}
    sq = _read(("analysis", "signal_quality_engine_pro.json"), default={}) or {}

    orches = _read(("telemetry", "orchestrator_pro.json"), default={}) or {}
    gov = _read(("analysis", "governance_engine_pro.json"), default={}) or {}
    exec_plan, exec_plan_path = load_effective_execution_plan(get_data_dir(), default={})
    exec_plan = exec_plan or {}
    sized = _read(("trading", "sized_signals.json"), default={}) or []
    portfolio = _read(("analysis", "portfolio_engine_pro.json"), default={}) or {}
    pnl = _read(("profitability", "monthly_pnl.json"), default={}) or {}
    costs = _read(("costs", "monthly_costs.json"), default={}) or {}

    # KPIs robustes
    can_trade = orches.get("can_trade")
    mode = orches.get("mode") or orches.get("risk_mode") or "unknown"
    reasons = orches.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]

    orders = 0
    if isinstance(exec_plan, dict):
        orders = len(exec_plan.get("orders") or [])

    nb_sized = len(sized) if isinstance(sized, list) else 0

    # Sentiment: supporte plusieurs schémas
    sentiment_bucket = _pick(sentiment, "bucket", "bucket_label", "sentiment_bucket", default=None)
    sentiment_avg = _pick(sentiment, "avg", "average", "average_sentiment", "mean", default=None)
    sentiment_total = _pick(sentiment, "total", "count", "nb_messages", "n_messages", default=None)

    digest = {
        "timestamp": _utc_now(),
        "env": env,
        "headline": {
            "can_trade": bool(can_trade) if can_trade is not None else None,
            "mode": mode,
            "meta_score": float(meta.get("score", 0.0) or 0.0),
            "market_conditions": {
                "flag": mc.get("global_flag") or mc.get("flag"),
                "score": mc.get("score"),
            },
            "signal_quality": {"flag": sq.get("flag"), "score": sq.get("score")},
            "risk_engine": {"flag": risk.get("flag"), "score": risk.get("score")},
            "sentiment": {"bucket": sentiment_bucket, "avg": sentiment_avg, "total": sentiment_total},
        },
        "trading": {
            "signals_sized": nb_sized,
            "orders_planned": orders,
            "execution_plan_path": str(exec_plan_path),
            "sized_signals_path": str(data_path("trading", "sized_signals.json")),
        },
        "portfolio": {
            "status": portfolio.get("status"),
            "symbols": portfolio.get("symbols") or portfolio.get("positions") or [],
        },
        "profitability": {
            "monthly_pnl_path": str(data_path("profitability", "monthly_pnl.json")),
            "monthly_costs_path": str(data_path("costs", "monthly_costs.json")),
            "pnl_summary": _short(pnl, 260),
            "costs_summary": _short(costs, 260),
        },
        "governance": {
            "flag": gov.get("flag"),
            "score": gov.get("score"),
            "orchestrator_reasons": [_short(r, 240) for r in (reasons or [])][:8],
        },
        "links": {
            "meta_score": str(data_path("analysis", "meta_score_engine_pro.json")),
            "market_conditions": str(data_path("analysis", "market_conditions_engine_pro.json")),
            "signal_quality": str(data_path("analysis", "signal_quality_engine_pro.json")),
            "risk_engine": str(data_path("analysis", "risk_engine_pro.json")),
            "governance": str(data_path("analysis", "governance_engine_pro.json")),
            "market_snapshot": str(data_path("analysis", "market_snapshot.json")),
        },
    }

    out_path = data_path("knowledge", "knowledge_daily.json")
    save_json_file(out_path, digest)
    logger.info("[knowledge_daily_generator] saved: %s", out_path)
    return digest


if __name__ == "__main__":
    print(main())
