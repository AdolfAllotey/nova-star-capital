#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NSC - Alert Digest (Telegram)
Regroupe les alertes sur des fenêtres fixes et envoie un résumé.

Fenêtres (Europe/Paris):
- morning : [00:00 → 08:00)
- noon    : [08:00 → 12:30)
- evening : [12:30 → 19:00)

Le fichier d'alertes est attendu en JSONL (une alerte par ligne JSON),
avec au minimum un champ "ts" en ISO8601 (UTC), et idéalement:
  {
    "ts": "2025-09-09T17:30:34Z",
    "kind": "worst_trade",
    "symbol": "BTCUSDT",
    "message": "Perte 12.3% ...",
    "severity": "warn",
    "source": "v2",
    "meta": {...}
  }

Utilisation:
  python3 -m v2.analytics.alert_digest --moment morning [--telegram]
  python3 -m v2.analytics.alert_digest --moment noon --log-file /path/alerts.log
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Iterable, List, Tuple, Optional, Dict, Any

# Py 3.9+ : zoneinfo standard
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

# --------------------------------------------------------------------------------------
# Chemins par défaut (structure v2)
# --------------------------------------------------------------------------------------
BASE_DIR = Path("/root/src/v2")
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_ALERTS_LOG = RUNTIME_DIR / "alerts.log"

PARIS = ZoneInfo("Europe/Paris") if ZoneInfo else None

# --------------------------------------------------------------------------------------
# Modèle simple d'alerte (facultatif, pour lisibilité)
# --------------------------------------------------------------------------------------
@dataclass
class Alert:
    ts: datetime          # UTC
    kind: Optional[str]   # ex: 'worst_trade'
    severity: Optional[str]
    symbol: Optional[str]
    message: Optional[str]
    source: Optional[str]
    meta: Optional[Dict[str, Any]]
    raw: Dict[str, Any]

# --------------------------------------------------------------------------------------
# Utilitaires de temps
# --------------------------------------------------------------------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso8601_utc(s: str) -> Optional[datetime]:
    """Parse ISO8601 'Z' ou avec offset → datetime aware en UTC."""
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # On assume déjà UTC si pas d'info
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def today_window(moment: str) -> Tuple[datetime, datetime, str]:
    """
    Calcule la fenêtre de la journée EN HEURE LOCALE Europe/Paris,
    puis renvoie (start_utc, end_utc, label).
    """
    if PARIS is None:
        raise RuntimeError("zoneinfo indisponible (Europe/Paris). Python 3.9+ requis.")

    now_local = datetime.now(PARIS)
    d = now_local.date()

    if moment == "morning":
        start_local = datetime.combine(d, time(0, 0), tzinfo=PARIS)
        end_local   = datetime.combine(d, time(8, 0), tzinfo=PARIS)
        label = "🧭 Digest matin (08:00)"
    elif moment == "noon":
        start_local = datetime.combine(d, time(8, 0), tzinfo=PARIS)
        end_local   = datetime.combine(d, time(12, 30), tzinfo=PARIS)
        label = "🧭 Digest midi (12:30)"
    elif moment == "evening":
        start_local = datetime.combine(d, time(12, 30), tzinfo=PARIS)
        end_local   = datetime.combine(d, time(19, 0), tzinfo=PARIS)
        label = "🧭 Digest soir (19:00)"
    else:
        raise ValueError("moment doit être parmi: morning|noon|evening")

    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
        label,
    )

# --------------------------------------------------------------------------------------
# Lecture du log d'alertes
# --------------------------------------------------------------------------------------
def load_alerts_between(start_utc: datetime, end_utc: datetime, log_path: Path) -> List[Alert]:
    """
    Lit un fichier JSONL et renvoie les alertes avec ts ∈ [start, end).
    """
    alerts: List[Alert] = []
    if not log_path.exists():
        return alerts

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue

            ts_raw = doc.get("ts") or doc.get("timestamp")
            if not ts_raw:
                continue

            ts = parse_iso8601_utc(str(ts_raw))
            if ts is None:
                continue

            if not (start_utc <= ts < end_utc):
                continue

            alerts.append(
                Alert(
                    ts=ts,
                    kind=doc.get("kind"),
                    severity=doc.get("severity"),
                    symbol=doc.get("symbol"),
                    message=doc.get("message"),
                    source=doc.get("source"),
                    meta=doc.get("meta"),
                    raw=doc,
                )
            )
    # tri par date ascendante
    alerts.sort(key=lambda a: a.ts)
    return alerts

# --------------------------------------------------------------------------------------
# Formatage Telegram
# --------------------------------------------------------------------------------------
SEVERITY_EMOJI = {
    "crit": "🚨",
    "error": "❌",
    "warn": "⚠️",
    "info": "ℹ️",
    None: "•",
}

KIND_EMOJI = {
    "worst_trade": "📉",
    "daily_report": "📑",
    "transfer_plan": "💸",
    "allocator": "🧮",
    "hook": "🪝",
    None: "•",
}

def format_one_alert(a: Alert) -> str:
    sev = SEVERITY_EMOJI.get(a.severity, "•")
    kind = KIND_EMOJI.get(a.kind, "•")
    hhmm = a.ts.strftime("%H:%M")
    sym = f" {a.symbol}" if a.symbol else ""
    msg = a.message or ""
    # Ligne compacte
    return f"{sev}{kind} [{hhmm} UTC]{sym} — {msg}".strip()

def format_digest(label: str, start_utc: datetime, end_utc: datetime, alerts: List[Alert], max_lines: int = 12) -> str:
    header = f"{label}\n🕒 Période: {start_utc.strftime('%H:%M')} UTC → {end_utc.strftime('%H:%M')} UTC"
    count = len(alerts)

    if count == 0:
        return f"{header}\n\n✅ Aucune alerte sur la période."

    body_lines = [format_one_alert(a) for a in alerts]
    clipped = False
    if len(body_lines) > max_lines:
        body_lines = body_lines[-max_lines:]
        clipped = True

    footer = f"\n📦 Total: {count} alerte(s)"
    if clipped:
        footer += " (dernières affichées)"

    return f"{header}\n\n" + "\n".join(body_lines) + footer

# --------------------------------------------------------------------------------------
# Envoi Telegram
# --------------------------------------------------------------------------------------
def telegram_send(text: str) -> Tuple[bool, str]:
    """
    Envoie sur Telegram via TELEGRAM_BOT_TOKEN et TELEGRAM_ALERTS_CHAT_ID
    (ou TELEGRAM_CHAT_ID). Retourne (ok, info_ou_erreur).
    """
    import urllib.parse
    import urllib.request

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_ALERTS_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat:
        return False, "TELEGRAM_BOT_TOKEN ou chat id manquant"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text
        # pas de parse_mode → pas besoin d'échapper
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200:
                return True, "sent"
            return False, f"HTTP {r.status}"
    except Exception as e:
        return False, f"{e}"

# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="NSC Alert Digest (Telegram)")
    p.add_argument("--moment", choices=["morning", "noon", "evening"], required=True, help="Créneau: morning|noon|evening")
    p.add_argument("--telegram", action="store_true", help="Envoyer le digest sur Telegram")
    p.add_argument("--log-file", default=str(DEFAULT_ALERTS_LOG), help=f"Fichier JSONL d'alertes (def: {DEFAULT_ALERTS_LOG})")
    p.add_argument("--max-lines", type=int, default=12, help="Nombre max de lignes détaillées")
    args = p.parse_args()

    start, end, label = today_window(args.moment)
    alerts = load_alerts_between(start, end, Path(args.log_file))
    text = format_digest(label, start, end, alerts, max_lines=args.max_lines)

    # Toujours afficher localement (journalctl/systemd)
    print(text)

    if args.telegram:
        ok, info = telegram_send(text)
        if ok:
            print("[alert_digest] Telegram: sent ✅")
            sys.exit(0)
        else:
            print(f"[alert_digest][WARN] Telegram send failed: {info}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
