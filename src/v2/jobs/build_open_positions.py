#!/usr/bin/env python3
import os, json, pathlib, datetime as dt, random

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
OUT = pathlib.Path(DATA_ROOT) / "simulation" / "open_positions.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# MOCK: positions ouvertes
tokens = ["BTC","ETH","SOL","LINK","OP","ARB","INJ","TIA","ATOM","APT"]
def r(): return random.uniform  # alias

items = []
now = dt.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
for _ in range(4):
    t = random.choice(tokens)
    qty = round(r()(0.1, 5.0), 4)
    entry = round(r()(10, 70000), 2)
    pnl = round(r()(-300, 1500), 2)  # en €
    items.append({
        "token": t,
        "qty": qty,
        "entry": entry,
        "pnl": pnl,
        "exit_reason": None,
        "ts": now
    })

with open(OUT, "w") as f:
    json.dump(items, f, indent=2)

print(f"[OK] wrote {OUT} ({len(items)} positions)")
