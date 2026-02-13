#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser(description="Validate NSC contract JSON against JSON Schema")
    ap.add_argument("--schema", required=True, help="Path to schema JSON file")
    ap.add_argument("--data", required=True, help="Path to data JSON file to validate")
    args = ap.parse_args()

    schema_path = Path(args.schema)
    data_path = Path(args.data)

    schema = _load_json(schema_path)
    data = _load_json(data_path)

    try:
        from jsonschema import Draft202012Validator
    except Exception as e:
        raise SystemExit(
            "Missing dependency: jsonschema. Install with: pip install jsonschema\n"
            f"Import error: {e}"
        )

    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: e.path)

    if errors:
        print(f"INVALID: {data_path} vs {schema_path}")
        for err in errors[:50]:
            loc = ".".join([str(x) for x in err.path]) if err.path else "(root)"
            print(f"- {loc}: {err.message}")
        raise SystemExit(2)

    print(f"OK: {data_path} matches {schema_path}")

if __name__ == "__main__":
    main()
