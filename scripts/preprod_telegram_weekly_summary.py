import os, json, glob
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.telegram_bot import send_telegram_message

DATA_DIR = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/app/data"))
RUNS_DIR = DATA_DIR / "telemetry" / "preprod_runs"

def _safe_load(p: Path, default=None):
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _fmt_eur(x):
    try:
        return f"{x:+.1f}€"
    except Exception:
        return "n/a"

def main():
    now = datetime.now()
    start = now - timedelta(days=7)

    # On prend tous les daily json
    files = sorted(glob.glob(str(RUNS_DIR / "preprod_daily_*.json")))
    runs = []
    for f in files:
        p = Path(f)
        d = _safe_load(p, default={}) or {}
        # date in filename: preprod_daily_YYYYMMDD_HHMMSS.json
        try:
            stem = p.stem
            ymd = stem.split("_")[2]  # YYYYMMDD
            dt = datetime.strptime(ymd, "%Y%m%d")
        except Exception:
            dt = now
        if dt >= start:
            runs.append((dt, d, p))

    if not runs:
        send_telegram_message("🧾 NSC PREPROD — Weekly Summary\n(no daily runs found for last 7 days)")
        return

    # KPI per run is usually stored at a fixed path; but daily json can include snapshots.
    # We aggregate from each daily json if present; fallback to 0.
    total_pnl = 0.0
    total_trades = 0
    total_wins = 0
    total_losses = 0

    best = None
    worst = None

    for dt, d, p in runs:
        k = d.get("kpis", {}) if isinstance(d, dict) else {}
        pnl = float(k.get("pnl_day_eur", k.get("pnl_day", 0.0)) or 0.0)
        total_pnl += pnl
        total_trades += int(k.get("trades", k.get("trades_count", 0)) or 0)
        total_wins += int(k.get("wins", 0) or 0)
        total_losses += int(k.get("losses", 0) or 0)

        bt = k.get("best_trade") or None
        wt = k.get("worst_trade") or None

        def upd_best(curr, cand):
            if not isinstance(cand, dict): return curr
            v = cand.get("pnl_eur")
            if not isinstance(v, (int, float)): return curr
            if curr is None or v > curr.get("pnl_eur", -1e18):
                return cand
            return curr

        def upd_worst(curr, cand):
            if not isinstance(cand, dict): return curr
            v = cand.get("pnl_eur")
            if not isinstance(v, (int, float)): return curr
            if curr is None or v < curr.get("pnl_eur", 1e18):
                return cand
            return curr

        best = upd_best(best, bt)
        worst = upd_worst(worst, wt)

    win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
    start_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    end_str = now.strftime("%Y-%m-%d")

    lines = []
    lines.append(f"🧾 NSC PREPROD — Weekly Summary ({start_str} → {end_str})")
    lines.append("Mode: SIMULATED_ONLY")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📈 Perf (7d)")
    lines.append(f"• PnL week: {_fmt_eur(total_pnl)}")
    lines.append(f"• Trades: {total_trades} (wins {total_wins} / losses {total_losses}) | Win rate: {win_rate:.0f}%")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📉 Best / Worst (7d)")
    if isinstance(best, dict):
        lines.append(f"• Best:  {_fmt_eur(best.get('pnl_eur', 0.0))} — {best.get('symbol','TOKEN')} ({best.get('reason','')})".strip())
    else:
        lines.append("• Best:  n/a")
    if isinstance(worst, dict):
        lines.append(f"• Worst: {_fmt_eur(worst.get('pnl_eur', 0.0))} — {worst.get('symbol','TOKEN')} ({worst.get('reason','')})".strip())
    else:
        lines.append("• Worst: n/a")

    msg = "\n".join(lines)
    ok = send_telegram_message(msg)

if __name__ == "__main__":
    main()
