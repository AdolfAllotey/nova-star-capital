# MODULE_GUARD_PREPROD_HARDTOP
import os as _os
_nsc_env = _os.getenv("NSC_ENV", "UNKNOWN").upper()
if _nsc_env != "PREPROD":
    # IMPORTANT: exit immediately, before any side effects (save/log/send)
    raise SystemExit(0)

import os
import json
import glob
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from src.utils.telegram_bot import send_telegram_message

logger = logging.getLogger("telegram_weekly_summary")


def _setup_logging() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def _data_dir() -> Path:
    # prefer NSC_DATA_DIR / NSC_DATA_ROOT / DATA_ROOT, fallback to /opt/nsc/app/data
    for k in ("NSC_DATA_DIR", "NSC_DATA_ROOT", "DATA_ROOT"):
        v = os.getenv(k)
        if v:
            return Path(v)
    return Path("/opt/nsc/app/data")


def _extract_float(obj: Any, candidates: list[str]) -> float | None:
    """
    Best-effort: search for first numeric value for any key name in candidates,
    in nested dicts/lists.
    """
    def walk(x: Any) -> float | None:
        if isinstance(x, dict):
            for ck in candidates:
                if ck in x:
                    val = x.get(ck)
                    try:
                        if isinstance(val, (int, float)):
                            return float(val)
                        if isinstance(val, str) and val.strip():
                            return float(val.replace(",", "."))
                    except Exception:
                        pass
            for v in x.values():
                got = walk(v)
                if got is not None:
                    return got
        elif isinstance(x, list):
            for it in x:
                got = walk(it)
                if got is not None:
                    return got
        return None

    return walk(obj)


def _extract_int(obj: Any, candidates: list[str]) -> int | None:
    v = _extract_float(obj, candidates)
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _fmt_eur(x: float | None) -> str:
    if x is None:
        return "n/a"
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.2f}€"


def _week_files(preprod_runs_dir: Path, days: int = 7) -> list[Path]:
    # filenames: preprod_daily_YYYYMMDD_HHMMSS.json
    pattern = str(preprod_runs_dir / "preprod_daily_*.json")
    files = [Path(p) for p in glob.glob(pattern)]
    if not files:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[Path] = []
    for fp in files:
        m = re.search(r"preprod_daily_(\d{8})_", fp.stem)
        if not m:
            continue
        ymd = m.group(1)
        try:
            dt = datetime.strptime(ymd, "%Y%m%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt >= cutoff:
            out.append(fp)

    # sort by filename => chronological enough
    return sorted(out)


def _load_json(fp: Path) -> dict:
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_latest_mode(data_dir: Path) -> str:
    # best-effort: read governance soft_veto from governance_engine_pro.json
    candidates = [
        data_dir / "governance" / "governance_engine_pro.json",
        data_dir / "governance_engine_pro.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                d = json.loads(c.read_text(encoding="utf-8"))
                # common shapes
                for key in ("soft_veto", "action_policy", "mode"):
                    if isinstance(d, dict) and d.get(key):
                        return str(d.get(key))
                # nested
                if isinstance(d, dict):
                    for k in ("governance", "state", "effective"):
                        if isinstance(d.get(k), dict):
                            for key in ("soft_veto", "action_policy", "mode"):
                                if d[k].get(key):
                                    return str(d[k].get(key))
            except Exception:
                pass
    # fallback
    return "SIMULATED_ONLY" if os.getenv("NSC_ENV", "").upper() == "PREPROD" else "UNKNOWN"


def _persist_message(preprod_runs_dir: Path, msg: str) -> Path:
    # FAILSAFE_NO_WRITE_IF_NOT_PREPROD
    nsc_env = os.getenv("NSC_ENV", "UNKNOWN").upper()
    if nsc_env != "PREPROD":
        try:
            logger.warning("NSC_ENV=%s => FAILSAFE skip md write (PREPROD only)", nsc_env)
        except Exception:
            pass
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = preprod_runs_dir / f"telegram_weekly_summary_{ts}.md"
    out.write_text(msg, encoding="utf-8")
    return out


def main() -> int:
    _setup_logging()

    if os.getenv("WEEKLY_SUMMARY_ENABLED", "1") != "1":
        logger.info("weekly summary disabled (WEEKLY_SUMMARY_ENABLED!=1)")
        return 0

    data_dir = _data_dir()
    preprod_runs_dir = data_dir / "telemetry" / "preprod_runs"
    preprod_runs_dir.mkdir(parents=True, exist_ok=True)

    files = _week_files(preprod_runs_dir, days=7)
    if not files:
        logger.warning("no daily json files found for weekly summary in %s", preprod_runs_dir)
        return 0

    # Aggregate from daily files
    pnl_week = 0.0
    trades_week = 0
    wins_week = 0
    losses_week = 0
    best_pnl = None
    best_token = None
    worst_pnl = None
    worst_token = None

    for fp in files:
        d = _load_json(fp)

        pnl_day = _extract_float(d, ["pnl_day", "pnl_eur_day", "pnl", "pnl_total_day"])
        if pnl_day is not None:
            pnl_week += pnl_day

        t = _extract_int(d, ["trades", "trades_count", "total_trades", "n_trades"])
        if t is not None:
            trades_week += t

        w = _extract_int(d, ["wins", "win_count", "n_wins"])
        l = _extract_int(d, ["losses", "loss_count", "n_losses"])
        if w is not None:
            wins_week += w
        if l is not None:
            losses_week += l

        # best/worst: try common keys
        bp = _extract_float(d, ["best_pnl", "best_trade_pnl", "best", "max_pnl"])
        bt = None
        if isinstance(d, dict):
            # token might be near best fields
            for kk in ("best_token", "best_symbol", "best_trade_token"):
                if kk in d:
                    bt = d.get(kk)
        wp = _extract_float(d, ["worst_pnl", "worst_trade_pnl", "worst", "min_pnl"])
        wt = None
        if isinstance(d, dict):
            for kk in ("worst_token", "worst_symbol", "worst_trade_token"):
                if kk in d:
                    wt = d.get(kk)

        if bp is not None and (best_pnl is None or bp > best_pnl):
            best_pnl = bp
            best_token = str(bt) if bt else None

        if wp is not None and (worst_pnl is None or wp < worst_pnl):
            worst_pnl = wp
            worst_token = str(wt) if wt else None

    # MTD/YTD from latest preprod_kpis.json if exists (best-effort)
    kpis_fp = preprod_runs_dir / "preprod_kpis.json"
    pnl_mtd = None
    pnl_ytd = None
    if kpis_fp.exists():
        k = _load_json(kpis_fp)
        pnl_mtd = _extract_float(k, ["pnl_mtd", "mtd_pnl", "pnl_month_to_date"])
        pnl_ytd = _extract_float(k, ["pnl_ytd", "ytd_pnl", "pnl_year_to_date"])

    env = os.getenv("NSC_ENV", "UNKNOWN")
    mode = _read_latest_mode(data_dir)

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    win_rate = None
    if trades_week > 0 and wins_week > 0:
        win_rate = (wins_week / trades_week) * 100.0

    msg = (
        f"📅 NSC PREPROD — Weekly Summary ({start_date} → {end_date})\n"
        f"Mode: {mode}\n\n"
        f"📈 Perf\n"
        f"• PnL week: {_fmt_eur(pnl_week)}"
        + (f"  | PnL MTD: {_fmt_eur(pnl_mtd)}" if pnl_mtd is not None else "")
        + (f"  | PnL YTD: {_fmt_eur(pnl_ytd)}" if pnl_ytd is not None else "")
        + "\n"
        f"• Trades: {trades_week} (wins {wins_week} / losses {losses_week})"
        + (f"  | Win rate: {win_rate:.0f}%" if win_rate is not None else "")
        + "\n\n"
        f"📉 Worst / Best\n"
        f"• Worst: {_fmt_eur(worst_pnl)}" + (f" ({worst_token})" if worst_token else "") + "\n"
        f"• Best:  {_fmt_eur(best_pnl)}" + (f" ({best_token})" if best_token else "") + "\n\n"
        f"📦 Artefacts\n"
        f"• kpis:      {kpis_fp}\n"
        f"• last_run:  {files[-1]}\n"
    )

    out = _persist_message(preprod_runs_dir, msg)
    logger.info("telegram weekly message saved: %s", out)


    # ENV_GUARD_PREPROD
    nsc_env = os.getenv("NSC_ENV", "UNKNOWN").upper()
    if nsc_env != "PREPROD":
        logger.warning("NSC_ENV=%s => skip weekly telegram send (PREPROD only)", nsc_env)
        return 0
    ok = send_telegram_message(msg)
    logger.info("telegram weekly summary sent=%s", ok)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
