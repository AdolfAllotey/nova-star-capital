#!/usr/bin/env python3
import os, json, pathlib, datetime as dt, random

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
OUT = pathlib.Path(DATA_ROOT) / "risk" / "worst_trades.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# MOCK: 5 pires trades (pertes négatives en €)
tokens = ["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","MATIC","DOT","DOGE"]
items = []
now = dt.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
for _ in range(5):
    t = random.choice(tokens)
    loss = round(-abs(random.uniform(50, 1500)), 2)
    items.append({
        "token": t,
        "loss_eur": loss,
        "reason": "Stop-loss déclenché (mock)",
        "ts": now
    })

payload = {"updated_at": now, "items": items}
with open(OUT, "w") as f:
    json.dump(payload, f, indent=2)

print(f"[OK] wrote {OUT} ({len(items)} items)")
