import json
from pathlib import Path

def write_json(out_dir: Path, name: str, payload):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
