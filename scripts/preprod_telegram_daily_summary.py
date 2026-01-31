import os, json, glob
from datetime import datetime
from pathlib import Path

from src.utils.telegram_bot import send_telegram_message

DATA_DIR = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/app/data"))
RUNS_DIR = DATA_DIR / "telemetry" / "preprod_runs"
KPI_PATH = RUNS_DIR / "preprod_kpis.json"
BASELINE_PATH = DATA_DIR / "telemetry" / "preprod_baseline.json"

def _safe_load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _latest_daily_json():
    files = sorted(glob.glob(str(RUNS_DIR / "preprod_daily_*.json")))
    return Path(files[-1]) if files else None

def _fmt_eur(x):
    try:
        return f"{x:+.1f}€"
    except Exception:
        return "n/a"

def _fmt_pct(x):
    try:
        return f"{x:+.2f}%"
    except Exception:
        return "n/a"

def main():
    daily_path = _latest_daily_json()
    daily = _safe_load(daily_path, default={}) if daily_path else {}
    kpi = _safe_load(KPI_PATH, default={}) or {}
    baseline = _safe_load(BASELINE_PATH, default={}) or {}

    today = daily.get("date") or datetime.now().strftime("%Y-%m-%d")
    run_id = daily.get("run_id") or daily.get("run") or daily.get("ts") or "UNKNOWN"
    mode = daily.get("mode") or "SIMULATED_ONLY"

    pnl_day = float(kpi.get("pnl_day_eur", kpi.get("pnl_day", 0.0)) or 0.0)
    pnl_mtd = float(kpi.get("pnl_mtd_eur", kpi.get("pnl_mtd", 0.0)) or 0.0)

    # Equity current: on essaie plusieurs clés
    equity_current = None
    for key in ("equity_current", "equity", "portfolio_value_eur", "nav_eur"):
        v = kpi.get(key)
        if isinstance(v, (int, float)) and v >= 0:
            equity_current = float(v)
            break
    if equity_current is None:
        # fallback: equity = start + pnl_ytd si dispo
        equity_current = float(baseline.get("equity_start_ytd", 0.0) or 0.0) + float(kpi.get("pnl_ytd_eur", 0.0) or 0.0)

    equity_start = float(baseline.get("equity_start_ytd", 0.0) or 0.0)
    pnl_ytd = equity_current - equity_start
    pnl_ytd_pct = (pnl_ytd / equity_start * 100.0) if equity_start > 0 else 0.0

    trades = int(kpi.get("trades", kpi.get("trades_count", 0)) or 0)
    wins = int(kpi.get("wins", 0) or 0)
    losses = int(kpi.get("losses", 0) or 0)
    win_rate = float(kpi.get("win_rate", 0.0) or 0.0)

    avg_win = kpi.get("avg_win_eur", None)
    avg_loss = kpi.get("avg_loss_eur", None)

    hard_block = str(kpi.get("hard_block", "NO")).upper()
    soft_veto = kpi.get("soft_veto", "SIMULATED_ONLY")
    reasons = kpi.get("reasons", kpi.get("risk_reasons", []))
    if isinstance(reasons, list):
        reasons_str = ",".join([str(x) for x in reasons[:5]]) if reasons else "-"
    else:
        reasons_str = str(reasons) if reasons else "-"

    best = kpi.get("best_trade", {}) or {}
    worst = kpi.get("worst_trade", {}) or {}

    best_line = f"• Best:  {_fmt_eur(best.get('pnl_eur', 0.0))} — {best.get('symbol','TOKEN')} ({best.get('reason','')})".strip()
    worst_line = f"• Worst: {_fmt_eur(worst.get('pnl_eur', 0.0))} — {worst.get('symbol','TOKEN')} ({worst.get('reason','')})".strip()

    telemetry_md = daily.get("telemetry_md") or (daily_path.with_suffix(".md").as_posix() if daily_path else "")
    kpis_json = KPI_PATH.as_posix()

    lines = []
    lines.append(f"🧾 NSC PREPROD — Daily Summary ({today})")
    lines.append(f"Run: {run_id}  | Mode: {mode}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📈 Perf")
    lines.append(f"• PnL day: {_fmt_eur(pnl_day)}  | PnL MTD: {_fmt_eur(pnl_mtd)}")
    lines.append(f"• PnL YTD: {_fmt_eur(pnl_ytd)} ({_fmt_pct(pnl_ytd_pct)})")
    lines.append(f"• Trades: {trades} (wins {wins} / losses {losses})  | Win rate: {win_rate:.0f}%")
    if isinstance(avg_win, (int, float)) and isinstance(avg_loss, (int, float)):
        lines.append(f"• Avg win / loss: {avg_win:+.1f}€ / {avg_loss:+.1f}€")
    lines.append("• Exposure: 0.00€ (PREPROD)")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ Risk / Governance")
    lines.append(f"• hard_block: {hard_block}")
    lines.append(f"• soft_veto: {soft_veto}")
    lines.append(f"• reasons: {reasons_str}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📉 Worst / Best")
    lines.append(worst_line)
    lines.append(best_line)
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📦 Artefacts")
    if telemetry_md:
        lines.append(f"• telemetry: {telemetry_md}")
    lines.append(f"• kpis:      {kpis_json}")

    msg = "\n".join(lines)
    ok = send_telegram_message(msg)

if __name__ == "__main__":
    main()
