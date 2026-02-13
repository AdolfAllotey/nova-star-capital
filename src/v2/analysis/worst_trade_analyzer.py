"""
Compat shim (PREPROD): historical module path.

Pipeline still imports `src.v2.analysis.worst_trade_analyzer`.
The implementation lives in `src.v2.analytics.worst_trade_analyzer`.

Do not add logic here. Keep it as a stable re-export layer.
"""
from __future__ import annotations

from src.v2.analytics.worst_trade_analyzer import *  # noqa: F401,F403
