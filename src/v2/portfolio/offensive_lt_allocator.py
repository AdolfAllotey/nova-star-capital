import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request


POLICY_PATH = Path("/opt/nsc/app/src/v2/config/offensive_lt_policy.json")
REGIME_PATH = Path("/opt/nsc/app/data/equities_offensive/market/market_regime.json")
TRANSFERS_PATH = Path("/opt/nsc/app/data/portfolio/transfer_instructions.jsonl")
POSITIONS_PATH = Path("/opt/nsc/app/data/portfolio/long_term_positions.json")


YAHOO_TICKERS = {
    "QQQ": "QQQ",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "META": "META",
    "AMZN": "AMZN",
    "SPY": "SPY",
    "COST": "COST",
    "BRK.B": "BRK-B",
    "VIG": "VIG",
    "KO": "KO",
    "JNJ": "JNJ",
    "ASML": "ASML",
    "TSMC": "TSM",
    "LVMH": "MC.PA",
    "VWCE": "VWCE.DE",
    "IEUR": "IEUR",
    "NESN": "NESN.SW",
    "AI": "AI.PA",
    "NOVO_B": "NOVO-B.CO"
}

FALLBACK_PRICES_USD = {
    "QQQ": 430.0,
    "MSFT": 390.0,
    "NVDA": 120.0,
    "META": 480.0,
    "AMZN": 175.0,
    "SPY": 510.0,
    "COST": 725.0,
    "BRK.B": 410.0,
    "VIG": 190.0,
    "KO": 60.0,
    "JNJ": 155.0,
    "ASML": 950.0,
    "TSMC": 145.0,
    "LVMH": 820.0,
    "VWCE": 125.0,
    "IEUR": 58.0,
    "NESN": 115.0,
    "AI": 185.0,
    "NOVO_B": 95.0,
    "CASH_PROXY": 1.0
}


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


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_yahoo_price(symbol_code: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_code}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    result = (((data or {}).get("chart") or {}).get("result") or [None])[0] or {}
    meta = result.get("meta") or {}
    price = meta.get("regularMarketPrice")

    if price is None:
        raise ValueError(f"No Yahoo price for {symbol_code}")

    return float(price)


def fetch_usd_to_eur_rate():
    try:
        eurusd = fetch_yahoo_price("EURUSD=X")
        if eurusd and eurusd > 0:
            return 1.0 / float(eurusd)
    except Exception:
        pass
    return 0.92


def get_equity_price_eur(symbol: str, usd_to_eur_rate: float):
    if symbol == "CASH_PROXY":
        return 1.0

    try:
        if symbol in YAHOO_TICKERS:
            px_usd = fetch_yahoo_price(YAHOO_TICKERS[symbol])
            return px_usd * usd_to_eur_rate
    except Exception:
        pass

    return float(FALLBACK_PRICES_USD.get(symbol, 1.0)) * usd_to_eur_rate


def normalize_regime(raw):
    if raw in ("risk_on", "risk_off", "balanced"):
        return raw
    return "balanced"


def main():
    policy = read_json(POLICY_PATH, default={}) or {}
    regime_payload = read_json(REGIME_PATH, default={}) or {}
    transfers = read_jsonl(TRANSFERS_PATH)
    registry = read_json(POSITIONS_PATH, default={}) or {}

    positions = registry.get("positions", [])
    if not isinstance(positions, list):
        positions = []

    processed_transfer_ids = registry.get("processed_transfer_ids", [])
    if not isinstance(processed_transfer_ids, list):
        processed_transfer_ids = []

    regime = normalize_regime(regime_payload.get("regime", "balanced"))
    regime_weights = ((policy.get("regimes") or {}).get(regime) or {})
    usd_to_eur_rate = fetch_usd_to_eur_rate()

    if not regime_weights:
        raise RuntimeError(f"No LT policy found for regime={regime}")

    lt_flows = []
    for row in transfers:
        if row.get("to_pocket") != "lt":
            continue
        if row.get("brick") != "equities_offensive":
            continue

        transfer_id = f'{row.get("brick","unknown")}::{row.get("ts","")}::{row.get("amount_eur",0)}'
        if transfer_id in processed_transfer_ids:
            continue

        lt_flows.append((transfer_id, row))

    if not lt_flows:
        print(json.dumps({
            "status": "ok",
            "engine": "offensive_lt_allocator_v1",
            "message": "no new offensive LT flows",
            "regime": regime
        }, ensure_ascii=False, indent=2))
        return

    created = []

    for transfer_id, flow in lt_flows:
        amount_eur = float(flow.get("amount_eur", 0.0) or 0.0)
        flow_ts = flow.get("ts", utc_now())

        for symbol, weight in regime_weights.items():
            invested = round(amount_eur * float(weight), 6)
            price = float(get_equity_price_eur(symbol, usd_to_eur_rate))
            units = round(invested / price, 10) if price > 0 else 0.0

            pos = {
                "position_id": f"lt_equities_offensive_{symbol}_{flow_ts.replace(':','').replace('-','')}",
                "symbol": symbol,
                "asset_name": symbol,
                "asset_class": "equity",
                "bucket": "equities_lt",
                "source_brick": "equities_offensive",
                "invested_eur": invested,
                "units": units,
                "avg_price_eur": price,
                "custody_type": "broker_account",
                "custody_location": "IBKR",
                "custody_status": "active",
                "status": "ACTIVE"
            }
            positions.append(pos)
            created.append(pos)

        processed_transfer_ids.append(transfer_id)

    registry["status"] = "ok"
    registry["engine"] = "long_term_positions_registry_v1"
    registry["currency"] = "EUR"
    registry["positions"] = positions
    registry["processed_transfer_ids"] = processed_transfer_ids
    registry["updated_at"] = utc_now()

    write_json(POSITIONS_PATH, registry)

    print(json.dumps({
        "status": "ok",
        "engine": "offensive_lt_allocator_v1",
        "regime": regime,
        "created_positions": len(created),
        "symbols": sorted(list(regime_weights.keys())),
        "updated_at": registry["updated_at"]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
