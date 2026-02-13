"""
Compat shim (PREPROD): historical module path.

Pipeline imports `src.v2.analysis.worst_trade_analyzer`.
Implementation lives in `src.v2.analytics.worst_trade_analyzer`.

Keep this file as a stable re-export layer (no business logic).
"""
from __future__ import annotations

from src.v2.analytics.worst_trade_analyzer import *  # noqa: F401,F403
