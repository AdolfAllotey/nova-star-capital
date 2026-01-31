import os
from src.v2.utils.logger import get_logger

# On réutilise ton sender existant
from src.utils.telegram_bot import send_telegram_message

logger = get_logger("alerting")

def _is_true(v: str | None) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def alerts_enabled() -> bool:
    return _is_true(os.getenv("ALERTS_ENABLED", "1"))

def critical_only() -> bool:
    return _is_true(os.getenv("ALERTS_CRITICAL_ONLY", "1"))

def daily_enabled() -> bool:
    return _is_true(os.getenv("DAILY_SUMMARY_ENABLED", "1"))

def signals_enabled() -> bool:
    return _is_true(os.getenv("SIGNALS_ALERTS_ENABLED", "0"))

def send_alert(message: str, level: str = "info", parse_mode: str | None = None) -> bool:
    """
    level:
      - critical : toujours autorisé si ALERTS_ENABLED=1
      - daily    : autorisé si DAILY_SUMMARY_ENABLED=1
      - info     : autorisé seulement si ALERTS_CRITICAL_ONLY=0
      - signal   : autorisé si SIGNALS_ALERTS_ENABLED=1
    """
    if not alerts_enabled():
        logger.info("[alerting] alerts disabled (ALERTS_ENABLED=0)")
        return False

    level = (level or "info").strip().lower()

    if level == "daily":
        if not daily_enabled():
            logger.info("[alerting] daily disabled")
            return False
    elif level == "signal":
        if not signals_enabled():
            logger.info("[alerting] signals disabled")
            return False
    elif level != "critical":
        # info/warn/etc.
        if critical_only():
            logger.info("[alerting] critical-only ON => skip level=%s", level)
            return False

    prefix = {
        "critical": "🚨",
        "daily": "🧾",
        "signal": "📣",
        "info": "ℹ️",
    }.get(level, "ℹ️")

    env = os.getenv("NSC_ENV", "UNKNOWN")
    final = f"{prefix} NSC {env}: {message}"

    ok = send_telegram_message(final, parse_mode=parse_mode)
    return bool(ok)
