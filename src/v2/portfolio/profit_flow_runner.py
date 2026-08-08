import json
from pathlib import Path
from datetime import datetime, timezone

from src.v2.portfolio.capital_flow_engine import compute_profit_flow


BRICK_FLOWS_PATH = Path("/opt/nsc/app/data/portfolio/brick_flows.json")
TRANSFER_INSTR_PATH = Path("/opt/nsc/app/data/portfolio/transfer_instructions.jsonl")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(brick, profit_eur, capital_eur, source_pool="unknown_pool"):
    result = compute_profit_flow(
        brick=brick,
        profit_eur=float(profit_eur),
        capital_eur=float(capital_eur),
    )

    existing = read_json(BRICK_FLOWS_PATH, {"ts": None, "engine": "profit_flow_runner_v1", "flows": []})
    if not isinstance(existing, dict):
        existing = {"ts": None, "engine": "profit_flow_runner_v1", "flows": []}

    flows = existing.get("flows", [])
    if not isinstance(flows, list):
        flows = []

    flow_row = {
        "flow_id": f"{brick}_{int(capital_eur)}_{int(profit_eur)}",
        "ts": utc_now(),
        "brick": brick,
        "capital_eur": capital_eur,
        "source_pool": source_pool,
        "flow": result,
    }
    if any(f.get("flow_id") == flow_row["flow_id"] for f in flows):
        print("FLOW ALREADY PROCESSED - SKIP")
        return
    flows.append(flow_row)

    payload = {
        "ts": utc_now(),
        "engine": "profit_flow_runner_v1",
        "flows": flows,
    }
    write_json(BRICK_FLOWS_PATH, payload)

    distributed = result.get("distributed", {})
    for pocket, amount in distributed.items():
        amount = float(amount or 0.0)
        if amount <= 0:
            continue

        append_jsonl(
            TRANSFER_INSTR_PATH,
            {
                "ts": utc_now(),
                "engine": "profit_flow_runner_v1",
                "brick": brick,
                "from_pool": source_pool,
                "to_pocket": pocket,
                "amount_eur": round(amount, 6),
                "status": "pending",
                "transfer_mode": "manual_review_required",
            },
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # test manuel par défaut
    run(
        brick="crypto",
        profit_eur=1000,
        capital_eur=7000,
        source_pool="crypto_exchange_pool",
    )
