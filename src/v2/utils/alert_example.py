#!/usr/bin/env python3
from v2.utils.alert_manager import AlertManager, Alert

if __name__ == "__main__":
    am = AlertManager(ttl_seconds=6*3600, cooldown_seconds=30*60)
    a = Alert(kind="breakout", symbol="BTCUSDT", message="Breakout 1h > 48k", severity="info", meta={"tf":"1h"})
    if am.should_emit(a):
        print("[alert] EMIT:", a.message)
        # -> envoyer sur Telegram/Email/etc.
        am.record(a)
    else:
        print("[alert] SKIP (duplicate/cooldown):", a.message)
