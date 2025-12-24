# src/v2/monitoring/run_scrapers.py
from __future__ import annotations

import os
import time
import inspect
import asyncio
from importlib import import_module
from typing import Any, Callable, Dict, Optional

from src.v2.utils.logger import get_logger

logger = get_logger("run_scrapers")


def _get_env() -> str:
    return os.environ.get("NSC_ENV", "PREPROD")


def _get_data_dir() -> str:
    root = os.environ.get("NSC_ROOT_DIR") or os.getcwd()
    return os.environ.get("NSC_DATA_DIR", os.path.join(root, "data"))


def _is_enabled(flag_env: str, default: str = "1") -> bool:
    return os.getenv(flag_env, default).lower() in ("1", "true", "yes", "on")


def _safe_call(func: Callable[..., Any], *args, **kwargs):
    """
    Appelle une fonction sync ou async de façon unifiée.
    Retourne:
      - coroutine/awaitable si async
      - None si sync (ou si le résultat n'est pas awaitable)
    """
    if inspect.iscoroutinefunction(func):
        return func(*args, **kwargs)

    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return res
    return None


async def _run_module_call(name: str, module_path: str, func_name: str) -> Dict[str, Any]:
    """
    Exécute module.func (sync/async) et retourne un petit status dict.
    """
    t0 = time.perf_counter()
    status = "pending"
    error: Optional[str] = None

    try:
        logger.info("[scrapers] %s -> import %s", name, module_path)
        module = import_module(module_path)

        func = getattr(module, func_name, None)
        if func is None:
            status = "skipped"
            error = f"missing func {func_name}"
            logger.warning("[scrapers] %s SKIPPED (func %s introuvable)", name, func_name)
        else:
            logger.info("[scrapers] %s -> call %s.%s()", name, module_path, func_name)
            awaitable = _safe_call(func)
            if inspect.isawaitable(awaitable):
                await awaitable
            status = "ok"
            logger.info("[scrapers] %s OK", name)

    except Exception as e:
        status = "error"
        error = f"{e.__class__.__name__}: {e}"
        logger.exception("[scrapers] %s ERROR: %s", name, error)

    dt = round(time.perf_counter() - t0, 3)
    return {"name": name, "module": module_path, "func": func_name, "status": status, "duration_s": dt, "error": error}


async def main_async() -> None:
    env = _get_env()
    data_dir = _get_data_dir()
    logger.info("[scrapers] start (env=%s data_dir=%s)", env, data_dir)

    # Flags (tu peux désactiver vite fait une source sans toucher au code)
    telegram_enabled = _is_enabled("TELEGRAM_ENABLED", "1")
    twitter_enabled = _is_enabled("TWITTER_ENABLED", "1")
    reddit_enabled = _is_enabled("REDDIT_ENABLED", "1")
    social_enabled = _is_enabled("SOCIAL_FEED_ENABLED", "1")
    sentiment_enabled = _is_enabled("SENTIMENT_ENABLED", "1")

    # 1) Telegram / Twitter / Reddit
    if telegram_enabled:
        await _run_module_call("telegram", "src.v2.monitoring.telegram_scraper", "scrape_telegram")
    else:
        logger.info("[scrapers] telegram disabled (TELEGRAM_ENABLED=0)")

    if twitter_enabled:
        await _run_module_call("twitter", "src.v2.monitoring.twitter_scraper", "scrape_twitter")
    else:
        logger.info("[scrapers] twitter disabled (TWITTER_ENABLED=0)")

    if reddit_enabled:
        await _run_module_call("reddit", "src.v2.monitoring.reddit_scraper", "scrape_reddit")
    else:
        logger.info("[scrapers] reddit disabled (REDDIT_ENABLED=0)")

    # 2) Social aggregator (build social_feed.json)
    if social_enabled:
        await _run_module_call("social", "src.v2.monitoring.social_aggregator", "build_social_feed")
    else:
        logger.info("[scrapers] social disabled (SOCIAL_FEED_ENABLED=0)")

    # 3) Sentiment (based on social feed)
    # IMPORTANT: ici on choisit d’appeler sentiment *une fois* dans le bloc scrapers.
    # Si tu veux le laisser aussi dans daily_trading_loop, il faudra le retirer d’un côté.
    if sentiment_enabled:
        await _run_module_call("sentiment", "src.v2.analysis.sentiment_analyzer", "analyze_sentiment")
    else:
        logger.info("[scrapers] sentiment disabled (SENTIMENT_ENABLED=0)")

    logger.info("[scrapers] done")


def main() -> None:
    """
    Entrée sync compatible systemd/cron:
    - si on est déjà dans une event-loop (rare côté service), on schedule.
    - sinon, asyncio.run().
    """
    try:
        loop = asyncio.get_running_loop()
        # Si on est dans un event loop déjà actif, on planifie.
        loop.create_task(main_async())
    except RuntimeError:
        asyncio.run(main_async())


if __name__ == "__main__":
    main()
