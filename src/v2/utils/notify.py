#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dispatcher de notifications (Telegram + stubs Email/Slack).
- Si le token/chat_id Telegram ne sont pas configurés, la fonction renvoie False sans lever d'exception.
- Appel typique : send_telegram("hello world")
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

# Essayez d'importer requests, mais restez silencieux si absent.
try:
    import requests  # apt-get install -y python3-requests
except Exception:  # pragma: no cover
    requests = None

BASE = Path(__file__).resolve().parents[1]          # .../src/v2
CONF = BASE / "config" / "notify.config.json"       # fichier JSON de config

def _load_conf() -> dict:
    if CONF.exists():
        try:
            return json.loads(CONF.read_text() or "{}")
        except Exception:
            return {}
    return {}

def send_telegram(text: str, parse_mode: Optional[str] = None, disable_web_page_preview: bool = True) -> bool:
    """
    Envoie un message Telegram via Bot API.
    Retourne True si succès, False sinon (aucune exception levée).
    """
    cfg = _load_conf().get("telegram", {})
    token = cfg.get("bot_token")
    chat_id = cfg.get("chat_id")
    if not token or not chat_id or requests is None:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        r = requests.post(url, json=payload, timeout=10)
        return bool(r.ok)
    except Exception:
        return False

def send_email(subject: str, body: str) -> bool:
    """Stub — à brancher plus tard (SMTP/SendGrid/Mailgun)."""
    return False

def send_slack(text: str) -> bool:
    """Stub — à brancher plus tard (Incoming Webhook)."""
    return False
