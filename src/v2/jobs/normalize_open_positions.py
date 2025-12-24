#!/usr/bin/env python3
import os, json, pathlib, tempfile, datetime as dt

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
SRC1 = pathlib.Path(DATA_ROOT) / "simulation" / "open_positions.json"
SRC2 = pathlib.Path(DATA_ROOT) / "trading" / "open_positions.json"
OUT  = pathlib.Path(DATA_ROOT) / "simulation" / "open_positions.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(p):
    if not p.exists() or p.stat().st_size == 0: return None
    with open(p,"r") as f:
        try: return json.load(f)
        except: return None

def normalize(obj):
    if isinstance(obj, dict) and "items" in obj: obj = obj["items"]
    if not isinstance(obj, list): return []
    rows=[]
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
    for r in obj:
        if not isinstance(r, dict): continue
        token = (r.get("token") or r.get("symbol") or "").upper()
        qty   = float(r.get("qty") or r.get("quantity") or 0)
        entry = float(r.get("entry") or r.get("entry_price") or r.get("price") or 0)
        pnl   = float(r.get("pnl") or r.get("pnl_eur") or 0)
        exit_reason = r.get("exit_reason")
        ts = r.get("ts") or r.get("timestamp") or now
        if not token or qty <= 0 or entry <= 0:  # garde-fous basiques
            continue
        rows.append({
            "token": token, "qty": round(qty, 8), "entry": round(entry, 8),
            "pnl": round(pnl, 2), "exit_reason": exit_reason, "ts": ts
        })
    return rows

src = load_json(SRC1) or load_json(SRC2) or []
norm = normalize(src)

tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(OUT.parent))
json.dump(norm, tmp, indent=2)
tmp.close()
os.replace(tmp.name, OUT)
print(f"[OK] normalized {len(norm)} positions -> {OUT}")
