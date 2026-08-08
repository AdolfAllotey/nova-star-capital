import json
from datetime import datetime


def save_json(data, path):
    if not isinstance(data, dict):
        data = {"value": data}
    data["timestamp"] = datetime.utcnow().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def round_dict(d, digits=6):
    return {k: round(float(v), digits) for k, v in d.items()}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default
