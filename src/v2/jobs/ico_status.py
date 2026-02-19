# -*- coding: utf-8 -*-
"""
ico_status.py – agrège l'état du pipeline ICO pour l'UI.
Lit: data/ico/ico_candidates.json, ico_screened.json, ico_scored.json, ico_allocation.json
Écrit: data/ico/ico_status.json
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict
from src.v2.utils.logsafe import get_logger
from src.v2.ico.ico_types import iso_now_utc
from datetime import datetime, timezone


log = get_logger("ico_status")

DATA = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)

ICO_DIR = os.path.join(DATA, "ico")
OUT = os.path.join(ICO_DIR, "ico_status.json")

FILES = {
    "candidates": os.path.join(ICO_DIR, "ico_candidates.json"),
    "screened": os.path.join(ICO_DIR, "ico_screened.json"),
    "scored": os.path.join(ICO_DIR, "ico_scored.json"),
    "allocation": os.path.join(ICO_DIR, "ico_allocation.json"),
}

def _safe_load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"items": [], "updated_at": None, "_missing": True}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"items": [], "updated_at": None, "_invalid": True}
        if "items" not in data:
            data["items"] = []
        if "updated_at" not in data:
            # compat: certains flux ont generated_at
            data["updated_at"] = data.get("generated_at")
        return data
    except Exception as e:
        return {"items": [], "updated_at": None, "_error": str(e)}

def main() -> None:
    parts = {k: _safe_load(p) for k, p in FILES.items()}

    status = {
        "updated_at": max([parts[k].get("updated_at") or "" for k in parts] or [""]) or None,
        "generated_at": iso_now_utc(),
        "counts": {k: len(parts[k].get("items") or []) for k in parts},
        "paths": FILES,
        "ok": True,
        "notes": [],
    }

    # simple health flags
    for k, d in parts.items():
        if d.get("_missing"):
            status["ok"] = False
            status["notes"].append(f"{k}:missing")
        if d.get("_invalid"):
            status["ok"] = False
            status["notes"].append(f"{k}:invalid_json_shape")
        if d.get("_error"):
            status["ok"] = False
            status["notes"].append(f"{k}:read_error:{d.get('_error')}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(status, f, indent=2)
    os.replace(tmp, OUT)

    status.setdefault('generated_at', status.get('generated_at') or status.get('updated_at') or _iso_now())
dt = _parse_dt(status.get('generated_at') or status.get('updated_at'))
status['last_run_seconds_ago'] = _seconds_since(dt)
status['health'] = _build_health(status.get('ok', False), status.get('notes'))
log.info("[ICO] status ok=%s -> %s", status["ok"], OUT)

if __name__ == "__main__":
    main()


def _iso_now():
    return datetime.now(timezone.utc).isoformat()

def _parse_dt(x):
    if not x:
        return None
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None

def _seconds_since(dt):
    if not dt:
        return None
    try:
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None

def _build_health(ok: bool, notes):
    notes = notes or []
    warnings = [n for n in notes if isinstance(n, str) and ("warn" in n or "warning" in n)]
    errors = [n for n in notes if isinstance(n, str) and ("error" in n or "failed" in n)]
    stage = "ok" if ok else "degraded"
    return {"ok": bool(ok), "stage": stage, "warnings": warnings, "errors": errors}

