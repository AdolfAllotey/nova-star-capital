#!/usr/bin/env python3
import json
from pathlib import Path

SOURCES = {
    "v2_options_inputs": "/opt/nsc/app/src/v2/options_v2/data/options_inputs.json",
    "v2_config": "/opt/nsc/app/src/v2/options_v2/data/options_config_v2.json",
    "v2_volatility_context": "/opt/nsc/app/src/v2/options_v2/data/volatility_context_v2.json",
    "v2_candidates_raw": "/opt/nsc/app/src/v2/options_v2/data/options_v2_candidates_raw.json",
    "v2_candidates_validated": "/opt/nsc/app/src/v2/options_v2/data/options_v2_candidates_validated.json",
    "v2_decisions": "/opt/nsc/app/src/v2/options_v2/data/options_v2_decisions.json",
    "v2_positions": "/opt/nsc/app/src/v2/options_v2/data/options_v2_positions.json",
    "v2_dashboard": "/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json",
    "v1_external_signals": "/opt/nsc/app/src/v2/options/data/external_signals.json",
    "v1_external_watchlists": "/opt/nsc/app/src/v2/options/data/external_watchlists.json",
    "v1_external_equity_positions": "/opt/nsc/app/src/v2/options/data/external_equity_positions.json",
}

OUT = Path("/opt/nsc/data/preprod/options_v3/options_v3_input_inventory.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def load(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return {"_error": str(e)}

def summarize(value):
    if value is None:
        return {"exists": False}
    if isinstance(value, list):
        return {"exists": True, "type": "list", "count": len(value), "sample": value[:2]}
    if isinstance(value, dict):
        return {"exists": True, "type": "dict", "keys": list(value.keys())[:40]}
    return {"exists": True, "type": type(value).__name__}

inventory = {}
for name, path in SOURCES.items():
    inventory[name] = {
        "path": path,
        **summarize(load(path)),
    }

OUT.write_text(json.dumps(inventory, indent=2))
print(json.dumps(inventory, indent=2))
