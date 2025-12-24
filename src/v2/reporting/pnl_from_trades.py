from __future__ import annotations
import csv
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
TRADES_CSV = ROOT / "src" / "v2" / "data" / "trading" / "trades.csv"
OUT_CSV    = ROOT / "src" / "v2" / "data" / "reporting" / "monthly_pnl.csv"

def _parse_iso(ts: str) -> datetime:
    # supporte "2025-09-04T18:07:32.45+00:00" ou "2025-09-04 18:07:32"
    ts = ts.strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        # fallback: tronque les microsecondes exotiques
        return datetime.fromisoformat(ts.split(".")[0])

def write_daily_pnl_from_trades(tz_name: str = "Europe/Paris",
                                trades_csv: Path = TRADES_CSV,
                                out_csv: Path = OUT_CSV) -> int:
    tz = ZoneInfo(tz_name)
    by_day = {}
    if not trades_csv.is_file():
        # Crée un CSV vide si pas de trades
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date","pnl_usd"])
        return 0

    with trades_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ts = (row.get("timestamp") or "").strip()
            v  = (row.get("pnl_usd") or row.get("pnl") or "").strip()
            if not ts or not v:
                continue
            try:
                dt = _parse_iso(ts)
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            dt = dt.astimezone(tz)
            dkey = dt.date().isoformat()
            try:
                val = float(v)
            except Exception:
                continue
            by_day[dkey] = by_day.get(dkey, 0.0) + val

    # Écrit un fichier propre (trié par date, sans doublons)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date","pnl_usd"])
        for d in sorted(by_day.keys()):
            w.writerow([d, f"{by_day[d]:.2f}"])
    return len(by_day)
