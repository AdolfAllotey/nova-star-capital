import os
import json
import glob
from pathlib import Path
from datetime import datetime, date

from src.v2.utils.logger import get_logger
from src.utils.telegram_bot import send_telegram_message
import re

logger = get_logger("telegram_daily_summary")


def _data_dir() -> Path:
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/app/data"))


def _latest_daily_md(data_dir: Path) -> Path | None:
    pattern = str(data_dir / "telemetry" / "preprod_runs" / "preprod_daily_*.md")
    files = sorted(glob.glob(pattern))
    return Path(files[-1]) if files else None


def _load_json(p: Path, default):
    try:
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed loading json: %s", p)
        return default


def _fmt_eur(x) -> str:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    sign = "+" if v >= 0 else ""
    # 2 decimals, French style acceptable in Telegram; keep dot to avoid parsing issues
    return f"{sign}{v:.2f}€"


def _to_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _pick(kpis: dict, *keys, default=None):
    for k in keys:
        if isinstance(kpis, dict) and k in kpis and kpis[k] is not None:
            return kpis[k]
    return default


def _calc_ytd_from_kpis(kpis: dict) -> float | None:
    """
    Best-effort:
    - prefer direct ytd key if present
    - else sum daily pnl list if present
    - else fallback to (mtd if today in Jan) or None
    """
    # direct keys
    ytd = _pick(kpis, "pnl_ytd", "ytd_pnl", "pnlYTD", "pnl_ytd_eur")
    if ytd is not None:
        return _to_float(ytd, 0.0)

    # series
    daily_series = _pick(kpis, "daily_pnl_series", "pnl_daily_series", "pnl_days", "daily_pnls")
    if isinstance(daily_series, list):
        return sum(_to_float(x, 0.0) for x in daily_series)

    # dict by date
    daily_map = _pick(kpis, "daily_pnl", "pnl_daily", "pnl_by_day")
    if isinstance(daily_map, dict):
        return sum(_to_float(v, 0.0) for v in daily_map.values())

    return None



def _calc_ytd_from_daily_json_files(data_dir):
    """
    Compute YTD by summing daily PnL from preprod_daily_*.json files (current year).
    Best-effort: tries several candidate keys inside each daily json.
    """
    try:
        from datetime import datetime
        year = datetime.now().year
        pattern = str(Path(data_dir) / "telemetry" / "preprod_runs" / "preprod_daily_*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            return None

        total = 0.0
        found_any = False

        for fp in files:
            name = Path(fp).stem
            m = re.search(r"preprod_daily_(\d{8})_", name)
            if not m:
                continue
            ymd = m.group(1)
            if int(ymd[:4]) != year:
                continue

            try:
                d = json.loads(Path(fp).read_text(encoding="utf-8"))
            except Exception:
                continue

            for k in ("pnl_day","daily_pnl","pnl","pnl_eur","pnl_day_eur","pnl_net_eur"):
                if isinstance(d, dict) and (k in d) and (d[k] is not None):
                    try:
                        total += float(d[k])
                        found_any = True
                        break
                    except Exception:
                        pass

        return total if found_any else None
    except Exception:
        try:
            logger.exception("Failed computing YTD from daily json files")
        except Exception:
            pass
        return None


def build_message(md_path: Path, kpis: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    # run id: keep as-is from filename for traceability
    run_id = md_path.stem.replace("preprod_daily_", "")

    # governance/risk hints (best effort)
    hard_block = _pick(kpis, "hard_block", "governance_hard_block", default=None)
    soft_veto = _pick(kpis, "soft_veto", "action_policy", "governance_action_policy", default=None)
    reasons = _pick(kpis, "reasons", "reason", "governance_reasons", default=None)

    pnl_day = _pick(kpis, "pnl_day", "daily_pnl", "pnl_day_eur", default=0.0)
    pnl_mtd = _pick(kpis, "pnl_mtd", "mtd_pnl", "pnl_mtd_eur", default=0.0)

    ytd_val = _calc_ytd_from_kpis(kpis)
    if ytd_val is None:
        ytd_val = _calc_ytd_from_daily_json_files(_data_dir())
    pnl_ytd = _fmt_eur(ytd_val) if ytd_val is not None else "N/A"

    trades = _pick(kpis, "trades", "trades_count", default=None)
    wins = _pick(kpis, "wins", "win_count", default=None)
    losses = _pick(kpis, "losses", "loss_count", default=None)
    win_rate = _pick(kpis, "win_rate", "winrate", default=None)

    exposure = _pick(kpis, "exposure_eur", "exposure", default=0.0)

    worst_pnl = _pick(kpis, "worst_pnl", "worst_trade_pnl", default=None)
    worst_token = _pick(kpis, "worst_token", "worst_trade_token", default="TOKEN")
    worst_reason = _pick(kpis, "worst_reason", "worst_trade_reason", default="")

    best_pnl = _pick(kpis, "best_pnl", "best_trade_pnl", default=None)
    best_token = _pick(kpis, "best_token", "best_trade_token", default="TOKEN")
    best_reason = _pick(kpis, "best_reason", "best_trade_reason", default="")

    # Normalisation affichage
    hard_block_txt = "YES" if str(hard_block).lower() in ("1", "true", "yes") else "NO"
    soft_veto_txt = str(soft_veto) if soft_veto is not None else "N/A"
    reasons_txt = ""
    if isinstance(reasons, list) and reasons:
        reasons_txt = ",".join(str(x) for x in reasons)
    elif isinstance(reasons, str) and reasons.strip():
        reasons_txt = reasons.strip()
    else:
        reasons_txt = "N/A"

    trades_txt = "N/A"
    if trades is not None:
        trades_txt = str(trades)
        if wins is not None and losses is not None:
            trades_txt += f" (wins {wins} / losses {losses})"
        if win_rate is not None:
            try:
                wr = float(win_rate)
                # accept 0-1 or 0-100
                wr_pct = wr * 100.0 if wr <= 1.0 else wr
                trades_txt += f"  | Win rate: {wr_pct:.0f}%"
            except Exception:
                pass

    worst_line = "• Worst: N/A"
    if worst_pnl is not None:
        worst_line = f"• Worst: {_fmt_eur(worst_pnl)} ({worst_token})"
        if worst_reason:
            worst_line += f"  reason={worst_reason}"

    best_line = "• Best:  N/A"
    if best_pnl is not None:
        best_line = f"• Best:  {_fmt_eur(best_pnl)} ({best_token})"
        if best_reason:
            best_line += f"  reason={best_reason}"

    telemetry_rel = md_path.as_posix()
    kpis_path = _data_dir() / "telemetry" / "preprod_runs" / "preprod_kpis.json"
    kpis_rel = kpis_path.as_posix()

    msg = (
        f"🧾 NSC PREPROD — Daily Summary ({today})\n"
        f"Run: {run_id}  | Mode: SIMULATED_ONLY\n\n"
        f"📈 Perf\n"
        f"• PnL day: {_fmt_eur(pnl_day)}  | PnL MTD: {_fmt_eur(pnl_mtd)}  | PnL YTD: {pnl_ytd}\n"
        f"• Trades: {trades_txt}\n"
        f"• Exposure: {_fmt_eur(exposure)} (PREPROD)\n\n"
        f"🛡️ Risk / Governance\n"
        f"• hard_block: {hard_block_txt}\n"
        f"• soft_veto: {soft_veto_txt}\n"
        f"• reasons: {reasons_txt}\n\n"
        f"📉 Worst / Best\n"
        f"{worst_line}\n"
        f"{best_line}\n\n"
        f"📦 Artefacts\n"
        f"• telemetry: {telemetry_rel}\n"
        f"• kpis:      {kpis_rel}"
    )
    return msg


def main() -> int:
    # FAILSAFE_NO_WRITE_IF_NOT_PREPROD
    nsc_env = os.getenv("NSC_ENV", "UNKNOWN").upper()
    if nsc_env != "PREPROD":
        try:
            logger.warning("NSC_ENV=%s => FAILSAFE skip md write (PREPROD only)", nsc_env)
        except Exception:
            pass
        return 0
    enabled = str(os.getenv("DAILY_SUMMARY_ENABLED", "0")).strip().lower() in ("1", "true", "yes")
    if not enabled:
        logger.info("DAILY_SUMMARY_ENABLED=0 => skip")
        return 0

    data_dir = _data_dir()
    md_path = _latest_daily_md(data_dir)
    if not md_path or not md_path.exists():
        logger.warning("No preprod_daily_*.md found => skip")
        return 0

    kpis_path = data_dir / "telemetry" / "preprod_runs" / "preprod_kpis.json"
    kpis = _load_json(kpis_path, default={})

    msg = build_message(md_path, kpis)
    __telegram_msg = msg
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = Path('/opt/nsc/app/data/telemetry/preprod_runs') / f'telegram_daily_summary_{ts}.md'
    out.write_text(__telegram_msg, encoding='utf-8')
    logger.info('telegram message saved: %s', out)
    ok = send_telegram_message(__telegram_msg)

    logger.info("telegram daily summary sent=%s md=%s", ok, md_path)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
