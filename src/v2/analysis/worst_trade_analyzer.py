"""
Compat shim: src.v2.analysis.worst_trade_analyzer

Objectif: fournir analyze_and_notify() sans jamais faire planter la pipeline
si OpenAI n'est pas installé/configuré en PREPROD.
"""
from __future__ import annotations

from src.v2.utils.logger import get_logger

logger = get_logger("worst_trade_analyzer_shim")


def analyze_and_notify(*args, **kwargs):
    """
    Essaie d'appeler l'analyseur réel (analytics). Si dépendance openai absente,
    on log + skip (PREPROD safe).
    """
    try:
        from src.v2.analytics import worst_trade_analyzer as impl  # noqa
    except Exception as e:
        logger.warning("[shim] worst_trade_analyzer indisponible (%s) — skip", e)
        return None

    fn = getattr(impl, "analyze_and_notify", None)
    if not callable(fn):
        logger.warning("[shim] analytics.worst_trade_analyzer.analyze_and_notify introuvable — skip")
        return None

    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.exception("[shim] erreur worst_trade_analyzer: %s", e)
        return None
