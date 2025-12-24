#!/usr/bin/env python3
import os, json, pathlib, tempfile, datetime as dt

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
SRC1 = pathlib.Path(DATA_ROOT) / "reports" / "monthly_costs.json"
SRC2 = pathlib.Path(DATA_ROOT) / "reports" / "costs_raw.json"
OUT  = pathlib.Path(DATA_ROOT) / "reports" / "monthly_costs.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(p):
    if not p.exists() or p.stat().st_size == 0:
        return None
    with open(p, "r") as f:
        try: return json.load(f)
        except json.JSONDecodeError: return None

def norm_month(s):
    s = str(s).strip()
    for fmt in ("%Y-%m", "%Y/%m", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = dt.datetime.strptime(s, fmt).date()
            return f"{d.year:04d}-{d.month:02d}"
        except: pass
    return None

def to_pairs(payload):
    pairs=[]
    if isinstance(payload, dict):
        for k,v in payload.items():
            pairs.append((k, float(v)))
    elif isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict): continue
            m = str(row.get("month") or row.get("Month") or row.get("date") or "")
            c = row.get("costs") or row.get("cost") or row.get("value")
            if m and c is not None:
                pairs.append((m, float(c)))
    return pairs

src = load_json(SRC1) or load_json(SRC2) or []
pairs = to_pairs(src)

norm, seen = [], set()
for m, c in pairs:
    mm = norm_month(m)
    if not mm or mm in seen: continue
    seen.add(mm)
    norm.append({"month": mm, "costs": round(float(c), 2)})

norm.sort(key=lambda x: x["month"])

tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(OUT.parent))
json.dump(norm, tmp, indent=2)
tmp.close()
os.replace(tmp.name, OUT)
print(f"[OK] normalized {len(norm)} rows -> {OUT}")
