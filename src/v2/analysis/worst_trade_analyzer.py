from __future__ import annotations
import logging

log = logging.getLogger("nsc.analysis.worst_trade")

def analyze_and_notify() -> None:
    """
    Analyse minimaliste : no-op + log (pas d'alerte envoyée).
    """
    log.info("worst_trade_analyzer.analyze_and_notify -> noop (placeholder)")
