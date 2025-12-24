# src/v2/monitoring/reddit_scraper.py
import os, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from typing import List, Dict, Any, Set
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

LOGGER = get_logger("reddit_scraper")

DATA_DIR = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_ROOT") or "data"
STATE_DIR = os.path.join(DATA_DIR, "state")
OUT_PATH = os.path.join(DATA_DIR, "reddit_data.json")
STATE_PATH = os.path.join(STATE_DIR, "reddit_state.json")

MAX_SEEN_IDS = int(os.getenv("REDDIT_MAX_SEEN_IDS", "5000"))

UA = "Mozilla/5.0 (X11; Linux x86_64) NovaStarBot/1.0 (+contact: ops@novastar.local)"

def _http_get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return resp.read()

def _merge_unique(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    seen = {str(x.get(key)) for x in existing if key in x}
    out = list(existing)
    for it in new_items:
        k = str(it.get(key))
        if k and k not in seen:
            out.append(it)
            seen.add(k)
    return out

def _parse_reddit_rss(xml_bytes: bytes) -> List[Dict[str, Any]]:
    # Parse un Atom/RSS de Reddit et renvoie des items uniformisés
    items: List[Dict[str, Any]] = []
    root = ET.fromstring(xml_bytes)
    # Atom (api reddit renvoie souvent du Atom)
    # espaces de noms fréquents
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }
    # Essaye Atom <entry>
    entries = root.findall(".//atom:entry", ns)
    if not entries:
        # fallback RSS 2.0 <item>
        entries = root.findall(".//item")

    for e in entries:
        # champs communs
        title = (e.findtext("atom:title", default="", namespaces=ns) or
                 (e.findtext("title") or ""))
        link = (e.findtext("atom:link", default="", namespaces=ns) or
                (e.findtext("link") or ""))
        if not link:
            # Atom link est un élément avec attrib href
            link_el = e.find("atom:link", ns)
            if link_el is not None:
                link = link_el.attrib.get("href", "")

        # id
        pid = (e.findtext("atom:id", default="", namespaces=ns) or
               (e.findtext("id") or ""))

        # pub date
        created = (e.findtext("atom:updated", default="", namespaces=ns) or
                   e.findtext("atom:published", default="", namespaces=ns) or
                   e.findtext("pubDate", default=""))

        # description / content
        content = (e.findtext("atom:content", default="", namespaces=ns) or
                   e.findtext("description", default="") or "")

        if not pid:
            # si pas d'id, utilise le lien
            pid = link

        items.append({
            "id": pid,
            "title": title,
            "text": content,
            "url": link,
            "created": created,
            "source": "reddit",
        })
    return items

async def scrape_reddit():
    ensure_dir(DATA_DIR); ensure_dir(STATE_DIR)

    subs_env = os.getenv("REDDIT_SUBS", "CryptoCurrency,CryptoMarkets")
    subs = [s.strip() for s in subs_env.split(",") if s.strip()]
    limit = min(max(int(os.getenv("REDDIT_LIMIT", "50")), 10), 100)  # pas utilisé directement en RSS

    state = load_json_file(STATE_PATH, default={"seen_ids": []})
    seen_ids: Set[str] = set(state.get("seen_ids") or [])

    collected: List[Dict[str, Any]] = []
    for sub in subs:
        # Flux RSS public (Atom) — plus tolérant
        url = f"https://www.reddit.com/r/{urllib.parse.quote(sub)}/new/.rss"
        try:
            xml_bytes = _http_get(url, timeout=25)
            items = _parse_reddit_rss(xml_bytes)
        except Exception as e:
            LOGGER.warning(f"Echec Reddit r/{sub} RSS: {e}")
            continue

        # filtre nouveaux items
        for it in items:
            pid = it.get("id")
            if not pid or pid in seen_ids:
                continue
            collected.append(it)
            seen_ids.add(pid)

        # petite pause
        time.sleep(1.0)

    existing = load_json_file(OUT_PATH, default=[])
    if not isinstance(existing, list):
        existing = []

    merged = _merge_unique(existing, collected, key="id")
    save_json_file(OUT_PATH, merged)

    # cap pour éviter un state infini
    seen_list = list(seen_ids)
    if len(seen_list) > MAX_SEEN_IDS:
        seen_list = seen_list[-MAX_SEEN_IDS:]
    save_json_file(STATE_PATH, {"seen_ids": sorted(seen_list)})

    LOGGER.info(f"Reddit: {len(collected)} nouveaux posts (total={len(merged)})")
