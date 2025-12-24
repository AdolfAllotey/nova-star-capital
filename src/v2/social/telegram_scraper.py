# src/v2/social/telegram_scraper.py
from __future__ import annotations

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timezone
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Telethon
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import InputPeerChannel, InputPeerChat

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

# ---------- utilitaires env / IO ----------

def _load_env() -> None:
    # charge le .env local à la v2 s’il existe
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path, override=False)
    # et le .env racine si présent
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"), override=False)

def _load_groups() -> List[str]:
    # 1) fichier liste (prioritaire si défini)
    path = os.getenv("TELEGRAM_GROUPS_FILE")
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            groups = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        if groups:
            log.info("[DEBUG] TELEGRAM_GROUPS loaded (file) = %s", ",".join(groups[:10]) + ("..." if len(groups) > 10 else ""))
            return groups

    # 2) variable TELEGRAM_GROUPS (CSV)
    raw = os.getenv("TELEGRAM_GROUPS", "")
    groups = [g.strip() for g in raw.split(",") if g.strip()]
    log.info("[DEBUG] TELEGRAM_GROUPS loaded = %s", ",".join(groups[:10]) + ("..." if len(groups) > 10 else ""))
    return groups

def _out_path() -> str:
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "social")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.realpath(os.path.join(base_dir, "telegram_data.json"))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def _ensure_client_user(api_id: int, api_hash: str, phone: str, session_path: str) -> TelegramClient:
    """
    Crée/retourne un client Telethon *utilisateur* (pas bot).
    Demande un code si première connexion.
    """
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        log.info("🔐 Authentification utilisateur nécessaire — envoi du code à %s", phone)
        await client.send_code_request(phone)
        code = input("Veuillez saisir le code reçu (SMS/App Telegram) : ").strip()
        await client.sign_in(phone=phone, code=code)
    me = await client.get_me()
    log.info("🔌 Connecté en mode USER (%s | bot=%s).", getattr(me, "id", "?"), getattr(me, "bot", False))
    return client

async def _ensure_client_bot(bot_token: str, session_path: str) -> TelegramClient:
    client = TelegramClient(session_path, api_id=0, api_hash="bot", bot_token=bot_token)
    await client.connect()
    me = await client.get_me()
    log.info("🔌 Connecté en mode BOT (%s | username=%s).", getattr(me, "id", "?"), getattr(me, "username", "?"))
    return client

async def _fetch_group_messages(client: TelegramClient, group: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Récupère jusqu'à `limit` messages récents d'un groupe/canal public.
    `group` peut être @handle, t.me/handle, ou nom public.
    """
    try:
        entity = await client.get_entity(group)
    except Exception as e:
        log.warning("⚠️  Impossible de résoudre '%s': %s", group, e)
        return []

    messages: List[Dict[str, Any]] = []
    try:
        async for msg in client.iter_messages(entity, limit=limit):
            messages.append({
                "id": msg.id,
                "date": msg.date.astimezone(timezone.utc).isoformat() if msg.date else None,
                "message": msg.message or "",
                "from_id": getattr(getattr(msg, "from_id", None), "user_id", None),
                "sender": getattr(getattr(msg, "sender", None), "username", None),
            })
    except FloodWaitError as fw:
        log.warning("⏳ FloodWait %ss sur '%s' — tronqué.", fw.seconds, group)
    except RPCError as e:
        log.warning("⚠️ RPCError sur '%s': %s", group, e)
    except Exception as e:
        log.warning("⚠️  Échec sur '%s': %s", group, e)

    return list(reversed(messages))  # messages du plus ancien au plus récent

def _save_json(data: Dict[str, Any], path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    log.info("📦 Données Telegram sauvegardées dans %s", path)

# ---------- fonctions publiques ----------

async def scrape_telegram() -> bool:
    """
    Version *async* pour l’orchestrateur.
    Écrit un JSON de forme:
    {
      "scraped_at": "...",
      "groups": {
        "<nom_groupe>": [ {msg}, ... ],
        ...
      }
    }
    """
    _load_env()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE", "")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Source de vérité : USER si TELEGRAM_FORCE_USER=1 ou si bot_token absent
    force_user = os.getenv("TELEGRAM_FORCE_USER") == "1" or not bot_token
    groups = _load_groups()
    limit = int(os.getenv("TELEGRAM_MESSAGE_LIMIT", "50") or "50")

    out = _out_path()

    client: Optional[TelegramClient] = None
    try:
        if force_user:
            if not api_id or not api_hash or not phone:
                log.warning("⚠️  Variables USER incomplètes (TELEGRAM_API_ID/HASH/PHONE).")
                return False
            client = await _ensure_client_user(int(api_id), api_hash, phone, session_path="state/telegram.user.session")
        else:
            client = await _ensure_client_bot(bot_token, session_path="state/telegram.bot.session")

        result: Dict[str, Any] = {
            "scraped_at": _now_iso(),
            "groups": {}  # dict par nom de groupe
        }

        for g in groups:
            log.info("🔎 Scraping groupe: '%s' (limit=%d)", g, limit)
            msgs = await _fetch_group_messages(client, g, limit=limit)
            result["groups"][g] = msgs

        _save_json(result, out)
        log.info("✅ Scraping Telegram terminé.")
        return True

    finally:
        if client:
            await client.disconnect()

# Point d’entrée CLI (permet: `python -m src.v2.social.telegram_scraper`)
if __name__ == "__main__":
    # Ici on peut utiliser asyncio.run, on est en script autonome
    try:
        ok = asyncio.run(scrape_telegram())
        raise SystemExit(0 if ok else 1)
    except KeyboardInterrupt:
        raise SystemExit(130)
