from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime, timezone

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    p = Path("data/telemetry/preprod_check.json")
    d = _load(p)
    ok = bool(d.get("ok"))
    env = os.getenv("NSC_ENV", "UNKNOWN")
    ts = datetime.now(timezone.utc).isoformat()

    if ok:
        return

    reasons = []
    details = d.get("details") or {}
    gov = details.get("governance_reasons") or []
    if isinstance(gov, list):
        reasons.extend(gov[:5])

    msg = (
        f"🚨 NSC PREPROD CHECK FAILED\n"
        f"- env: {env}\n"
        f"- ts: {ts}\n"
        f"- details: {p}\n"
        f"- reasons: " + " | ".join(str(r) for r in reasons)
    )

    # Telegram (best-effort)
    try:
        from src.v2.utils.telegram_utils import send_telegram_message
        send_telegram_message(msg)
    except Exception:
        pass

    # Email (best-effort)
    try:
        from src.v2.utils.email_utils import send_email
        to_addr = os.getenv("NSC_ALERT_EMAIL") or os.getenv("REPORT_EMAIL") or ""
        if to_addr:
            send_email(to_addr, "NSC PREPROD FAILED", msg)
    except Exception:
        pass

if __name__ == "__main__":
    main()
