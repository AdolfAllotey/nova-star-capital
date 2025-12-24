#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSC · Weekly Report v2
- Lit data/metrics/equity_daily.csv
- Construit un sparkline 7 jours (weekly_sparkline.png)
- Produit un résumé JSON (weekly_report.json)
- Envoie un message Telegram optionnel (--telegram)

Env attendus (comme le daily) :
  TELEGRAM_BOT_TOKEN
  TELEGRAM_WEEKLY_CHAT_ID  (sinon TELEGRAM_DAILY_CHAT_ID, sinon TELEGRAM_CHAT_ID)

Exemples:
  python -m v2.reporting.generate_weekly_report
  python -m v2.reporting.generate_weekly_report --telegram
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Forcer backend headless si non défini (sécurise l’exécution hors TTY)
os.environ.setdefault("MPLBACKEND", "Agg")

# Matplotlib import tardif (après MPLBACKEND)
import matplotlib.pyplot as plt  # noqa: E402

# --- Constantes chemins
ROOT = Path(__file__).resolve().parents[2]  # .../v2
DATA_DIR = ROOT / "data"
METRICS_DIR = DATA_DIR / "metrics"
REPORTS_DIR = DATA_DIR / "reports"

EQUITY_CSV = METRICS_DIR / "equity_daily.csv"
SPARKLINE_PNG = REPORTS_DIR / "weekly_sparkline.png"
REPORT_JSON = REPORTS_DIR / "weekly_report.json"

# --- Helpers formatage
def fmt_money(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        return f"{x:,.2f}€".replace(",", " ").replace(".00€", "€")
    except Exception:
        return str(x)

def fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        return f"{x:.2f}%"
    except Exception:
        return str(x)

def log(msg: str):
    print(f"[weekly_report][INFO] {msg}")

def warn(msg: str):
    print(f"[weekly_report][WARN] {msg}")

# --- Structures
@dataclass
class EquityPoint:
    date: datetime
    equity_eur: float
    profit_eur: Optional[float] = None

# --- Lecture CSV equity
def read_equity_csv(p: Path) -> List[EquityPoint]:
    rows: List[EquityPoint] = []
    if not p.exists():
        warn(f"CSV absent: {p}")
        return rows
    with p.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for line in r:
            try:
                d = datetime.strptime(line["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                eq = float(line["equity_eur"])
                pr = float(line["profit_eur"]) if line.get("profit_eur") not in (None, "",) else None
                rows.append(EquityPoint(d, eq, pr))
            except Exception as e:
                warn(f"ligne invalide: {line} ({e})")
    rows.sort(key=lambda x: x.date)
    log(f"{len(rows)} lignes chargées depuis {p}")
    return rows

# --- Filtres temporels
def last_7_days(points: List[EquityPoint]) -> List[EquityPoint]:
    if not points:
        return []
    end = points[-1].date
    start = end - timedelta(days=6)  # fenêtre inclusive de 7 jours
    return [p for p in points if start.date() <= p.date.date() <= end.date()]

# --- Agrégations
def compute_weekly_stats(points: List[EquityPoint]) -> Dict[str, Any]:
    if not points:
        return {
            "start_date": None,
            "end_date": None,
            "start_equity": None,
            "end_equity": None,
            "pnl_eur": None,
            "pnl_pct": None,
            "count": 0,
        }
    start, end = points[0], points[-1]
    pnl_eur = end.equity_eur - start.equity_eur
    pnl_pct = (pnl_eur / start.equity_eur * 100.0) if start.equity_eur else None
    return {
        "start_date": start.date.date().isoformat(),
        "end_date": end.date.date().isoformat(),
        "start_equity": start.equity_eur,
        "end_equity": end.equity_eur,
        "pnl_eur": pnl_eur,
        "pnl_pct": pnl_pct,
        "count": len(points),
    }

# --- Sparkline
def save_sparkline(points: List[EquityPoint], out_png: Path) -> bool:
    if not points:
        warn("aucun point pour sparkline")
        return False
    out_png.parent.mkdir(parents=True, exist_ok=True)

    xs = [p.date for p in points]
    ys = [p.equity_eur for p in points]

    # Plot simple et propre (pas de couleurs forcées)
    fig = plt.figure(figsize=(6, 2.2), dpi=160)
    ax = fig.add_subplot(111)
    ax.plot(xs, ys, marker="o", linewidth=1.8)
    ax.grid(True, axis="y", alpha=0.25)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="x", rotation=0, labelsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title("Équity (7 derniers jours)", fontsize=10, pad=8)
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)

    log(f"sparkline écrit: {out_png}")
    return True

# --- Alerts (optionnel) : lecture best-effort d’un log si présent
def count_alerts_last_7_days(log_path: Path = ROOT / "logs" / "alerts.log") -> int:
    if not log_path.exists():
        return 0
    start_dt = datetime.now(timezone.utc) - timedelta(days=7)
    count = 0
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # heuristique: cherche un timestamp ISO au début de ligne
                # ex: 2025-09-08 10:15:22,123 ...
                try:
                    prefix = line[:23].replace(",", ".")
                    dt = datetime.strptime(prefix, "%Y-%m-%d %H:%M:%S.%f")
                    dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= start_dt:
                        count += 1
                except Exception:
                    # ignore lignes non conformes
                    pass
    except Exception:
        return 0
    return count

# --- Telegram (sendMessage ou sendPhoto)
def _env_chat_id() -> Optional[str]:
    return (
        os.getenv("TELEGRAM_WEEKLY_CHAT_ID")
        or os.getenv("TELEGRAM_DAILY_CHAT_ID")
        or os.getenv("TELEGRAM_CHAT_ID")
    )

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    import urllib.request
    import urllib.parse

    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        warn(f"Telegram sendMessage failed: {e}")
        return False

def send_telegram_photo(token: str, chat_id: str, caption: str, photo_path: Path) -> bool:
    import mimetypes, uuid, urllib.request

    if not photo_path.exists():
        return False
    boundary = f"----NSCFormBoundary{uuid.uuid4().hex}"
    fields = {
        "chat_id": chat_id,
        "caption": caption,
        "parse_mode": "HTML",
    }

    body = []
    # champs texte
    for name, value in fields.items():
        body.append(f"--{boundary}")
        body.append(f'Content-Disposition: form-data; name="{name}"')
        body.append("")
        body.append(value)
    # fichier
    mime = mimetypes.guess_type(str(photo_path))[0] or "application/octet-stream"
    body.append(f"--{boundary}")
    body.append(
        f'Content-Disposition: form-data; name="photo"; filename="{photo_path.name}"'
    )
    body.append(f"Content-Type: {mime}")
    body.append("")
    with photo_path.open("rb") as f:
        file_bytes = f.read()
    # Joindre binaire + fin
    body_bytes = ("\r\n".join(body) + "\r\n").encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    req = urllib.request.Request(url, data=body_bytes)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body_bytes)))
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:
        warn(f"Telegram sendPhoto failed: {e}")
        return False

# --- Rendu texte
def build_caption(summary: Dict[str, Any], alerts_7d: int) -> str:
    # Emoji & mise en forme proche du daily
    sd = summary
    lines = []
    lines.append("📊 <b>Weekly Report</b>")
    if sd.get("start_date") and sd.get("end_date"):
        lines.append(f"🗓️ {sd['start_date']} → {sd['end_date']}")
    lines.append("")
    lines.append(f"💼 Équity début: <b>{fmt_money(sd.get('start_equity'))}</b>")
    lines.append(f"🏁 Équity fin: <b>{fmt_money(sd.get('end_equity'))}</b>")
    lines.append(f"📈 P&L: <b>{fmt_money(sd.get('pnl_eur'))}</b> ({fmt_pct(sd.get('pnl_pct'))})")
    lines.append(f"🚨 Alertes (7j): <b>{alerts_7d}</b>")
    return "\n".join(lines)

# --- Main
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true", help="Envoi Telegram")
    parser.add_argument("--no-chart", action="store_true", help="Ne pas générer le sparkline")
    parser.add_argument("--no-json", action="store_true", help="Ne pas écrire le JSON")
    args = parser.parse_args(argv)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Charger le CSV equity + réduire à 7j
    points_all = read_equity_csv(EQUITY_CSV)
    points_7 = last_7_days(points_all)

    # 2) Stats
    stats = compute_weekly_stats(points_7)
    alerts_7d = count_alerts_last_7_days()

    # 3) Chart
    chart_ok = False
    if not args.no_chart:
        try:
            chart_ok = save_sparkline(points_7, SPARKLINE_PNG)
        except Exception as e:
            warn(f"Chart error: {e}")

    # 4) JSON
    if not args.no_json:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload = {
            "utc_generated_at": now,
            "summary": stats,
            "alerts_last_7d": alerts_7d,
            "chart": str(SPARKLINE_PNG if chart_ok else ""),
        }
        with REPORT_JSON.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        log(f"weekly_report.json generated at: {REPORT_JSON}")

    # 5) Telegram
    if args.telegram:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = _env_chat_id()
        if not token or not chat_id:
            warn("Telegram non configuré (TELEGRAM_BOT_TOKEN/CHAT_ID)")
        else:
            caption = build_caption(stats, alerts_7d)
            sent = False
            if chart_ok:
                sent = send_telegram_photo(token, chat_id, caption, SPARKLINE_PNG)
            if not sent:
                sent = send_telegram_message(token, chat_id, caption)
            if sent:
                log("Telegram: sent ✅")
            else:
                warn("Telegram: send failed")

    # 6) Résumé console
    pnl_eur = stats.get("pnl_eur")
    pnl_pct = stats.get("pnl_pct")
    print(
        f"[weekly_report] {stats.get('start_date','?')}→{stats.get('end_date','?')} · "
        f"P&L: {fmt_money(pnl_eur)} ({fmt_pct(pnl_pct)}) · "
        f"Alertes(7j): {alerts_7d}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
