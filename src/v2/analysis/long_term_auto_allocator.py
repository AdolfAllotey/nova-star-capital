from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from src.v2.analysis.long_term_funding_processor import enqueue_long_term_funding


INPUT_DIR = Path("/opt/nsc/src/v2/data/long_term/funding_inputs")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_input_file(path: Path):
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        return None

    enabled = bool(payload.get("enabled", False))
    brick = payload.get("brick") or path.stem
    net_profit_eur = float(payload.get("net_profit_eur") or 0)
    lt_allocation_pct = float(payload.get("lt_allocation_pct") or 0)
    min_trigger_eur = float(payload.get("min_trigger_eur") or 0)
    preferred_symbol = payload.get("preferred_symbol")

    if not enabled or net_profit_eur <= 0:
        return {
            "brick": brick,
            "status": "skipped",
            "reason": "disabled_or_no_profit",
            "queued_amount_eur": 0,
        }

    amount_eur = net_profit_eur * lt_allocation_pct

    if amount_eur < min_trigger_eur:
        return {
            "brick": brick,
            "status": "skipped",
            "reason": "below_trigger",
            "queued_amount_eur": 0,
        }

    item = enqueue_long_term_funding(
        source_brick=brick,
        amount_eur=amount_eur,
        symbol=preferred_symbol,
        notes=f"Auto-allocation from {brick}",
    )

    payload["last_queued_amount_eur"] = amount_eur
    payload["last_queue_id"] = item["queue_id"]
    payload["last_processed_candidate_at"] = utc_now()
    payload["net_profit_eur"] = 0
    payload["updated_at"] = utc_now()
    write_json(path, payload)

    return {
        "brick": brick,
        "status": "queued",
        "reason": "ok",
        "queued_amount_eur": amount_eur,
        "queue_id": item["queue_id"],
    }


def main():
    results = []
    for path in sorted(INPUT_DIR.glob("*.json")):
        results.append(process_input_file(path))

    out = {
        "status": "ok",
        "engine": "long_term_auto_allocator_v1",
        "results": results,
        "updated_at": utc_now(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
