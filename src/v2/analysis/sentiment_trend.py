import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("sentiment_trend")

# Avoid duplicate log lines if get_logger attached multiple handlers
_NSC_DEDUP_HANDLERS_DONE = False
if not _NSC_DEDUP_HANDLERS_DONE:
    seen = set()
    uniq = []
    for h in list(logger.handlers):
        key = (type(h).__name__, getattr(h, "baseFilename", None))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    logger.handlers = uniq
    _NSC_DEDUP_HANDLERS_DONE = True



logger.propagate = False  # avoid duplicate logs via root handlers
# Idempotency guard (avoid double run in same process)
_SENTIMENT_TREND_ALREADY_RAN = False
_SENTIMENT_TREND_LAST_PAYLOAD = None

DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")

REPORTS_DIR = Path(DATA_DIR) / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Inputs
AVG_SENTIMENT_PRIMARY = Path(DATA_DIR) / "average_sentiment.json"

# Outputs
TS_JSONL = REPORTS_DIR / "sentiment_timeseries.jsonl"
TREND_JSON = REPORTS_DIR / "sentiment_trend.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> datetime | None:
    try:
        # isoformat with timezone
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _read_jsonl(path: Path, max_lines: int = 5000) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        # read last max_lines by scanning all (OK for our sizes)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        if len(rows) > max_lines:
            rows = rows[-max_lines:]
        return rows
    except Exception as e:
        logger.warning(f"failed to read jsonl {path}: {e}")
        return []


def _window_stats(rows: list[dict], now: datetime, window: timedelta) -> dict:
    lo = now - window
    pts = []
    for r in rows:
        ts = _parse_ts(r.get("ts", "")) or _parse_ts(r.get("generated_at", ""))
        if not ts:
            continue
        if ts >= lo and ts <= now:
            v = r.get("overall")
            if isinstance(v, (int, float)):
                pts.append((ts, float(v)))

    pts.sort(key=lambda x: x[0])
    n = len(pts)
    if n == 0:
        return {"avg": 0.0, "delta": 0.0, "n": 0}

    avg = sum(v for _, v in pts) / n
    delta = pts[-1][1] - pts[0][1] if n >= 2 else 0.0
    return {"avg": avg, "delta": delta, "n": n}


def _regime_from(stats_1h: dict) -> tuple[str, float, list[str]]:
    """
    Simple & robuste:
      - bullish si avg_1h > +0.10 et delta_1h > 0
      - bearish si avg_1h < -0.10 et delta_1h < 0
      - sinon neutral
    Confidence: augmente avec n et amplitude (capée)
    """
    avg = float(stats_1h.get("avg", 0.0) or 0.0)
    delta = float(stats_1h.get("delta", 0.0) or 0.0)
    n = int(stats_1h.get("n", 0) or 0)

    reasons = [f"avg_1h={avg:.4f}", f"delta_1h={delta:.4f}", f"n_1h={n}"]

    if avg > 0.10 and delta > 0:
        regime = "bullish"
    elif avg < -0.10 and delta < 0:
        regime = "bearish"
    else:
        regime = "neutral"

    # confidence heuristic
    # base from count (0..1), plus amplitude signal (0..1), capped
    c_count = min(1.0, n / 50.0)  # 50 points ~ "good"
    c_amp = min(1.0, (abs(avg) + abs(delta)) / 0.6)  # 0.6 ~ strong combined signal
    conf = min(1.0, 0.15 + 0.55 * c_count + 0.30 * c_amp)
    return regime, conf, reasons


def append_timeseries(payload: dict) -> None:
    """
    Append one line to JSONL. Keep it minimal.
    """
    record = {
        "ts": _utc_now().isoformat(),
        "overall": float(payload.get("overall", 0.0) or 0.0),
        "by_source": payload.get("by_source", {}) if isinstance(payload.get("by_source"), dict) else {},
        "counts": payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {},
        "status": payload.get("status", "unknown"),
        "method": payload.get("method", {}) if isinstance(payload.get("method"), dict) else {},
    }
    TS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with TS_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_trend() -> dict:
    avg = load_json_file(str(AVG_SENTIMENT_PRIMARY), default=None)
    if not isinstance(avg, dict) or not avg:
        # still write a trend file but indicate empty
        now = _utc_now()
        trend = {
            "ts": now.isoformat(),
            "status": "empty",
            "last": {"overall": 0.0, "by_source": {}, "counts": {"total": 0}},
            "windows": {
                "1h": {"avg": 0.0, "delta": 0.0, "n": 0},
                "6h": {"avg": 0.0, "delta": 0.0, "n": 0},
                "24h": {"avg": 0.0, "delta": 0.0, "n": 0},
            },
            "regime": "neutral",
            "confidence": 0.0,
            "reasons": ["average_sentiment.json missing/invalid"],
        }
        return trend

    # append this run
    append_timeseries(avg)

    now = _utc_now()
    rows = _read_jsonl(TS_JSONL)

    s1h = _window_stats(rows, now, timedelta(hours=1))
    s6h = _window_stats(rows, now, timedelta(hours=6))
    s24h = _window_stats(rows, now, timedelta(hours=24))

    regime, conf, reasons = _regime_from(s1h)

    trend = {
        "ts": now.isoformat(),
        "status": "ok",
        "last": {
            "overall": float(avg.get("overall", 0.0) or 0.0),
            "by_source": avg.get("by_source", {}) if isinstance(avg.get("by_source"), dict) else {},
            "counts": avg.get("counts", {}) if isinstance(avg.get("counts"), dict) else {},
            "generated_at": avg.get("generated_at"),
        },
        "windows": {
            "1h": s1h,
            "6h": s6h,
            "24h": s24h,
        },
        "regime": regime,
        "confidence": conf,
        "reasons": reasons,
    }
    return trend


def run():
    global _SENTIMENT_TREND_ALREADY_RAN, _SENTIMENT_TREND_LAST_PAYLOAD
    if _SENTIMENT_TREND_ALREADY_RAN:
        logger.info("🟡 sentiment_trend already ran in this process — skipping duplicate call")
        return _SENTIMENT_TREND_LAST_PAYLOAD
    _SENTIMENT_TREND_ALREADY_RAN = True

    trend = build_trend()
    _SENTIMENT_TREND_LAST_PAYLOAD = trend
    save_json_file(str(TREND_JSON), trend)
    logger.info(
        f"✅ sentiment_trend written: {TREND_JSON} regime={trend.get('regime')} conf={trend.get('confidence')}"
    )
    return trend


if __name__ == "__main__":
    run()
