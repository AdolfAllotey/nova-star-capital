from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

INPUT_DIR = Path("/opt/nsc/data/preprod/portfolio/inputs")
OUT = Path("/opt/nsc/data/preprod/portfolio/audit/global_brick_confidence_audit.json")
HISTORY = Path("/opt/nsc/data/preprod/portfolio/audit/brick_confidence_history.jsonl")

OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

now = datetime.now(timezone.utc).isoformat()
rows = []

for path in sorted(INPUT_DIR.glob("*_portfolio_input.json")):
    doc = load_json(path)
    brick = doc.get("brick") or path.name.replace("_portfolio_input.json", "")
    confidence = doc.get("confidence")
    target_weight = doc.get("target_weight")
    regime = doc.get("regime")
    enabled = doc.get("enabled")

    rows.append({
        "brick": brick,
        "file": str(path),
        "enabled": enabled,
        "confidence": confidence,
        "target_weight": target_weight,
        "regime": regime,
        "portfolio_role": doc.get("portfolio_role"),
    })

sample = {
    "timestamp": now,
    "bricks": {r["brick"]: r["confidence"] for r in rows},
}

with HISTORY.open("a", encoding="utf-8") as f:
    f.write(json.dumps(sample) + "\n")

history = []
try:
    for line in HISTORY.read_text(encoding="utf-8").splitlines()[-100:]:
        if line.strip():
            history.append(json.loads(line))
except Exception:
    history = []

brick_values = {}
for h in history:
    for brick, value in (h.get("bricks") or {}).items():
        brick_values.setdefault(brick, []).append(value)

brick_status = {}
for brick, values in brick_values.items():
    clean = [v for v in values if isinstance(v, (int, float))]
    unique = len(set(clean))
    samples = len(clean)

    if samples >= 10 and unique == 1:
        status = "STATIC_WATCH"
    elif samples >= 30 and unique == 1:
        status = "STATIC_CRITICAL"
    elif unique > 1:
        status = "DYNAMIC"
    else:
        status = "INSUFFICIENT_HISTORY"

    brick_status[brick] = {
        "samples": samples,
        "unique_values": unique,
        "status": status,
        "latest": clean[-1] if clean else None,
    }

static_bricks = [
    b for b, s in brick_status.items()
    if s["status"] in ("STATIC_WATCH", "STATIC_CRITICAL")
]

payload = {
    "status": "ok",
    "engine": "global_preprod_brick_confidence_audit_v1",
    "generated_at": now,
    "input_dir": str(INPUT_DIR),
    "bricks_checked": len(rows),
    "static_bricks_count": len(static_bricks),
    "static_bricks": static_bricks,
    "rows": rows,
    "brick_status": brick_status,
    "recommendation": (
        "Some brick confidence inputs appear static. Inspect their portfolio input exporters."
        if static_bricks
        else "No static confidence confirmed yet or insufficient history."
    ),
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
