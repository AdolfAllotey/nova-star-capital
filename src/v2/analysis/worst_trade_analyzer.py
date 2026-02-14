from __future__ import annotations

from typing import Any, Dict

from src.v2.utils.logger import get_logger

logger = get_logger("worst_trade_analyzer_shim")


def analyze_and_notify(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Compat shim used by run_pipeline.
    Delegates to src.v2.analytics.worst_trade_analyzer.analyze_worst_trades_and_generate_summary.
    """
    try:
        from src.v2.analytics.worst_trade_analyzer import analyze_worst_trades_and_generate_summary
    except Exception as e:
        logger.warning(f"[shim] analytics.worst_trade_analyzer indisponible ({e}) — skip")
        return {"status": "skipped", "reason": f"analytics_import_failed: {e}"}

    try:
        res = analyze_worst_trades_and_generate_summary()
        return {"status": "ok", "result": res}
    except Exception as e:
        logger.exception(f"[shim] échec analyse worst trades: {e}")
        return {"status": "error", "error": str(e)}


# Optional alias if other code imports this name from analysis
analyze_worst_trades_and_generate_summary = analyze_and_notify
