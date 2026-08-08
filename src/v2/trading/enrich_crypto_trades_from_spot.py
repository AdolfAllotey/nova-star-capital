import json
from pathlib import Path

TRADE_PATH = Path("/opt/nsc/data/preprod/trading/trade_simulation.json")
SPOT_PATH = Path("/opt/nsc/data/preprod/market/crypto_spot_prices.json")

print("RUNNING FILE:", __file__)
print("TRADE_PATH exists:", TRADE_PATH.exists())
print("SPOT_PATH exists:", SPOT_PATH.exists())

trades = json.loads(TRADE_PATH.read_text(encoding="utf-8")) if TRADE_PATH.exists() else []
spots_raw = json.loads(SPOT_PATH.read_text(encoding="utf-8")) if SPOT_PATH.exists() else {}

spots = {}
if isinstance(spots_raw, dict):
    for k, v in spots_raw.items():
        try:
            if isinstance(v, (int, float, str)):
                spots[str(k).upper().strip()] = float(v)
            elif isinstance(v, dict):
                for field in ("price_eur", "eur", "price", "current_price_eur", "current_price", "usd"):
                    if v.get(field) is not None:
                        spots[str(k).upper().strip()] = float(v.get(field))
                        break
        except Exception:
            pass

print("SPOTS =", spots)

enriched = []

for t in trades:
    if not isinstance(t, dict):
        continue

    row = dict(t)
    token = str(row.get("token", "")).upper().strip()
    if not token:
        enriched.append(row)
        continue

    notional = float(row.get("notional_eur", row.get("amount", 0.0)) or 0.0)
    live_price = spots.get(token)

    existing_entry = row.get("entry_price_eur")
    try:
        existing_entry = float(existing_entry) if existing_entry not in (None, "", 0, 0.0) else None
    except Exception:
        existing_entry = None

    existing_qty = row.get("quantity_units")
    try:
        existing_qty = float(existing_qty) if existing_qty not in (None, "", 0, 0.0) else None
    except Exception:
        existing_qty = None

    # prix d'entrée figé si déjà présent
    if existing_entry is not None:
        entry_price = existing_entry
    else:
        entry_price = float(live_price) if live_price and live_price > 0 else None

    # quantité figée si déjà présente
    if existing_qty is not None:
        quantity_units = existing_qty
    else:
        quantity_units = round(notional / entry_price, 10) if entry_price and entry_price > 0 else None

    # seul le prix courant bouge
    current_price = float(live_price) if live_price and live_price > 0 else None

    entry_value = round(quantity_units * entry_price, 2) if quantity_units and entry_price else round(notional, 2)
    current_value = round(quantity_units * current_price, 2) if quantity_units and current_price else round(entry_value, 2)
    pnl_eur = round(current_value - entry_value, 2)

    row["entry_price_eur"] = round(entry_price, 8) if entry_price else None
    row["quantity_units"] = round(quantity_units, 10) if quantity_units else None
    row["current_price_eur"] = round(current_price, 8) if current_price else None
    row["entry_value_eur"] = entry_value
    row["current_value_eur"] = current_value
    row["pnl_eur"] = pnl_eur

    print(
        "TOKEN", token,
        "ENTRY", row["entry_price_eur"],
        "CURRENT", row["current_price_eur"],
        "QTY", row["quantity_units"],
        "PNL", row["pnl_eur"]
    )

    enriched.append(row)

TRADE_PATH.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
print("DONE")
