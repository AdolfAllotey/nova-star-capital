#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone

BASE = "/opt/nsc/app/data"
RISK_DIR = os.path.join(BASE, "risk")
os.makedirs(RISK_DIR, exist_ok=True)

PATH = os.path.join(RISK_DIR, "worst_trades.json")
now = datetime.now(timezone.utc).isoformat()

default_doc = {
    "updated_at": now,
    "items": [],
}

def main():
    try:
        if os.path.exists(PATH):
            with open(PATH, "r", encoding="utf-8") as f:
                doc = json.load(f)
            if not isinstance(doc, dict):
                doc = default_doc
            doc.setdefault("updated_at", now)
            doc.setdefault("items", [])
        else:
            doc = default_doc

        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"[normalize_worst_trades] OK -> {PATH}")
    except Exception as e:
        print(f"[normalize_worst_trades] ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
