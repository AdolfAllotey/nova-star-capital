from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

MAPS = {
    "/opt/nsc/data/preprod/defensive/prices.json": [
        "KO", "PEP", "JNJ", "USMV", "VDC", "VIG", "XLV", "AI.PA", "DUK", "SO"
    ],
    "/opt/nsc/data/preprod/bonds/prices.json": [
        "SHY", "IEF", "TLT", "LQD"
    ],
    "/opt/nsc/data/preprod/metals/prices.json": [
        "GLD", "SLV"
    ],
}

ALIASES = {
    "AI.PA": "AI"
}

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

def fetch_last(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="5d")
        if data is None or data.empty:
            return None
        return float(data["Close"].dropna().iloc[-1])
    except Exception:
        return None

def main():
    for out, symbols in MAPS.items():
        prices = {}
        for sym in symbols:
            px = fetch_last(sym)
            if px and px > 0:
                prices[ALIASES.get(sym, sym)] = round(px, 4)

        payload = {
            "status": "ok" if prices else "empty",
            "engine": "preprod_price_refresher_yfinance_v1",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "prices": prices,
        }

        # legacy-compatible flat output
        write_json(Path(out), prices)
        write_json(Path(out).with_name("prices_meta.json"), payload)
        print(out, prices)

if __name__ == "__main__":
    main()
