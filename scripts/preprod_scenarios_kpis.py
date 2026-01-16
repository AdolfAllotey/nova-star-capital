from __future__ import annotations

import json, glob
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCEN_DIR = Path("data/telemetry/preprod_scenarios")
OUT_JSON = SCEN_DIR / "preprod_scenarios_kpis.json"
OUT_MD   = SCEN_DIR / "preprod_scenarios_kpis.md"


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        # supports "2026-01-16T20:34:27Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _load_json(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _window_stats(items: list[dict[str, Any]], since: datetime) -> dict[str, Any]:
    w = [x for x in items if x["ts"] and x["ts"] >= since]
    total = len(w)
    ok = sum(1 for x in w if x.get("overall_ok") is True)
    ok_rate = (ok / total) if total else 0.0

    # top failed scenario ids in window
    fail_ids: dict[str, int] = {}
    for x in w:
        if x.get("overall_ok") is True:
            continue
        for sid in x.get("failed_ids") or []:
            fail_ids[sid] = fail_ids.get(sid, 0) + 1

    top_failed = sorted(fail_ids.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    return {
        "total": total,
        "ok": ok,
        "ok_rate": round(ok_rate, 4),
        "top_failed_ids": [{"id": k, "count": v} for k, v in top_failed],
    }


def main() -> int:
    files = sorted(glob.glob(str(SCEN_DIR / "preprod_scenarios_*.json")))
    runs: list[dict[str, Any]] = []

    for fp in files:
        p = Path(fp)
        d = _load_json(p)
        ts = _parse_ts(str(d.get("generated_at") or ""))
        overall_ok = bool(d.get("overall_ok")) if "overall_ok" in d else False

        failed_ids: list[str] = []
        for s in d.get("scenarios") or []:
            try:
                if s.get("scenario_ok") is not True:
                    sid = s.get("id")
                    if sid:
                        failed_ids.append(str(sid))
            except Exception:
                pass

        runs.append({
            "file": str(p),
            "ts": ts,
            "overall_ok": overall_ok,
            "failed_ids": failed_ids,
        })

    runs = [r for r in runs if r["ts"] is not None]
    runs.sort(key=lambda r: r["ts"])

    now = datetime.now(timezone.utc)
    w7  = now - timedelta(days=7)
    w30 = now - timedelta(days=30)

    last_run = runs[-1] if runs else None

    # last failure
    last_failure = None
    for r in reversed(runs):
        if r.get("overall_ok") is not True:
            last_failure = r
            break

    # fail streak (consecutive failures from most recent backwards)
    fail_streak = 0
    for r in reversed(runs):
        if r.get("overall_ok") is True:
            break
        fail_streak += 1

    payload: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "window_7d": _window_stats(runs, w7),
        "window_30d": _window_stats(runs, w30),
        "last_run": None,
        "last_failure": None,
        "fail_streak": fail_streak,
        "files_total": len(runs),
    }

    if last_run:
        payload["last_run"] = {
            "ts": last_run["ts"].isoformat(),
            "ok": bool(last_run["overall_ok"]),
            "file": last_run["file"],
            "failed_ids": last_run.get("failed_ids") or [],
        }
    if last_failure:
        payload["last_failure"] = {
            "ts": last_failure["ts"].isoformat(),
            "ok": bool(last_failure["overall_ok"]),
            "file": last_failure["file"],
            "failed_ids": last_failure.get("failed_ids") or [],
        }

    SCEN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # small MD summary
    lines = []
    lines.append("# NSC PREPROD SCENARIOS KPIs\n")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    if payload["last_run"]:
        lines.append(f"- last_run: `{payload['last_run']['ts']}` ok=`{payload['last_run']['ok']}`")
    if payload["last_failure"]:
        lines.append(f"- last_failure: `{payload['last_failure']['ts']}` failed_ids=`{', '.join(payload['last_failure']['failed_ids'])}`")
    lines.append(f"- fail_streak: `{payload['fail_streak']}`\n")

    for k in ("window_7d", "window_30d"):
        w = payload[k]
        lines.append(f"## {k}")
        lines.append(f"- total: `{w['total']}`")
        lines.append(f"- ok: `{w['ok']}`")
        lines.append(f"- ok_rate: `{w['ok_rate']}`")
        if w["top_failed_ids"]:
            lines.append("- top_failed_ids:")
            for row in w["top_failed_ids"]:
                lines.append(f"  - {row['id']}: {row['count']}")
        else:
            lines.append("- top_failed_ids: (none)")
        lines.append("")

    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"✅ wrote {OUT_JSON}")
    print(f"✅ wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
