from __future__ import annotations

import os, json, glob
from pathlib import Path
from datetime import datetime, timezone

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _latest(pattern: str) -> Path | None:
    files = sorted(glob.glob(pattern))
    return Path(files[-1]) if files else None

def main() -> int:
    env = os.getenv("NSC_ENV", "UNKNOWN")
    ts = datetime.now(timezone.utc).isoformat()

    last = _latest("data/telemetry/preprod_scenarios/preprod_scenarios_[0-9]*.json")
    if not last:
        return 0

    d = _load(last)
    if not isinstance(d.get("scenarios"), list):
        return 0

    overall_ok = bool(d.get("overall_ok"))

    # always compute KPIs if available
    kpi_path = Path("data/telemetry/preprod_scenarios/preprod_scenarios_kpis.json")
    kpis = _load(kpi_path) if kpi_path.exists() else {}

    if overall_ok:
        return 0

    failed = []
    for s in d.get("scenarios") or []:
        if s.get("scenario_ok") is not True and s.get("id"):
            failed.append(str(s["id"]))

    w7 = kpis.get("window_7d") or {}
    w30 = kpis.get("window_30d") or {}
    fail_streak = kpis.get("fail_streak")

    msg = (
        "🚨 NSC PREPROD SCENARIOS FAILED\n"
        f"- env: {env}\n"
        f"- ts: {ts}\n"
        f"- report: {last}\n"
        f"- failed_ids: {', '.join(failed) if failed else 'unknown'}\n"
    )

    if w7:
        msg += f"- ok_rate_7d: {w7.get('ok_rate')} (ok={w7.get('ok')}/{w7.get('total')})\n"
    if w30:
        msg += f"- ok_rate_30d: {w30.get('ok_rate')} (ok={w30.get('ok')}/{w30.get('total')})\n"
    if fail_streak is not None:
        msg += f"- fail_streak: {fail_streak}\n"

    # Telegram (si ton notifier existe)
    try:
        from src.v2.notifications.telegram_notifier import send_telegram_alert  # type: ignore
        send_telegram_alert(msg)
    except Exception:
        pass

    # Email (optionnel)
    try:
        from src.v2.notifications.email_notifier import send_email  # type: ignore
        addr = os.getenv("NSC_ALERT_EMAIL") or ""
        if addr:
            send_email(addr, "NSC PREPROD SCENARIOS FAILED", msg)
    except Exception:
        pass

    print(msg)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
