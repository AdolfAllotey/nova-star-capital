from __future__ import annotations

"""
Compatibility wrapper.

Historically, the pipeline imported:
  src.v2.analytics.worst_trade_analyzer

The maintained implementation lives in:
  src.v2.analysis.worst_trade_analyzer

This module re-exports the public entrypoints.
"""

from src.v2.analysis.worst_trade_analyzer import (  # noqa: F401
    analyze_worst_trades_and_generate_summary,
)

def main() -> None:
    analyze_worst_trades_and_generate_summary()

if __name__ == "__main__":
    main()
