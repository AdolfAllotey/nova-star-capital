# src/v2/monitoring/twitter_scraper.py
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict, Any, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

LOGGER = get_logger("twitter_scraper")

DATA_DIR = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_ROOT") or "data"
STATE_DIR = os.path.join(DATA_DIR, "state")
OUT_PATH = os.path.join(DATA_DIR, "twitter_data.json")
STATE_PATH = os.path.join(STATE_DIR, "twitter_state.json")

API_URL = "https://api.twitter.com/2/tweets/search/recent"

TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "1").lower() in ("1", "true", "yes", "on")
DEFAULT_QUERY = os.getenv("TWITTER_QUERY", "bitcoin OR ethereum OR solana OR airdrop OR listing")
MAX_RESULTS = int(os.getenv("TWITTER_MAX_RESULTS", "25"))
MAX_PAGES = int(os.getenv("TWITTER_MAX_PAGES", "2"))
REQUEST_TIMEOUT = int(os.getenv("TWITTER_TIMEOUT", "20"))
MAX_RETRIES = int(os.getenv("TWITTER_MAX_RETRIES", "3"))
MAX_STORED_TWEETS = int(os.getenv("TWITTER_MAX_STORED", "1500"))

def _parse_body(body_bytes: bytes) -> Dict[str, Any]:
    body = (body_bytes or b"").decode("utf-8", errors="replace")
    if not body:
        return {}
    try:
        return json.loads(body)
    except Exception:
        return {"_raw": body}

def _http_get(url: str, headers: Dict[str, str], timeout: int = 20) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 200))
            raw_headers = dict(resp.headers.items())
            payload = _parse_body(resp.read())
            return status, raw_headers, payload

    except urllib.error.HTTPError as e:
        # IMPORTANT: urllib lève HTTPError pour 4xx/5xx -> on récupère status/headers/body
        status = int(getattr(e, "code", 0) or 0)
        raw_headers = dict(getattr(e, "headers", {}).items()) if getattr(e, "headers", None) else {}
        payload = _parse_body(e.read() if hasattr(e, "read") else b"")
        return status, raw_headers, payload

def _sleep_backoff(attempt: int) -> None:
    t = min(15.0, 1.2 * (2 ** max(0, attempt - 1)))
    time.sleep(t)

def _merge_unique(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]], key: str = "id") -> List[Dict[str, Any]]:
    seen = {str(x.get(key)) for x in existing if x.get(key) is not None}
    out = list(existing)
    for it in new_items:
        k = str(it.get(key))
        if k and k not in seen:
            out.append(it)
            seen.add(k)
    return out

def _trim_keep_last(items: List[Dict[str, Any]], max_keep: int) -> List[Dict[str, Any]]:
    if len(items) <= max_keep:
        return items
    return items[-max_keep:]

def _build_headers(bearer: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "User-Agent": os.getenv("TWITTER_USER_AGENT", "NovaStarBot/1.0 (+ops@novastar.local)"),
        "Accept": "application/json",
    }

def _is_rate_limited(status: int, payload: Dict[str, Any]) -> bool:
    if status == 429:
        return True
    title = str(payload.get("title", "")).lower()
    detail = str(payload.get("detail", "")).lower()
    return ("too many requests" in title) or ("too many requests" in detail)

def _get_reset_ts(headers: Dict[str, str]) -> Optional[int]:
    reset = headers.get("x-rate-limit-reset") or headers.get("X-Rate-Limit-Reset")
    if not reset:
        return None
    try:
        return int(reset)
    except Exception:
        return None

async def scrape_twitter() -> None:
    ensure_dir(DATA_DIR)
    ensure_dir(STATE_DIR)

    if not TWITTER_ENABLED:
        LOGGER.info("Twitter disabled via TWITTER_ENABLED=0 — scraping ignoré.")
        return

    bearer = os.getenv("TWITTER_BEARER") or os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer:
        LOGGER.info("TWITTER_BEARER absent — scraping Twitter ignoré.")
        return

    state = load_json_file(STATE_PATH, default={}) or {}
    next_allowed = int(state.get("next_allowed_ts") or 0)
    now = int(time.time())

    if now < next_allowed:
        wait = next_allowed - now
        LOGGER.warning(f"Twitter: rate-limited — skip until reset in {wait}s (next_allowed_ts={next_allowed})")
        return

    existing = load_json_file(OUT_PATH, default=[])
    if isinstance(existing, dict):
        existing = existing.get("data", [])
    if not isinstance(existing, list):
        existing = []

    headers = _build_headers(bearer)
    query = DEFAULT_QUERY
    max_results = max(10, min(100, MAX_RESULTS))

    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "id,text,created_at,author_id,lang,public_metrics",
    }

    total_new = 0
    next_token: Optional[str] = None

    for page in range(MAX_PAGES):
        if next_token:
            params["next_token"] = next_token
        else:
            params.pop("next_token", None)

        url = API_URL + "?" + urllib.parse.urlencode(params)

        last_status = 0
        last_headers: Dict[str, str] = {}
        last_payload: Dict[str, Any] = {}
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            status, resp_headers, payload = _http_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            last_status, last_headers, last_payload = status, resp_headers, payload

            if _is_rate_limited(status, payload):
                reset_ts = _get_reset_ts(resp_headers) or (int(time.time()) + 15 * 60)
                state["next_allowed_ts"] = int(reset_ts)
                state["last_429_ts"] = int(time.time())
                save_json_file(STATE_PATH, state)

                wait = max(0, int(reset_ts) - int(time.time()))
                LOGGER.warning(
                    f"Twitter: 429 rate-limit. next_allowed_ts={reset_ts} (wait≈{wait}s) "
                    f"limit={resp_headers.get('x-rate-limit-limit')} remaining={resp_headers.get('x-rate-limit-remaining')}"
                )
                return

            if status != 200:
                LOGGER.warning(f"Twitter HTTP {status} (attempt {attempt}/{MAX_RETRIES}): {payload}")
                _sleep_backoff(attempt)
                continue

            success = True
            break

        if not success:
            LOGGER.warning(f"Twitter: failed after retries (status={last_status}).")
            # On garde le state sans casser le pipeline
            state["last_fail_ts"] = int(time.time())
            state["last_fail_status"] = int(last_status or 0)
            save_json_file(STATE_PATH, state)
            return

        data = last_payload.get("data") or []
        meta = last_payload.get("meta") or {}

        if isinstance(data, list) and data:
            before = len(existing)
            existing = _merge_unique(existing, data, key="id")
            after = len(existing)
            total_new += max(0, after - before)

            existing = _trim_keep_last(existing, MAX_STORED_TWEETS)
            save_json_file(OUT_PATH, existing)

        next_token = meta.get("next_token")
        if not next_token:
            break

    state["last_run_ts"] = int(time.time())
    save_json_file(STATE_PATH, state)

    LOGGER.info(f"Twitter: {total_new} nouveaux tweets (total={len(existing)})")
