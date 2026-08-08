from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

CANDIDATES_PATH = DATA_DIR / "discovery" / "discovery_candidates.json"
HISTORY_PATH = DATA_DIR / "discovery" / "discovery_history.json"
SUMMARY_PATH = DATA_DIR / "discovery" / "persistence_summary.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_ts(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> None:
    now = datetime.now(timezone.utc)
    now_s = utc_now()

    raw = load_json(CANDIDATES_PATH, default={}) or {}
    items = raw.get("items", [])
    if not isinstance(items, list):
        items = []

    history = load_json(HISTORY_PATH, default={}) or {}
    if not isinstance(history, dict):
        history = {}

    seen_now = set()

    for row in items:
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        seen_now.add(symbol)

        chg = float(row.get("chg_24h") or 0.0)
        score = float(row.get("discovery_score") or row.get("score") or 0.0)
        sources = row.get("discovery_sources") or row.get("sources") or []

        h = history.get(symbol) or {}

        first_seen = h.get("first_seen") or now_s
        observations = int(h.get("observations") or 0) + 1
        max_gain = max(float(h.get("max_gain") or chg), chg)
        min_gain = min(float(h.get("min_gain") or chg), chg)
        max_score = max(float(h.get("max_score") or score), score)

        first_dt = parse_ts(first_seen) or now
        hours_present = round((now - first_dt).total_seconds() / 3600, 2)

        previous_gain = h.get("last_chg_24h")
        try:
            gain_delta = round(chg - float(previous_gain), 4) if previous_gain is not None else 0.0
        except Exception:
            gain_delta = 0.0

        all_sources = sorted(set(h.get("sources") or []) | set(sources))

        if observations >= 6 and gain_delta > 0:
            persistence_status = "accelerating"
        elif observations >= 6 and gain_delta < 0:
            persistence_status = "decelerating"
        elif observations >= 3:
            persistence_status = "persistent"
        else:
            persistence_status = "new"

        persistence_score = min(
            100.0,
            35.0
            + min(observations, 20) * 2.0
            + min(hours_present, 48) * 0.5
            + min(len(all_sources), 5) * 5.0
            + max(0.0, min(gain_delta, 20.0)) * 0.8
        )

        history[symbol] = {
            "symbol": symbol,
            "first_seen": first_seen,
            "last_seen": now_s,
            "observations": observations,
            "hours_present": hours_present,
            "last_chg_24h": chg,
            "gain_delta": gain_delta,
            "max_gain": round(max_gain, 4),
            "min_gain": round(min_gain, 4),
            "last_discovery_score": round(score, 4),
            "max_score": round(max_score, 4),
            "sources": all_sources,
            "sources_count": len(all_sources),
            "persistence_status": persistence_status,
            "persistence_score": round(persistence_score, 2),
        }

    # Marque les tokens non revus sur ce run
    for symbol, h in list(history.items()):
        if symbol not in seen_now:
            h["currently_visible"] = False
        else:
            h["currently_visible"] = True

    visible = [h for h in history.values() if h.get("currently_visible")]
    visible.sort(key=lambda x: (x.get("persistence_score", 0), x.get("last_discovery_score", 0)), reverse=True)

    summary = {
        "status": "ok",
        "generated_at": now_s,
        "engine": "discovery_persistence_v1",
        "visible_count": len(visible),
        "history_count": len(history),
        "top_persistent": visible[:15],
    }

    save_json(HISTORY_PATH, history)
    save_json(SUMMARY_PATH, summary)

    print({
        "output": str(SUMMARY_PATH),
        "engine": "discovery_persistence_v1",
        "visible_count": len(visible),
        "history_count": len(history),
        "top": [x.get("symbol") for x in visible[:10]],
    })


if __name__ == "__main__":
    main()
