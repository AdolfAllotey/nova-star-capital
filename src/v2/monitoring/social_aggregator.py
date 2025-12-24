# src/v2/monitoring/social_aggregator.py
import os
import time
import hashlib
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

LOGGER = get_logger("social_aggregator")

DATA_DIR = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_ROOT") or "data"
STATE_DIR = os.path.join(DATA_DIR, "state")

TG_PATH = os.path.join(DATA_DIR, "telegram_data.json")
TW_PATH = os.path.join(DATA_DIR, "twitter_data.json")
RD_PATH = os.path.join(DATA_DIR, "reddit_data.json")

OUT_PATH = os.path.join(DATA_DIR, "social_feed.json")
STATE_PATH = os.path.join(STATE_DIR, "social_feed_state.json")

# Fenêtre glissante + caps
WINDOW_HOURS = int(os.getenv("SOCIAL_WINDOW_HOURS", "48"))
MAX_ITEMS = int(os.getenv("SOCIAL_MAX_ITEMS", "3000"))

def _to_int_ts(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None

def _hash_key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

def _norm_telegram(item: Dict[str, Any]) -> Dict[str, Any]:
    # On tolère plusieurs formats possibles
    chat = item.get("chat") or item.get("chat_title") or item.get("group") or ""
    chat_id = item.get("chat_id") or item.get("peer_id") or ""
    msg_id = item.get("id") or item.get("message_id") or ""

    text = item.get("text") or item.get("message") or ""
    created_at = item.get("created_at") or item.get("date") or ""
    ts = _to_int_ts(item.get("ts")) or _to_int_ts(item.get("timestamp"))

    # fallback ts = now si pas dispo (mais on évite d’en abuser)
    if ts is None:
        ts = int(time.time())

    key = f"telegram:{chat_id}:{msg_id}" if chat_id and msg_id else f"telegram:{_hash_key(chat + '|' + text + '|' + str(ts))}"

    return {
        "id": key,
        "source": "telegram",
        "ts": ts,
        "created_at": created_at,
        "text": text,
        "url": item.get("url") or "",
        "chat": chat,
        "author": item.get("author") or item.get("from") or "",
        "lang": item.get("lang") or "",
        "metrics": item.get("metrics") or {},
        "_raw": item,
    }

def _norm_twitter(item: Dict[str, Any]) -> Dict[str, Any]:
    tid = str(item.get("id") or "")
    text = item.get("text") or ""
    created_at = item.get("created_at") or ""
    ts = _to_int_ts(item.get("ts"))

    if ts is None:
        # pas parfait sans parser ISO, mais ok pour feed "récent"
        ts = int(time.time())

    key = f"twitter:{tid}" if tid else f"twitter:{_hash_key(text + '|' + str(ts))}"

    return {
        "id": key,
        "source": "twitter",
        "ts": ts,
        "created_at": created_at,
        "text": text,
        "url": "",
        "chat": "",
        "author": str(item.get("author_id") or ""),
        "lang": item.get("lang") or "",
        "metrics": item.get("public_metrics") or {},
        "_raw": item,
    }

def _norm_reddit(item: Dict[str, Any]) -> Dict[str, Any]:
    rid = str(item.get("id") or item.get("url") or "")
    text = item.get("text") or item.get("title") or ""
    created_at = item.get("created") or item.get("created_at") or ""
    ts = _to_int_ts(item.get("ts"))

    if ts is None:
        ts = int(time.time())

    key = f"reddit:{rid}" if rid else f"reddit:{_hash_key(text + '|' + str(ts))}"

    return {
        "id": key,
        "source": "reddit",
        "ts": ts,
        "created_at": created_at,
        "text": text,
        "url": item.get("url") or "",
        "chat": item.get("subreddit") or "",
        "author": item.get("author") or "",
        "lang": item.get("lang") or "",
        "metrics": item.get("metrics") or {},
        "_raw": item,
    }

def _dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        k = it.get("id")
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def build_social_feed() -> None:
    ensure_dir(DATA_DIR)
    ensure_dir(STATE_DIR)

    tg = load_json_file(TG_PATH, default=[]) or []
    tw = load_json_file(TW_PATH, default=[]) or []
    rd = load_json_file(RD_PATH, default=[]) or []

    if isinstance(tg, dict): tg = tg.get("data", [])
    if isinstance(tw, dict): tw = tw.get("data", [])
    if isinstance(rd, dict): rd = rd.get("data", [])

    tg_items = [_norm_telegram(x) for x in tg if isinstance(x, dict)]
    tw_items = [_norm_twitter(x) for x in tw if isinstance(x, dict)]
    rd_items = [_norm_reddit(x) for x in rd if isinstance(x, dict)]

    all_items = tg_items + tw_items + rd_items
    all_items = _dedup(all_items)

    # fenêtre glissante
    now = int(time.time())
    min_ts = now - (WINDOW_HOURS * 3600)
    all_items = [x for x in all_items if int(x.get("ts", 0)) >= min_ts]

    # tri + cap
    all_items.sort(key=lambda x: int(x.get("ts", 0)))
    if len(all_items) > MAX_ITEMS:
        all_items = all_items[-MAX_ITEMS:]

    out = {
        "generated_at": now,
        "window_hours": WINDOW_HOURS,
        "counts": {
            "telegram": len([x for x in all_items if x["source"] == "telegram"]),
            "twitter": len([x for x in all_items if x["source"] == "twitter"]),
            "reddit": len([x for x in all_items if x["source"] == "reddit"]),
            "total": len(all_items),
        },
        "items": all_items,
    }

    save_json_file(OUT_PATH, out)
    save_json_file(STATE_PATH, {"generated_at": now, "min_ts": min_ts, "max_items": MAX_ITEMS})

    LOGGER.info(
        "Social feed built: total=%s (tg=%s tw=%s rd=%s) window=%sh -> %s",
        out["counts"]["total"],
        out["counts"]["telegram"],
        out["counts"]["twitter"],
        out["counts"]["reddit"],
        WINDOW_HOURS,
        OUT_PATH,
    )
