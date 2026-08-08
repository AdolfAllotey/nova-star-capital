from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("/opt/nsc/data/preprod/governance/governance_engine_pro.json")
DST = Path("/opt/nsc/data/preprod/equities_offensive/governance/governance_engine_pro.json")

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main() -> int:
    gov = read_json(SRC, default={}) or {}

    # fallback safe (UI / checks never break)
    if not isinstance(gov, dict) or not gov:
        gov = {
            "ts": utc_now_iso(),
            "engine": "equ_sync_governance_v1",
            "env": "unknown",
            "mode": "PREPROD",
            "action_policy": "SIMULATED_EXECUTION",
            "hard_block": False,
            "caps": {
                "max_orders_per_run": 5,
                "max_notional_eur_per_run": 2500.0,
                "max_notional_eur_per_asset": 1000.0
            },
            "notes": ["global governance missing/empty; wrote fallback SIMULATED_EXECUTION"],
        }
    else:
        source_timestamp = gov.get("timestamp") or gov.get("ts") or gov.get("updated_at")
        gov = dict(gov)
        gov.setdefault("engine", "equ_sync_governance_v1")
        gov["synced_from"] = str(SRC)
        gov["source_timestamp"] = source_timestamp
        gov["synced_at"] = utc_now_iso()
        gov["sync_status"] = "synced_from_global_governance"

    write_json(DST, gov)
    print({"saved": str(DST), "action_policy": gov.get("action_policy"), "hard_block": gov.get("hard_block")})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
