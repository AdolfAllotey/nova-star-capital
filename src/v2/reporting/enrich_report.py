from __future__ import annotations
import csv, json, math
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Paths
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "src" / "v2" / "data"
REPORTS = DATA / "reports"
ANALYSIS = DATA / "analysis"
TRADING = DATA / "trading"
RISK = DATA / "risk"
SOCIAL = DATA / "social"
REPORTS.mkdir(parents=True, exist_ok=True)

MD_PATH = REPORTS / "daily_report.md"
JSON_PATH = REPORTS / "daily_report.json"
TG_TXT_PATH = REPORTS / "daily_report.telegram.txt"

# Helpers
def _now_paris():
    tz = ZoneInfo("Europe/Paris")
    return datetime.now(tz)

def _fmt_money(v: float) -> str:
    sign = "+" if v >= 0 else "−"
    return f"{sign}{abs(v):,.2f} USD".replace(",", " ")

def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_sentiment():
    j = _load_json(ANALYSIS / "sentiment_summary.json") or {}
    score = _safe_float(j.get("score", 0.0), 0.0)
    gen_at = j.get("generated_at") or j.get("generatedAt") or ""
    return score, gen_at

def load_social(prev_json: Path | None = JSON_PATH):
    # Try fresh data
    tele = _load_json(SOCIAL / "telegram_data.json")
    red  = _load_json(SOCIAL / "reddit_data.json")
    t_cnt = None
    r_cnt = None
    # Best-effort counters
    if isinstance(tele, list):
        t_cnt = len(tele)
    elif isinstance(tele, dict):
        for k in ("messages","items","data","results"):
            if isinstance(tele.get(k), list):
                t_cnt = len(tele[k]); break
        if t_cnt is None:
            # generic count of values that are lists
            t_cnt = sum(isinstance(v, list) for v in tele.values()) or 0
    if isinstance(red, list):
        r_cnt = len(red)
    elif isinstance(red, dict):
        for k in ("posts","items","data","results"):
            if isinstance(red.get(k), list):
                r_cnt = len(red[k]); break
        if r_cnt is None:
            r_cnt = sum(isinstance(v, list) for v in red.values()) or 0

    # Fallback to last JSON report if needed
    if (t_cnt is None or r_cnt is None) and prev_json and prev_json.exists():
        try:
            prev = json.loads(prev_json.read_text(encoding="utf-8"))
            t_cnt = t_cnt if t_cnt is not None else int(prev.get("social",{}).get("telegram",0))
            r_cnt = r_cnt if r_cnt is not None else int(prev.get("social",{}).get("reddit",0))
        except Exception:
            pass

    return int(t_cnt or 0), int(r_cnt or 0)

def load_trades_last48h():
    # Count rows in trades.csv (if it has timestamps, we try 48h filter; else count all)
    path = TRADING / "trades.csv"
    total = 0
    try:
        rows = []
        with path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append(row)
        # Try filter by timestamp
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=48)
        def parse_ts(s: str):
            s = (s or "").strip()
            if not s:
                return None
            for fmt in ("%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S.%f%z","%Y-%m-%d %H:%M:%S%z","%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(s, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    continue
            return None
        any_ts = any(parse_ts(r.get("timestamp") or r.get("time") or "") for r in rows)
        if any_ts:
            total = sum(1 for r_ in rows if (lambda d: d is not None and d >= cutoff)(parse_ts(r_.get("timestamp") or r_.get("time") or "")))
        else:
            total = len(rows)
    except Exception:
        total = 0
    return int(total)

def load_pnl():
    """Return (today, mtd, all_time, trend_prev_day) from monthly_pnl.csv (grouped by date)."""
    path = DATA / "reporting" / "monthly_pnl.csv"
    today = _now_paris().date()
    month_start = today.replace(day=1)
    daily_map = {}
    try:
        with path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                d = (row.get("date") or "").strip()
                v = _safe_float(row.get("pnl_usd"), 0.0)
                if not d:
                    continue
                # keep last occurrence per date (idempotent-friendly)
                daily_map[d] = v
    except Exception:
        pass

    # Aggregate
    pnl_today = daily_map.get(str(today), 0.0)
    pnl_prev  = None
    # try previous day if exists
    prev_date = str(today - timedelta(days=1))
    if prev_date in daily_map:
        pnl_prev = daily_map[prev_date]

    # MTD sum
    mtd = 0.0
    for d, v in daily_map.items():
        try:
            dd = datetime.strptime(d, "%Y-%m-%d").date()
            if month_start <= dd <= today:
                mtd += float(v)
        except Exception:
            continue
    # All-time sum
    all_time = sum(float(v) for v in daily_map.values()) if daily_map else 0.0
    return pnl_today, mtd, all_time, pnl_prev

def load_worst_trades_count():
    j = _load_json(RISK / "worst_trades.json")
    if isinstance(j, list):
        return len(j)
    if isinstance(j, dict):
        for k in ("items","trades","data","results"):
            if isinstance(j.get(k), list):
                return len(j[k])
    return 0

# Renderers
def render_markdown(social_tg:int, social_rd:int, score:float, score_gen:str,
                    trades48:int, worst:int, pnl_today:float, pnl_mtd:float, pnl_all:float):
    now = _now_paris()
    heading_date = now.strftime("%Y-%m-%d")
    clock = now.strftime("%H:%M")
    pnl_today_str = _fmt_money(pnl_today)
    pnl_mtd_str   = _fmt_money(pnl_mtd)
    pnl_all_str   = _fmt_money(pnl_all)

    def badge(val: float) -> str:
        if val > 0: return "🟢"
        if val < 0: return "🔴"
        return "⚪️"

    md = []
    md.append(f"# 🌌 Rapport quotidien — {heading_date}\n")
    md.append(f"📅 **Généré à** : {clock} (CEST)\n")
    md.append("---\n")
    md.append("## 🛰️ Activité Social (48h)")
    md.append(f"- **Telegram** : {_fmt_int(social_tg)} msgs")
    md.append(f"- **Reddit** : {_fmt_int(social_rd)} posts\n")
    md.append("---\n")
    md.append("## 🧠 Sentiment")
    md.append(f"- **Score** : `{score:.4f}`")
    if score_gen:
        md.append(f"- **Calculé** : {score_gen}\n")
    else:
        md.append("")
    md.append("---\n")
    md.append("## 📊 Trades")
    md.append(f"- **Total (48h)** : {_fmt_int(trades48)} opérations")
    md.append(f"- **⚠️ Pires trades** : {_fmt_int(worst)} détectés\n")
    md.append("---\n")
    md.append("## 💹 PnL (USD)")
    md.append(f"- **Aujourd’hui** : `{pnl_today_str}` {badge(pnl_today)}")
    md.append(f"- **Mois (MTD)** : `{pnl_mtd_str}` {badge(pnl_mtd)}")
    md.append(f"- **Cumul** : `{pnl_all_str}` {badge(pnl_all)}\n")
    md.append("---\n")
    md.append("✨ _Nova Star_ 🚀")
    return "\n".join(md).rstrip() + "\n"

def render_telegram_short(social_tg:int, social_rd:int, score:float,
                          trades48:int, worst:int, pnl_today:float, pnl_mtd:float, pnl_all:float):
    now = _now_paris()
    d = now.strftime("%Y-%m-%d")
    clock = now.strftime("%H:%M")
    arrow = "📈" if pnl_today >= 0 else "📉"
    return (
        f"🌌 *Rapport quotidien* — {d}  \n"
        f"🕒 {clock} (CEST)\n"
        f"— — — — — — — —\n"
        f"🛰️ Social 48h  \n"
        f"• Telegram: {_fmt_int(social_tg)}  • Reddit: {_fmt_int(social_rd)}\n"
        f"🧠 Sentiment: `{score:.2f}`\n"
        f"📊 Trades 48h: {_fmt_int(trades48)}  |  ⚠️ Pires: {_fmt_int(worst)}\n"
        f"💹 PnL: {arrow} Aujourd’hui {_fmt_money(pnl_today)}  \n"
        f"MTD {_fmt_money(pnl_mtd)} • Cumul {_fmt_money(pnl_all)}\n"
        f"_Nova Star_ 🚀"
    )

def main():
    # Gather
    score, score_gen = load_sentiment()
    tg_cnt, rd_cnt = load_social()
    trades48 = load_trades_last48h()
    worst = load_worst_trades_count()
    pnl_today, pnl_mtd, pnl_all, pnl_prev = load_pnl()

    # JSON
    payload = {
        "generated_at": _now_paris().isoformat(),
        "social": {"telegram": tg_cnt, "reddit": rd_cnt},
        "sentiment": {"score": score, "generated_at": score_gen},
        "trades": {"last_48h": trades48, "worst_count": worst},
        "pnl_usd": {"today": pnl_today, "mtd": pnl_mtd, "all_time": pnl_all},
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # MD
    md = render_markdown(
        social_tg=tg_cnt, social_rd=rd_cnt, score=score, score_gen=score_gen,
        trades48=trades48, worst=worst,
        pnl_today=pnl_today, pnl_mtd=pnl_mtd, pnl_all=pnl_all
    )
    MD_PATH.write_text(md, encoding="utf-8")

    # Telegram short text
    TG_TXT_PATH.write_text(
        render_telegram_short(
            tg_cnt, rd_cnt, score, trades48, worst, pnl_today, pnl_mtd, pnl_all
        ),
        encoding="utf-8",
    )

    # Print ANSI preview (optional UX)
    import sys
    if "--ansi" in sys.argv:
        print("🌌 Rapport quotidien —", _now_paris().strftime("%Y-%m-%d"))
        print("Généré à :", _now_paris().strftime("%H:%M (CEST)"))
        print("—"*60)
        print("🛰️ Social (48h)")
        print(f"  Telegram : {_fmt_int(tg_cnt)}  |  Reddit : {_fmt_int(rd_cnt)}")
        print("—"*60)
        print("🧠 Sentiment")
        print(f"  Score    : {score:.4f}")
        if score_gen:
            print(f"  Calculé  : {score_gen}")
        print("—"*60)
        print("📊 Trades")
        print(f"  Total (48h)   : {_fmt_int(trades48)}")
        print(f"  ⚠️  Pires     : {_fmt_int(worst)}")
        print("—"*60)
        print("💹 PnL (USD)")
        print(f"  Aujourd’hui   : {_fmt_money(pnl_today)}")
        print(f"  Mois (MTD)    : {_fmt_money(pnl_mtd)}")
        print(f"  Cumul         : {_fmt_money(pnl_all)}")

if __name__ == "__main__":
    main()
    print(json.dumps({"updated": str(JSON_PATH), "markdown": str(MD_PATH), "telegram_text": str(TG_TXT_PATH)}))
