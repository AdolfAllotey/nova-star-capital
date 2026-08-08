import json
from datetime import datetime


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data, path):
    if not isinstance(data, dict):
        data = {"value": data}
    data["timestamp"] = datetime.utcnow().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def clamp(value, min_val=0, max_val=1):
    return max(min_val, min(max_val, value))
