from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

RUNS_DIR = Path("data/telemetry/preprod_runs")
OUT = RUNS_DIR / "preprod_kpis.json"

def _parse_ts(name: str) -> datetime | None:
    # preprod_daily_YYYYmmdd_HHMMSS.json
    try:
        s = name.replace("preprod_daily_", "").replace(".json", "")
        return datetime.strptime(s, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main() -> dict:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(RUNS_DIR.glob("preprod_daily_*.json"))
    runs = []
    for f in files:
        ts = _parse_ts(f.name)
        if not ts:
            continue
        d = _load(f)
        ok = d.get("ok")
        runs.append({"ts": ts.isoformat(), "ok": bool(ok), "file": str(f)})

    now = datetime.now(timezone.utc)
    def _window(days: int):
        cutoff = now - timedelta(days=days)
        w = [r for r in runs if datetime.fromisoformat(r["ts"]) >= cutoff]
        total = len(w)
        okc = sum(1 for r in w if r["ok"])
        return {"total": total, "ok": okc, "ok_rate": (okc / total) if total else None}

    out = {
        "generated_at": now.isoformat(),
        "runs_total": len(runs),
        "last_run": runs[-1] if runs else None,
        "window_7d": _window(7),
        "window_30d": _window(30),
        "recent_failures": [r for r in runs[-20:] if not r["ok"]],
    }

    OUT.write_text(json.dumps(out, indent=2, sort_keys=False), encoding="utf-8")
    return out

if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
