import os, json, sys
from datetime import datetime, timezone
import subprocess

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def send_telegram(text):
    # utilisé seulement si DIGEST désactivé
    import urllib.parse, urllib.request
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat  = os.getenv("TELEGRAM_DAILY_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[example_hook] Telegram token/chat manquant, skip", file=sys.stderr)
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status == 200

def enqueue_alert(alert: dict):
    p = subprocess.run(
        ["/usr/local/bin/nsc-alert-enqueue.py"],
        input=(json.dumps(alert)).encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    ok = (p.returncode == 0)
    if not ok:
        sys.stderr.write(p.stderr.decode(errors="ignore"))
    return ok

def main():
    digest = os.getenv("HOOK_DIGEST","true").lower() == "true"

    # Exemple : récupérer la dernière alerte “worst_trade” d’un fichier runtime (si présent)
    # Ici, à adapter à ta source d’alertes réelle ; pour la démo on fabrique 1 alerte.
    alert = {
        "ts": utcnow_iso(),
        "kind": "worst_trade",
        "symbol": "BTCUSDT",
        "severity": "warn",
        "message": "Perte 12.3% sur BTCUSDT (≈ -120.50€)",
        "source": "v2",
        "meta": {"pnl_pct": -12.3, "pnl_eur": -120.5}
    }

    if digest:
        ok = enqueue_alert(alert)
        print("[example_hook] queued" if ok else "[example_hook] queue failed", file=sys.stderr if not ok else sys.stdout)
    else:
        # mode direct (non digest)
        ok = send_telegram(f"[ALERTE] {alert['symbol']} — {alert['message']}")
        print("[example_hook] Telegram envoyé" if ok else "[example_hook] Telegram FAILED")

if __name__ == "__main__":
    main()
