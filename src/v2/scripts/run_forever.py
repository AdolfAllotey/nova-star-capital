"""
Legacy helper (kept import-safe).
If you need a long-running loop later, re-implement cleanly.
"""

from __future__ import annotations
import time
import os
import logging

logger = logging.getLogger("run_forever")


def main() -> int:
    interval_hours = float(os.getenv("RUN_FOREVER_INTERVAL_HOURS", "1"))
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    logger.info("run_forever (noop) interval_hours=%s", interval_hours)
    # No infinite loop by default to avoid accidental runaway in PREPROD.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
