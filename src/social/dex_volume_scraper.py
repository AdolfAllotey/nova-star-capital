"""
Dex volume scraper (placeholder import-safe version).
Original file had indentation/syntax issues.
"""

from __future__ import annotations
import os
import logging
import requests

logger = logging.getLogger("dex_volume_scraper")

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/pairs/ethereum"


def fetch_pair() -> dict:
    r = requests.get(DEXSCREENER_URL, timeout=20)
    r.raise_for_status()
    return r.json()


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    try:
        data = fetch_pair()
        logger.info("dex_volume_scraper ok keys=%s", list(data.keys())[:10])
        return 0
    except Exception as e:
        logger.exception("dex_volume_scraper failed: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
