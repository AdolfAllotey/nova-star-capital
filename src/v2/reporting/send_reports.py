from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any

# Import optionnel
try:
    import requests  # type: ignore
except Exception:
    requests = None  # fallback: pas d'envoi réseau

BASE = Path("/opt/nsc/src/v2")
REPORTS = BASE / "data" / "reports"
SETTINGS = BASE / "config" / "settings.json"

def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _send_webhook(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not requests:
        return {"status": "skipped", "reason": "requests_not_installed"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return {"status": "ok", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def send_reports() -> Dict[str, Any]:
    """
    Envoi (optionnel) du daily report via webhook/HTTP.
    Si SETTINGS.reporting.send_enabled=false (ou requests absent), on SKIP proprement.
    """
    cfg = _read_json(SETTINGS) or {}
    reporting = (cfg.get("reporting") or {}) if isinstance(cfg, dict) else {}
    send_enabled = bool(reporting.get("send_enabled", False))
    webhook = reporting.get("webhook_url") or os.getenv("NSC_REPORT_WEBHOOK") or ""

    daily = _read_json(REPORTS / "daily_report.json") or {}
    payload = {
        "title": f"NSC Daily Report — {daily.get('date', '')}",
        "allocator_mode": (daily.get("allocator") or {}).get("mode", "unknown"),
        "equity_eur": (daily.get("equity_eur") or 0.0),
        "generated_at": daily.get("generated_at"),
    }

    if not send_enabled:
        return {"status": "skipped", "reason": "send_disabled", "payload": payload}
    if not webhook:
        return {"status": "skipped", "reason": "no_webhook_configured", "payload": payload}

    return _send_webhook(str(webhook), payload)
