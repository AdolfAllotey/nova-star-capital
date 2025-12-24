# src/v2/analysis/token_extractor.py
import os, re
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

LOGGER = get_logger("token_extractor")

DATA_DIR = "src/v2/data"
OUT_LIST = f"{DATA_DIR}/selected_tokens.json"
OUT_COUNTS = f"{DATA_DIR}/selected_tokens_counts.json"

# ---- Règles d'extraction ----
RE_CASHTAG = re.compile(r"\$([A-Za-z]{2,10})\b")
RE_HASHTAG = re.compile(r"#([A-Za-z0-9]{2,12})\b")
RE_PAIR    = re.compile(r"\b([A-Za-z]{2,10})\s*[-/]\s*([A-Za-z]{2,10})\b")
RE_UPPER   = re.compile(r"\b([A-Z]{2,6})\b")  # mots full caps courts

FIATS = {"USD", "USDT", "USDC", "EUR", "GBP", "JPY", "CHF", "CNY", "RUB", "AUD", "CAD"}
COMMON = {  # mots fréquents à ignorer même en caps
    "NFT","AI","DEFI","DEX","CEX","L2","L1","APY","TVL","ATH","FUD","FOMO","PUMP","DUMP","MOON",
    "BTC","ETH"  # <- on les garde souvent, mais on peut forcer en whitelist
}

# par défaut, on **autorise** BTC/ETH via whitelist pour ne pas les perdre
DEFAULT_WHITELIST = {"BTC","ETH"}
DEFAULT_BLACKLIST = {
    "USD","USDT","USDC","EUR","GBP","JPY","CHF","CNY","RUB","AUD","CAD",
    "ETHEREUM","BITCOIN"  # mots complets, pas tickers
}

def _iter_texts(payload: Any) -> Iterable[str]:
    """Extrait les champs texte usuels depuis un json liste/dict."""
    if isinstance(payload, list):
        for it in payload:
            if isinstance(it, dict):
                for key in ("text","content","message","title","body","selftext"):
                    v = it.get(key)
                    if isinstance(v, str) and v.strip():
                        yield v
            elif isinstance(it, str) and it.strip():
                yield it
    elif isinstance(payload, dict):
        for key in ("text","content","message","title","body","selftext"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                yield v
        for key in ("items","data","messages","posts"):
            arr = payload.get(key)
            if isinstance(arr, list):
                for sub in _iter_texts(arr):
                    yield sub

def _norm(token: str) -> str:
    return token.strip().upper()

def _is_plausible(sym: str, whitelist: set, blacklist: set) -> bool:
    s = _norm(sym)
    if s in whitelist:
        return True
    if s in blacklist:  # fiat etc.
        return False
    if 2 <= len(s) <= 6 and s.isalpha():
        return True
    return False

def _extract_from_text(t: str) -> List[str]:
    toks: List[str] = []
    # cashtags/hashtags
    toks += [m.group(1) for m in RE_CASHTAG.finditer(t)]
    toks += [m.group(1) for m in RE_HASHTAG.finditer(t)]
    # paires (on prend la jambe gauche, ex: BTC/USDT -> BTC)
    for m in RE_PAIR.finditer(t):
        left, right = m.group(1), m.group(2)
        toks.append(left)
        # si la jambe droite n'est pas fiat (ex: ETH-BTC), on peut aussi la garder
        if _norm(right) not in FIATS:
            toks.append(right)
    # mots FULL CAPS courts
    toks += [m.group(1) for m in RE_UPPER.finditer(t)]
    return toks

def _from_structured(items: Any) -> List[str]:
    """Certains scrapers mettent directement token/symbol."""
    out: List[str] = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                for k in ("token","symbol","ticker","base","quote"):
                    v = it.get(k)
                    if isinstance(v, str):
                        out.append(v)
    elif isinstance(items, dict):
        for k in ("token","symbol","ticker","base","quote"):
            v = items.get(k)
            if isinstance(v, str):
                out.append(v)
    return out

def extract_tokens(top_n: int = None, min_freq: int = None) -> Dict[str, int]:
    """Retourne un dict {TOKEN:count} trié par fréquence."""
    ensure_dir(DATA_DIR)

    # paramètres via .env
    try:
        top_n = top_n or int(os.getenv("TOKENS_TOP_N", "15"))
    except Exception:
        top_n = 15
    try:
        min_freq = min_freq or int(os.getenv("TOKENS_MIN_FREQ", "2"))
    except Exception:
        min_freq = 2

    whitelist = set(DEFAULT_WHITELIST)
    blenv = os.getenv("TOKENS_WHITELIST","").strip()
    if blenv:
        whitelist |= { _norm(x) for x in blenv.split(",") if x.strip() }

    blacklist = set(DEFAULT_BLACKLIST) | FIATS | COMMON
    blenv2 = os.getenv("TOKENS_BLACKLIST","").strip()
    if blenv2:
        blacklist |= { _norm(x) for x in blenv2.split(",") if x.strip() }

    texts: List[str] = []
    counts = Counter()

    # charge les sources
    tw = load_json_file(f"{DATA_DIR}/twitter_data.json", default=[])
    rd = load_json_file(f"{DATA_DIR}/reddit_data.json",  default=[])
    tg = load_json_file(f"{DATA_DIR}/telegram_data.json",default=[])

    for payload in (tw, rd, tg):
        # textes bruts
        for t in _iter_texts(payload):
            for tok in _extract_from_text(t):
                s = _norm(tok)
                if _is_plausible(s, whitelist, blacklist):
                    counts[s] += 1
        # champs structurés éventuels
        for s in _from_structured(payload):
            s = _norm(s)
            if _is_plausible(s, whitelist, blacklist):
                counts[s] += 1

    # applique min_freq (sauf whitelisted)
    filtered = {k:v for k,v in counts.items() if v >= min_freq or k in whitelist}

    # tri par fréquence puis alpha
    sorted_items: List[Tuple[str,int]] = sorted(filtered.items(), key=lambda kv:(-kv[1], kv[0]))
    if top_n:
        sorted_items = sorted_items[:top_n]

    # sortie fichiers
    final_tokens = [k for k,_ in sorted_items]
    save_json_file(OUT_LIST, final_tokens)
    save_json_file(OUT_COUNTS, {k:v for k,v in sorted_items})

    LOGGER.info(f"Extracteur tokens: {len(final_tokens)} retenus (min_freq={min_freq}, top_n={top_n})")
    return dict(sorted_items)

def run_token_extractor():
    extract_tokens()
