from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from datetime import datetime, timezone

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main() -> int:
    files = sorted(glob.glob("data/telemetry/preprod_scenarios/preprod_scenarios_*.json"))
    if not files:
        return 0

    p = Path(files[-1])
    d = _load(p)

    overall_ok = bool(d.get("overall_ok", False))
    if overall_ok:
        return 0

    failed = []
    for s in d.get("scenarios") or []:
        if not bool(s.get("scenario_ok", False)):
            sid = s.get("id") or "unknown"
            failed.append(str(sid))

    env = os.getenv("NSC_ENV", "UNKNOWN")
    ts = datetime.now(timezone.utc).isoformat()

    msg = (
        "🚨 NSC PREPROD SCENARIOS FAILED\n"
        f"- env: {env}\n"
        f"- ts: {ts}\n"
        f"- report: {p}\n"
        f"- failed: {', '.join(failed) if failed else 'unknown'}\n"
    )

    # Telegram (optionnel)
    try:
        from src.v2.integrations.telegram_notifier import send_telegram_message
        send_telegram_message(msg)
    except Exception:
        pass

    # Email (optionnel)
    try:
        to_addr = os.getenv("NSC_ALERT_EMAIL") or os.getenv("ALERT_EMAIL") or ""
        if to_addr:
            from src.v2.integrations.email_sender import send_email
            send_email(to_addr, "NSC PREPROD SCENARIOS FAILED", msg)
    except Exception:
        pass

    # Log stdout
    print(msg.strip())
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
