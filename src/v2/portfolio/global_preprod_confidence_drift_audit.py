from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

BASE = Path("/opt/nsc/data/preprod")
PORTFOLIO_TARGET = BASE / "portfolio" / "portfolio_target.json"
OUT = BASE / "portfolio" / "audit" / "global_confidence_drift_audit.json"
HISTORY = BASE / "portfolio" / "audit" / "confidence_history.jsonl"

OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

def extract_confidence(doc: dict):
    confidence = doc.get("brick_confidence") or doc.get("confidence") or {}
    if isinstance(confidence, dict) and confidence:
        vals = []
        for v in confidence.values():
            try:
                vals.append(float(v))
            except Exception:
                pass
        if vals:
            return round(mean(vals), 6), confidence

    for key in ("global_confidence", "confidence_score", "avg_confidence"):
        if key in doc:
            try:
                return round(float(doc[key]), 6), {key: doc[key]}
            except Exception:
                pass

    return None, confidence

target = load_json(PORTFOLIO_TARGET, {})
current_value, raw_confidence = extract_confidence(target)

now = datetime.now(timezone.utc).isoformat()

sample = {
    "timestamp": now,
    "source": str(PORTFOLIO_TARGET),
    "confidence_value": current_value,
    "raw_confidence": raw_confidence,
}

with HISTORY.open("a", encoding="utf-8") as f:
    f.write(json.dumps(sample) + "\n")

samples = []
try:
    for line in HISTORY.read_text(encoding="utf-8").splitlines()[-300:]:
        if line.strip():
            samples.append(json.loads(line))
except Exception:
    samples = []

values = [
    s.get("confidence_value")
    for s in samples
    if isinstance(s.get("confidence_value"), (int, float))
]

unique_values = sorted(set(values))
last_10 = values[-10:]
last_30 = values[-30:]

stuck_last_10 = len(set(last_10)) == 1 and len(last_10) >= 10
stuck_last_30 = len(set(last_30)) == 1 and len(last_30) >= 30

drift_from_first = None
drift_from_previous = None

if len(values) >= 2:
    drift_from_first = round(values[-1] - values[0], 6)
    drift_from_previous = round(values[-1] - values[-2], 6)

if current_value is None:
    drift_state = "MISSING"
elif stuck_last_30:
    drift_state = "STUCK_CRITICAL"
elif stuck_last_10:
    drift_state = "STUCK_WATCH"
elif drift_from_previous == 0:
    drift_state = "STABLE"
else:
    drift_state = "MOVING"

payload = {
    "status": "ok",
    "engine": "global_preprod_confidence_drift_audit_v1",
    "generated_at": now,
    "source": str(PORTFOLIO_TARGET),
    "current_confidence": current_value,
    "display_confidence_pct": None if current_value is None else round(current_value * 100, 2),
    "samples": len(values),
    "unique_values": len(unique_values),
    "drift_from_first": drift_from_first,
    "drift_from_previous": drift_from_previous,
    "stuck_last_10": stuck_last_10,
    "stuck_last_30": stuck_last_30,
    "drift_state": drift_state,
    "raw_confidence": raw_confidence,
    "recommendation": (
        "Investigate frontend or allocator source: confidence appears stuck."
        if drift_state.startswith("STUCK")
        else "Confidence metric appears dynamic or insufficient history."
    ),
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
