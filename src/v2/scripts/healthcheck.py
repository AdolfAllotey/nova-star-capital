#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, re
from datetime import datetime, timezone, timedelta, timezone
from pathlib import Path

BASE = Path("/root/Bot_crypto_ultra")
DATA_TG = BASE / "src/v2/data/social/telegram_data.json"
DATA_REPORT = BASE / "src/v2/data/reports/daily_report.json"
LOG_DIR = BASE / "src/v2/logs"
LOG_SEND = LOG_DIR / f"send_reports_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
STATE_DIR = BASE / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_HEALTH = STATE_DIR / "health_last.json"

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} - {msg}", flush=True)

def notify_telegram(message: str):
    try:
        from src.v2.utils.telegram_utils import send_telegram_message
        send_telegram_message(message)
        return True
    except Exception as e:
        log(f"⚠️ Alerte Telegram non envoyée: {e}")
        return False

def read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        log(f"❌ Lecture JSON échouée ({path}): {e}")
        return None

def count_messages(data):
    if not isinstance(data, list):
        return 0
    total = 0
    for ch in data:
        msgs = ch.get("messages", [])
        if isinstance(msgs, list):
            total += len(msgs)
    return total

def max_message_datetime(data):
    iso_dates = []
    for ch in data or []:
        for m in ch.get("messages", []) or []:
            d = m.get("date")
            if not d: 
                continue
            try:
                dt = datetime.fromisoformat(d.replace("Z","+00:00"))
                iso_dates.append(dt)
            except Exception:
                pass
    return max(iso_dates) if iso_dates else None

def check_telegram_data(now_utc: datetime):
    issues = []
    data = read_json(DATA_TG)
    if not data:
        issues.append("telegram_data.json absent ou illisible.")
        return issues, 0, None

    total = count_messages(data)
    last_dt = max_message_datetime(data)

    prev = read_json(STATE_HEALTH) or {}
    prev_total = int(prev.get("total_msgs", 0))
    prev_time = prev.get("last_check_time")

    if not last_dt or (now_utc - last_dt) > timedelta(hours=36):
        issues.append("Aucun message récent (<36h) dans telegram_data.json.")

    if prev_total > 0 and total <= prev_total and (prev_time):
        try:
            prev_dt = datetime.fromisoformat(prev_time)
            if (now_utc - prev_dt) > timedelta(hours=36):
                issues.append("Le total de messages Telegram n’a pas augmenté depuis >36h.")
        except Exception:
            pass

    return issues, total, last_dt

def check_report(now_utc: datetime):
    issues = []
    if not DATA_REPORT.exists():
        issues.append("Rapport quotidien absent.")
        return issues, None

    try:
        st = DATA_REPORT.stat()
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        if (now_utc - mtime) > timedelta(hours=36):
            issues.append(f"Rapport trop ancien (dernier={mtime.isoformat()}).")
    except Exception as e:
        issues.append(f"Impossible de lire mtime du rapport: {e}")
        mtime = None

    rep = read_json(DATA_REPORT)
    if not rep or not isinstance(rep, dict):
        issues.append("Rapport JSON illisible ou invalide (pas un dict).")
    else:
        for k in ("date","trade_count","worst_trade_count"):
            if k not in rep:
                issues.append(f"Clé manquante dans le rapport: {k}")

    return issues, mtime

def check_send_logs(now_utc: datetime):
    issues = []
    if not LOG_SEND.exists():
        issues.append("Log d’envoi du jour introuvable.")
        return issues
    try:
        txt = LOG_SEND.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        issues.append(f"Lecture log envoi échouée: {e}")
        return issues

    ok_tg = bool(re.search(r"Telegram envoyé\s*=\s*True", txt))
    ok_mail = bool(re.search(r"Email envoyé\s*=\s*True", txt))

    if not ok_tg:
        issues.append("Aucun succès Telegram trouvé dans le log du jour.")
    if os.getenv("EMAIL_ENABLED", os.getenv("EMAIL_ENABLED_V2","0")) in ("1","true","True","yes","YES"):
        if not ok_mail:
            issues.append("Aucun succès Email trouvé dans le log du jour.")
    return issues

def main():
    now_utc = datetime.now(timezone.utc)
    all_issues = []

    tg_issues, total_msgs, last_dt = check_telegram_data(now_utc)
    all_issues.extend(tg_issues)

    rep_issues, rep_mtime = check_report(now_utc)
    all_issues.extend(rep_issues)

    log_issues = check_send_logs(now_utc)
    all_issues.extend(log_issues)

    status = "✅ HEALTHCHECK OK"
    if all_issues:
        status = "❌ HEALTHCHECK PROBLÈMES DÉTECTÉS"
        bullet = "\n - ".join(all_issues)
        msg = (
            f"{status}\n"
            f"📊 total_msgs={total_msgs} | last_msg={last_dt.isoformat() if last_dt else 'n/a'}\n"
            f"🗂 rapport_mtime={rep_mtime.isoformat() if rep_mtime else 'n/a'}\n"
            f"Problèmes:\n - {bullet}"
        )
        print(msg)
        notify_telegram(msg)
        rc = 2
    else:
        msg = (
            f"{status}\n"
            f"📊 total_msgs={total_msgs} | last_msg={last_dt.isoformat() if last_dt else 'n/a'}\n"
            f"🗂 rapport_mtime={rep_mtime.isoformat() if rep_mtime else 'n/a'}\n"
            "Tout est au vert."
        )
        print(msg)
        rc = 0

    try:
        with STATE_HEALTH.open("w", encoding="utf-8") as f:
            json.dump({
                "last_check_time": now_utc.isoformat(),
                "total_msgs": total_msgs,
                "last_msg_dt": (last_dt.isoformat() if last_dt else None),
                "report_mtime": (rep_mtime.isoformat() if rep_mtime else None),
                "ok": (rc == 0),
                "issues": all_issues,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ Impossible d’écrire l’état de healthcheck: {e}")

    return rc

if __name__ == "__main__":
    sys.exit(main())
