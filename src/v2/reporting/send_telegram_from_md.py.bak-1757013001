from __future__ import annotations
import os, sys, json
from pathlib import Path
import urllib.request
import urllib.parse

# Chemins
ROOT = Path(__file__).resolve().parents[3]  # /root/Bot_crypto_ultra
MD_PATH = ROOT / "src" / "v2" / "data" / "reports" / "daily_report.md"
ENV_PATH = ROOT / "src" / "v2" / ".env"

def load_env_from_file(path: Path) -> dict:
    env = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def send_telegram(token: str, chat_id: str, text: str) -> dict:
    # Envoie en texte brut (pas de parse_mode) → évite les soucis d’échappement
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
        "disable_notification": "false",
    }
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main() -> int:
    # 1) Charger token/chat depuis env ou .env
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        envfile = load_env_from_file(ENV_PATH)
        token = token or envfile.get("TELEGRAM_BOT_TOKEN")
        chat_id = chat_id or envfile.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(json.dumps({"ok": False, "error": "missing token/chat_id"}))
        return 2

    # 2) Lire le markdown
    if not MD_PATH.is_file():
        print(json.dumps({"ok": False, "error": f"markdown not found: {MD_PATH}"}))
        return 3

    text = MD_PATH.read_text(encoding="utf-8").strip()
    # Telegram limite ~4096 caractères → on tronque au besoin
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    try:
        resp = send_telegram(token, chat_id, text)
        ok = bool(resp.get("ok"))
        print(json.dumps({"ok": ok, "response": resp}))
        return 0 if ok else 4
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 5

if __name__ == "__main__":
    raise SystemExit(main())
