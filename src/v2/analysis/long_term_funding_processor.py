from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from src.v2.analysis.long_term_transfer_engine import create_long_term_transfer


QUEUE_PATH = Path("/opt/nsc/src/v2/data/long_term/long_term_funding_queue.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def enqueue_long_term_funding(source_brick: str, amount_eur: float, symbol: str | None = None, notes: str | None = None):
    queue = read_json(
        QUEUE_PATH,
        {
            "status": "ok",
            "engine": "long_term_funding_queue_v1",
            "items": [],
            "updated_at": None,
        },
    )

    item = {
        "queue_id": f"ltq_{uuid4().hex[:12]}",
        "source_brick": source_brick,
        "amount_eur": float(amount_eur),
        "symbol": symbol.upper() if symbol else None,
        "status": "pending",
        "notes": notes,
        "created_at": utc_now(),
        "processed_at": None,
        "result": None,
    }

    queue.setdefault("items", []).append(item)
    queue["updated_at"] = utc_now()
    write_json(QUEUE_PATH, queue)
    return item


def process_long_term_funding_queue():
    queue = read_json(
        QUEUE_PATH,
        {
            "status": "ok",
            "engine": "long_term_funding_queue_v1",
            "items": [],
            "updated_at": None,
        },
    )

    items = queue.get("items", [])
    processed = []

    for item in items:
        if item.get("status") != "pending":
            continue

        try:
            result = create_long_term_transfer(
                source_brick=item["source_brick"],
                amount_eur=float(item["amount_eur"]),
                symbol=item.get("symbol"),
            )
            item["status"] = "processed"
            item["processed_at"] = utc_now()
            item["result"] = {
                "engine": result.get("engine"),
                "symbol": result.get("symbol"),
                "amount_eur": result.get("amount_eur"),
                "quantity": result.get("quantity"),
                "updated_at": result.get("updated_at"),
            }
            processed.append(item["queue_id"])
        except Exception as e:
            item["status"] = "failed"
            item["processed_at"] = utc_now()
            item["result"] = {"error": str(e)}

    queue["updated_at"] = utc_now()
    write_json(QUEUE_PATH, queue)

    return {
        "status": "ok",
        "engine": "long_term_funding_processor_v1",
        "processed_count": len(processed),
        "processed_ids": processed,
        "updated_at": utc_now(),
    }


if __name__ == "__main__":
    out = process_long_term_funding_queue()
    print(json.dumps(out, ensure_ascii=False, indent=2))
