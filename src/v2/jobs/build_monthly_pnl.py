#!/usr/bin/env python3
import os, json, datetime as dt, pathlib, random

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
OUT = pathlib.Path(DATA_ROOT) / "reports" / "monthly_pnl.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# MOCK: 12 mois glissants avec PnL en €
today = dt.date.today().replace(day=1)
months = []
for i in range(11, -1, -1):
    m = (today - dt.timedelta(days=32*i)).replace(day=1)
    key = f"{m.year:04d}-{m.month:02d}"
    pnl = round(random.uniform(-500, 2500), 2)  # remplace par tes vraies données
    months.append({"month": key, "pnl": pnl})

with open(OUT, "w") as f:
    json.dump(months, f, indent=2)

print(f"[OK] wrote {OUT} ({len(months)} months)")
