#!/usr/bin/env python3
import os, json, pathlib, tempfile, datetime as dt

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
SRC1 = pathlib.Path(DATA_ROOT) / "reports" / "monthly_pnl.json"
SRC2 = pathlib.Path(DATA_ROOT) / "reports" / "profitability_raw.json"  # optionnel
OUT  = pathlib.Path(DATA_ROOT) / "reports" / "monthly_pnl.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(p):
    if not p.exists() or p.stat().st_size == 0:
        return None
    with open(p, "r") as f:
        try: return json.load(f)
        except json.JSONDecodeError: return None

def to_pairs(payload):
    # accepte dict {"YYYY-MM": pnl} ou liste d'objets
    pairs = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            pairs.append((k, float(v)))
    elif isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                m = str(row.get("month") or row.get("Month") or row.get("date"))
                if not m: continue
                pnl = row.get("pnl") or row.get("PnL") or row.get("value")
                if pnl is None: continue
                pairs.append((m, float(pnl)))
    return pairs

def norm_month(s):
    # tolère "2025-11", "2025-11-01", "2025/11", etc.
    s = str(s).strip()
    for fmt in ("%Y-%m", "%Y/%m", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = dt.datetime.strptime(s, fmt).date()
            return f"{d.year:04d}-{d.month:02d}"
        except Exception:
            pass
    return None

src = load_json(SRC1) or load_json(SRC2) or []
pairs = to_pairs(src)

norm = []
seen = set()
for m, v in pairs:
    mm = norm_month(m)
    if not mm: continue
    if mm in seen: continue
    seen.add(mm)
    norm.append({"month": mm, "pnl": round(float(v), 2)})

norm.sort(key=lambda x: x["month"])

# Écriture atomique
tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(OUT.parent))
json.dump(norm, tmp, indent=2)
tmp.close()
os.replace(tmp.name, OUT)

print(f"[OK] normalized {len(norm)} rows -> {OUT}")
