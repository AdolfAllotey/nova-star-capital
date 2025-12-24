# src/v2/monitoring/telegram_scraper.py
from __future__ import annotations

import os
import time
import json
import errno
import asyncio
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

LOGGER = get_logger("telegram_scraper")

# --- Paths / env ---
DATA_DIR = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_ROOT") or "data"
STATE_DIR = os.path.join(DATA_DIR, "state")

OUT_PATH = os.path.join(DATA_DIR, "telegram_data.json")
STATE_PATH = os.path.join(STATE_DIR, "telegram_state.json")

# Session user (créée via scripts/telegram_login.py)
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "telegram_user")
SESSION_PATH = os.getenv("TELEGRAM_SESSION_PATH") or os.path.join(STATE_DIR, SESSION_NAME)

LOCK_PATH = os.getenv("TELEGRAM_LOCK_PATH") or (SESSION_PATH + ".lock")

# --- Config ---
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "1").lower() in ("1", "true", "yes", "on")

MAX_CHATS = int(os.getenv("TELEGRAM_MAX_CHATS", "50"))          # ex: 40, 300
MAX_PER_CHAT = int(os.getenv("TELEGRAM_MAX_PER_CHAT", "50"))   # messages max par chat/run
MAX_STORED = int(os.getenv("TELEGRAM_MAX_STORED", "1500"))     # cap global
LOCK_TTL_S = int(os.getenv("TELEGRAM_LOCK_TTL_S", "1200"))     # 20 min par défaut
FLOOD_WAIT_BUFFER_S = int(os.getenv("TELEGRAM_FLOOD_WAIT_BUFFER_S", "2"))

# Telethon creds
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

# IMPORTANT: en Option A tu l’as commenté => on ne l’utilise pas.
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def _now_ts() -> int:
    return int(time.time())


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _read_lock(lock_path: str) -> Tuple[Optional[int], Optional[int]]:
    """
    lock file format: {"pid":123, "ts":1700000000}
    (compat: ancien format "pid ts")
    """
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return None, None
        try:
            obj = json.loads(raw)
            pid = int(obj.get("pid")) if obj.get("pid") is not None else None
            ts = int(obj.get("ts")) if obj.get("ts") is not None else None
            return pid, ts
        except Exception:
            parts = raw.split()
            pid = int(parts[0]) if len(parts) > 0 else None
            ts = int(parts[1]) if len(parts) > 1 else None
            return pid, ts
    except FileNotFoundError:
        return None, None
    except Exception:
        return None, None


def _acquire_lock(lock_path: str, ttl_s: int) -> bool:
    """
    Lock atomique.
    Si lock existant:
      - stale (TTL dépassé) ou PID mort -> suppression
      - sinon -> refuse (un autre process tourne)
    """
    ensure_dir(os.path.dirname(lock_path) or ".")

    if os.path.exists(lock_path):
        pid, ts = _read_lock(lock_path)
        age = (_now_ts() - ts) if ts else None

        stale = False
        if pid is not None and not _pid_alive(pid):
            stale = True
        if age is not None and age > ttl_s:
            stale = True

        if stale:
            try:
                os.remove(lock_path)
                LOGGER.warning(
                    "Telegram: lock stale supprimé (%s) pid=%s age_s=%s",
                    lock_path, pid, age
                )
            except Exception:
                return False
        else:
            return False

    payload = {"pid": os.getpid(), "ts": _now_ts()}
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload))
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise


def _release_lock(lock_path: str) -> None:
    try:
        if os.path.exists(lock_path):
            pid, _ts = _read_lock(lock_path)
            if pid is None or pid == os.getpid():
                os.remove(lock_path)
    except Exception:
        pass


def _normalize_msg(msg: Any, chat: Any, source: str = "telegram") -> Dict[str, Any]:
    text = getattr(msg, "message", None) or ""
    ts = int(getattr(msg, "date").timestamp()) if getattr(msg, "date", None) else _now_ts()

    sender_id = None
    try:
        sid = getattr(msg, "sender_id", None)
        if sid is not None:
            sender_id = int(sid)
    except Exception:
        sender_id = None

    chat_id = None
    chat_title = None
    try:
        cid = getattr(chat, "id", None)
        chat_id = int(cid) if cid is not None else None
        chat_title = getattr(chat, "title", None) or getattr(chat, "name", None)
    except Exception:
        pass

    mid = None
    try:
        mid_raw = getattr(msg, "id", None)
        mid = int(mid_raw) if mid_raw is not None else None
    except Exception:
        mid = None

    return {
        "source": source,
        "ts": ts,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "sender_id": sender_id,
        "message_id": mid,
        "text": text,
    }


def _dedupe_keep_latest(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dédup simple par (chat_id, message_id). Garde la version la plus récente (ts).
    """
    seen: Dict[Tuple[Optional[int], Optional[int]], Dict[str, Any]] = {}
    for it in items:
        key = (it.get("chat_id"), it.get("message_id"))
        prev = seen.get(key)
        if prev is None or (it.get("ts", 0) or 0) >= (prev.get("ts", 0) or 0):
            seen[key] = it
    out = list(seen.values())
    out.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return out


async def scrape_telegram() -> None:
    if not TELEGRAM_ENABLED:
        LOGGER.info("Telegram: disabled (TELEGRAM_ENABLED=0)")
        return

    ensure_dir(DATA_DIR)
    ensure_dir(STATE_DIR)

    if not API_ID or not API_HASH:
        LOGGER.error("Telegram: TELEGRAM_API_ID / TELEGRAM_API_HASH manquants")
        return

    # Lock (anti concurrence / sqlite locked)
    if not _acquire_lock(LOCK_PATH, LOCK_TTL_S):
        LOGGER.warning("Telegram: lock actif (%s) — un autre process tourne, skip.", LOCK_PATH)
        return

    t0 = time.perf_counter()
    start_ts = _now_ts()

    try:
        from telethon import TelegramClient
        from telethon.errors import FloodWaitError

        api_id = int(API_ID)
        api_hash = str(API_HASH)

        # On utilise la session user uniquement.
        # BOT_TOKEN peut exister mais en Option A tu l’as commenté => non utilisé.
        if BOT_TOKEN:
            LOGGER.warning(
                "Telegram: TELEGRAM_BOT_TOKEN est défini mais Option A recommande de le désactiver. "
                "Le scraper utilise la session user (%s).",
                SESSION_PATH,
            )

        client = TelegramClient(SESSION_PATH, api_id, api_hash)

        state = load_json_file(STATE_PATH, default={})
        per_chat: Dict[str, int] = {}
        if isinstance(state, dict) and isinstance(state.get("per_chat", {}), dict):
            per_chat = state.get("per_chat", {}) or {}

        existing = load_json_file(OUT_PATH, default=[])
        if not isinstance(existing, list):
            existing = []

        LOGGER.info("Telegram scraper start (session=%s)", SESSION_PATH)

        await client.connect()

        # On attend une session user déjà loginée via scripts/telegram_login.py
        if not await client.is_user_authorized():
            LOGGER.error("Telegram: session non autorisée. Relance scripts/telegram_login.py en TTY.")
            return

        dialogs = await client.get_dialogs(limit=MAX_CHATS)
        LOGGER.info("Telegram: dialogs détectés = %d", len(dialogs))

        new_items: List[Dict[str, Any]] = []
        dialogs_kept = 0

        for d in dialogs:
            if dialogs_kept >= MAX_CHATS:
                break

            chat = getattr(d, "entity", None)
            if chat is None:
                continue

            chat_id = getattr(chat, "id", None)
            if chat_id is None:
                continue

            dialogs_kept += 1
            chat_key = str(int(chat_id))

            min_id = 0
            try:
                min_id = int(per_chat.get(chat_key, 0) or 0)
            except Exception:
                min_id = 0

            fetched = 0
            last_seen_id = min_id

            try:
                async for msg in client.iter_messages(chat, limit=MAX_PER_CHAT, min_id=min_id):
                    it = _normalize_msg(msg, chat, source="telegram")
                    if it.get("message_id") is not None:
                        last_seen_id = max(last_seen_id, int(it["message_id"]))
                    new_items.append(it)
                    fetched += 1

                if fetched > 0:
                    per_chat[chat_key] = int(last_seen_id)

            except FloodWaitError as e:
                wait_s = int(getattr(e, "seconds", 0) or 0) + FLOOD_WAIT_BUFFER_S
                LOGGER.warning("Telegram: FloodWait sur chat=%s, sleep=%ss", chat_key, wait_s)
                await asyncio.sleep(max(1, wait_s))
            except Exception as e:
                LOGGER.warning("Telegram: erreur sur chat=%s (%s)", chat_key, e)

        # Merge + dedupe + cap
        merged = existing + new_items
        merged = _dedupe_keep_latest(merged)
        merged = merged[:MAX_STORED]

        total_new = len(new_items)

        # Persist
        save_json_file(OUT_PATH, merged)

        duration_s = int(round(time.perf_counter() - t0))
        out_state = {
            "updated_at": int(time.time()),
            "session": SESSION_NAME,
            "max_chats": MAX_CHATS,
            "max_per_chat": MAX_PER_CHAT,
            "max_stored": MAX_STORED,
            "dialogs_kept": dialogs_kept,
            "duration_s": duration_s,
            "per_chat": per_chat,
        }
        save_json_file(STATE_PATH, out_state)

        LOGGER.info(
            "Telegram: %d nouveaux messages (dialogs_kept=%d, total=%d)",
            total_new, dialogs_kept, len(merged)
        )

    except Exception as e:
        LOGGER.exception("Telegram scraper error: %s", e)
    finally:
        try:
            # Best effort disconnect
            try:
                from telethon import TelegramClient  # noqa: F401
            except Exception:
                pass
        finally:
            _release_lock(LOCK_PATH)
            LOGGER.info("Telegram scraper done")


def main() -> None:
    asyncio.run(scrape_telegram())


if __name__ == "__main__":
    main()
