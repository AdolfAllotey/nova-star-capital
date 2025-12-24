from pathlib import Path
import datetime, sys

# On réutilise ta fonction d'envoi Telegram si dispo ; sinon no-op
try:
    from src.v2.utils.telegram_utils import send_telegram_message
except Exception:
    def send_telegram_message(msg: str) -> None:
        print("[telegram skipped]", msg)

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "src" / "v2" / "data" / "reports" / "daily_report.json"

def main():
    now = datetime.datetime.now(datetime.timezone.utc)

    if not REPORT.exists():
        send_telegram_message("⚠️ Rapport quotidien absent : daily_report.json manquant")
        sys.exit(1)

    mtime = datetime.datetime.fromtimestamp(REPORT.stat().st_mtime, datetime.timezone.utc)
    age_hours = (now - mtime).total_seconds() / 3600

    if age_hours > 24:
        send_telegram_message(f"⚠️ Rapport quotidien trop ancien (dernier: {mtime.isoformat()})")
        sys.exit(1)

    send_telegram_message("✅ Healthcheck OK : rapport quotidien récent")
    # code 0 = OK
if __name__ == "__main__":
    main()
