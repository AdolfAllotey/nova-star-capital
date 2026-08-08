from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path("/opt/nsc/data/preprod")
KILL_SWITCH_PATH = DATA_DIR / "trading/kill_switch.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    KILL_SWITCH_PATH.parent.mkdir(parents=True, exist_ok=True)

    current = read_json(KILL_SWITCH_PATH, {}) or {}

    refreshed = {
        "enabled": bool(current.get("enabled", False)),
        "hard_block": bool(current.get("hard_block", False)),
        "soft_block": bool(current.get("soft_block", False)),
        "soft_veto": bool(current.get("soft_veto", False)),
        "mode": current.get("mode") or "normal",
        "source": "kill_switch_refresher",
        "previous_source": current.get("source"),
        "reasons": current.get("reasons") if isinstance(current.get("reasons"), list) else [],
        "updated_at": utc_now(),
        "note": "Refreshed without changing kill-switch decision.",
    }

    KILL_SWITCH_PATH.write_text(
        json.dumps(refreshed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(refreshed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
