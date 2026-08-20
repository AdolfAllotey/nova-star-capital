#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_top_movers.py
- Source 1: CoinGecko (si clé/quotas -> meilleur coverage)
- Fallback : Binance (USDT spot)
- Ecrit:   $NSC_DATA_ROOT/market/top_movers.json
- Archive: $NSC_DATA_ROOT/market/archive/top_movers-<ts>.json
- Log:     /opt/nsc/src/v2/logs/build_top_movers.log
"""

import os, sys, json, time, datetime, pathlib, gzip, traceback
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# --------- Config chemins ---------
DATA_ROOT = os.environ.get("NSC_DATA_ROOT") or os.environ.get("NSC_DATA_DIR") or "/opt/nsc/data/preprod"
DATA_ROOT = DATA_ROOT.rstrip("/")
OUT_DIR   = f"{DATA_ROOT}/market"
OUT_FILE  = f"{OUT_DIR}/top_movers.json"
ARCHIVE_D = f"{OUT_DIR}/archive"
LOG_FILE = os.environ.get("NSC_TOP_MOVERS_LOG", "/var/log/nsc/preprod/build_top_movers.log")

UA = os.environ.get("NSC_HTTP_UA", "NSC/2.0 (+https://novastarcapital.fr)")
TIMEOUT = 15
TOP_N = 20

def log(msg: str):
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    line = f"{ts} build_top_movers: {msg}\n"
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # on imprime quand même, au cas où
        sys.stderr.write(line)

def http_json(url: str, headers: dict = None):
    headers = headers or {}
    headers.setdefault("User-Agent", UA)
    req = Request(url, headers=headers)
    with urlopen(req, timeout=TIMEOUT) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "application/json" not in ctype and not raw.strip().startswith(b"{") and not raw.strip().startswith(b"["):
            raise ValueError(f"Unexpected content-type: {ctype}")
        return json.loads(raw.decode("utf-8", errors="replace"))

# --------- Normalisation des items ---------
def normalize_items(items):
    # format final minimal (clé -> valeur)
    # id, symbol, name, price, chg_1h, chg_24h, chg_7d, source
    out = []
    for it in items:
        out.append({
            "id":        it.get("id"),
            "symbol":    it.get("symbol"),
            "name":      it.get("name"),
            "price":     it.get("price"),
            "chg_1h":    it.get("chg_1h"),
            "chg_24h":   it.get("chg_24h"),
            "chg_7d":    it.get("chg_7d"),
            "source":    it.get("source"),
            "pair":      it.get("pair"),
            "market_status": it.get("market_status"),
            "spot_trading_allowed": it.get(
                "spot_trading_allowed"
            ),
            "ticker_close_time": it.get(
                "ticker_close_time"
            ),
        })
    return out

# --------- Source: CoinGecko (si accessible) ---------
def fetch_from_coingecko():
    # Sans clé, CoinGecko est souvent bridé; on tente quand même
    # Markets endpoint avec % 1h/24h/7d
    url = ("https://api.coingecko.com/api/v3/coins/markets"
           "?vs_currency=usd&order=market_cap_desc&per_page=150&page=1"
           "&sparkline=false&price_change_percentage=1h,24h,7d")
    js = http_json(url)
    items = []
    for c in js:
        items.append({
            "id": c.get("id"),
            "symbol": (c.get("symbol") or "").upper(),
            "name": c.get("name"),
            "price": c.get("current_price"),
            "chg_1h": (c.get("price_change_percentage_1h_in_currency")),
            "chg_24h": (c.get("price_change_percentage_24h_in_currency")),
            "chg_7d": (c.get("price_change_percentage_7d_in_currency")),
            "source": "coingecko",
            "pair": None,
        })
    # On trie par |24h| décroissant et on garde TOP_N
    items.sort(key=lambda x: abs(x["chg_24h"] or 0), reverse=True)
    return items[:TOP_N]

# --------- Fallback: Binance (USDT) ---------
def fetch_binance_exchange_status():
    """
    Canonical Binance execution-market state.

    A ticker response alone does NOT prove that a symbol is currently
    tradable. Delisted / suspended pairs can remain visible through
    ticker/24hr with historical price-change values.

    Only STATUS=TRADING pairs are eligible for NSC market movers.
    """
    url = "https://api.binance.com/api/v3/exchangeInfo"
    js = http_json(url)

    out = {}
    for row in js.get("symbols", []) if isinstance(js, dict) else []:
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        out[symbol] = {
            "status": str(row.get("status") or "").upper(),
            "isSpotTradingAllowed": bool(
                row.get("isSpotTradingAllowed", False)
            ),
        }

    return out


def fetch_from_binance():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    js = http_json(url)

    market_status = fetch_binance_exchange_status()

    items = []
    for t in js:
        s = str(t.get("symbol") or "").upper().strip()
        if not s.endswith("USDT"):
            continue

        market = market_status.get(s) or {}

        if market.get("status") != "TRADING":
            continue

        if market.get("isSpotTradingAllowed") is not True:
            continue
        # priceChangePercent est une string
        try:
            chg_24h = float(t.get("priceChangePercent", "0"))
            last = float(t.get("lastPrice", "0"))
        except Exception:
            continue
        sym = s.replace("USDT","")
        items.append({
            "id": sym.lower(),
            "symbol": sym,
            "name": sym,   # Binance ne retourne pas de nom lisible
            "price": last,
            "chg_1h": None,     # non dispo via cet endpoint
            "chg_24h": chg_24h,
            "chg_7d": None,     # non dispo
            "source": "binance",
            "pair": s,
            "market_status": market.get("status"),
            "spot_trading_allowed": market.get(
                "isSpotTradingAllowed"
            ),
            "ticker_close_time": t.get("closeTime"),
        })
    # Top N par |24h|
    items.sort(key=lambda x: abs(x["chg_24h"] or 0), reverse=True)
    return items[:TOP_N]

def write_json(out_path, data):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, out_path)

def archive_copy(out_path):
    try:
        os.makedirs(ARCHIVE_D, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dst = f"{ARCHIVE_D}/top_movers-{ts}.json"
        with open(out_path, "rb") as src, open(dst, "wb") as d:
            d.write(src.read())
    except Exception as e:
        log(f"[WARN] archive_copy failed: {e}")

def main():
    try:
        log("start")
        items = []
        # 1) Binance first: best source for tradable USDT pairs in NSC crypto execution.
        try:
            items = fetch_from_binance()
            log(f"binance items={len(items)}")
        except Exception as e:
            log(f"[binance] error: {e}")

        # 2) fallback CoinGecko only if Binance unavailable
        if not items:
            try:
                items = fetch_from_coingecko()
                log(f"coingecko items={len(items)}")
            except Exception as e:
                log(f"[coingecko] error: {e}")

        items = normalize_items(items)

        out = {
            "updated_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "items": items
        }
        write_json(OUT_FILE, out)
        log(f"wrote {len(items)} items -> {OUT_FILE}")

        # Archive si ≥1 item (sinon on évite de multiplier les archives vides)
        if len(items) > 0:
            archive_copy(OUT_FILE)
        log("done")
        return 0
    except Exception as e:
        log(f"[FATAL] {e}\n{traceback.format_exc()}")
        # En cas de plantage, on protège le fichier courant (si besoin)
        try:
            if not os.path.exists(OUT_FILE):
                write_json(OUT_FILE, {"updated_at": None, "items": []})
        except Exception as _:
            pass
        return 1

if __name__ == "__main__":
    sys.exit(main())
