import json
from pathlib import Path
from datetime import datetime, timezone


TRANSFER_PATH = Path("/opt/nsc/app/data/portfolio/transfer_instructions.jsonl")
PORTFOLIO_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio.json")


LT_WEIGHTS = {
    "BTC": 0.50,
    "ETH": 0.30,
    "SOL": 0.20
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_portfolio():
    if not PORTFOLIO_PATH.exists():
        return {
            "status": "ok",
            "engine": "long_term_allocator_v2",
            "positions": {},
            "total_value_eur": 0.0,
            "flows_processed": [],
        }

    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Migration V1 -> V2
    if "positions" not in data:
        allocation = data.get("allocation", {}) if isinstance(data, dict) else {}
        positions = {}

        if isinstance(allocation, dict):
            for asset, amount in allocation.items():
                positions[asset] = {
                    "amount_eur": float(amount or 0.0),
                    "weight": float((data.get("weights") or {}).get(asset, 0.0) or 0.0),
                }

        data = {
            "status": "ok",
            "engine": "long_term_allocator_v2",
            "positions": positions,
            "total_value_eur": float(data.get("total_lt_capital_eur", 0.0) or 0.0),
            "flows_processed": [],
        }

    if "flows_processed" not in data or not isinstance(data.get("flows_processed"), list):
        data["flows_processed"] = []

    if "positions" not in data or not isinstance(data.get("positions"), dict):
        data["positions"] = {}

    if "total_value_eur" not in data:
        data["total_value_eur"] = 0.0

    return data


def save_portfolio(data):
    data["status"] = "ok"
    data["engine"] = "long_term_allocator_v2"
    data["timestamp"] = utc_now()
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def run():
    transfers = read_jsonl(TRANSFER_PATH)
    portfolio = read_portfolio()

    processed_ids = set(portfolio.get("flows_processed", []))

    new_flows = [
        t for t in transfers
        if t.get("to_pocket") == "lt"
        and t.get("ts") not in processed_ids
    ]

    if not new_flows:
        print("NO NEW LT FLOWS")
        save_portfolio(portfolio)
        return

    total_added = 0.0

    for flow in new_flows:
        amount = float(flow.get("amount_eur", 0.0) or 0.0)
        total_added += amount

        for asset, weight in LT_WEIGHTS.items():
            alloc = amount * weight

            if asset not in portfolio["positions"]:
                portfolio["positions"][asset] = {
                    "amount_eur": 0.0,
                    "weight": 0.0
                }

            portfolio["positions"][asset]["amount_eur"] += alloc

        portfolio["flows_processed"].append(flow.get("ts"))

    portfolio["total_value_eur"] = round(
        sum(float(p.get("amount_eur", 0.0) or 0.0) for p in portfolio["positions"].values()),
        6
    )

    # recalcul poids
    for asset, p in portfolio["positions"].items():
        if portfolio["total_value_eur"] > 0:
            p["weight"] = round(
                float(p.get("amount_eur", 0.0) or 0.0) / portfolio["total_value_eur"],
                6
            )
        else:
            p["weight"] = 0.0

    save_portfolio(portfolio)

    print(json.dumps({
        "status": "updated",
        "engine": "long_term_allocator_v2",
        "added_eur": round(total_added, 2),
        "total_lt": round(portfolio["total_value_eur"], 2),
        "positions": portfolio["positions"]
    }, indent=2))


if __name__ == "__main__":
    run()
