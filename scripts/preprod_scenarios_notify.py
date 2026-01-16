from __future__ import annotations
import os, json, glob
from pathlib import Path
from datetime import datetime, timezone

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    files = sorted(glob.glob("data/telemetry/preprod_scenarios/preprod_scenarios_*.json"))
    if not files:
        return
    p = Path(files[-1])
    d = _load(p)
    ok = bool(d.get("overall_ok"))
    env = os.getenv("NSC_ENV", "UNKNOWN")
    ts = datetime.now(timezone.utc).isoformat()

    if ok:
        return

    failed = []
    for s in d.get("scenarios") or []:
        if not s.get("scenario_ok", False):
            failed.append(s.get("id"))

    msg = (
        f"🚨 NSC PREPROD SCENARIOS FAILED\n"
        f"- env: {env}\n"
        f"- ts: {ts}\n"
        f"- report: {p}\n"
        f"- failed: {', '.join(failed) if failed else 'unknown'}"
    )

    try:
        from src.v2.utils.telegram_utils import send_telegram_message
        send_telegram_message(msg)
    except Exception:
        pass

    try:
        from src.v2.utils.email_utils import send_email
        to_addr = os.getenv("NSC_ALERT_EMAIL") or os.getenv("REPORT_EMAIL") or ""
        if to_addr:
            send_email(to_addr, "NSC PREPROD SCENARIOS FAILED", msg)
    except Exception:
        pass

if __name__ == "__main__":
    main()
