import os
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# -----------------------------------------------------------------------------
# Logger centralisé
# -----------------------------------------------------------------------------
try:
    from src.v2.utils.logger import get_logger  # type: ignore
    logger = get_logger("price_fetcher")
except Exception:  # fallback si le logger centralisé n'est pas dispo
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("price_fetcher")

# -----------------------------------------------------------------------------
# Config NSC
# -----------------------------------------------------------------------------

NSC_ENV = os.getenv("NSC_ENV", "LOCAL")
DATA_ROOT = Path(os.getenv("NSC_DATA_DIR") or "/opt/nsc/data/preprod").resolve()

MARKET_DIR = DATA_ROOT / "market"
MARKET_DIR.mkdir(parents=True, exist_ok=True)


OUTPUT_FILE = DATA_ROOT / "market" / "ohlcv_combined.json"

# --- Correlation universe support (optional) ---------------------------------
CORRELATION_UNIVERSE_FILE = MARKET_DIR / "correlation_universe.json"

# If price_fetcher uses CoinGecko IDs (your current keys: bitcoin/ethereum/solana),
# allow config with tickers like BTCUSDT/ETHUSDT by mapping to CoinGecko IDs.
TICKER_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "LINK": "chainlink",
}

def _normalize_symbol_to_cg_id(sym: str) -> str | None:
    """
    Accept:
      - "bitcoin" (already cg id)
      - "BTC", "ETH"
      - "BTCUSDT" / "ETHUSDT" (we keep base ticker)
      - "BTC/USDT" (base ticker)
    Return CoinGecko id if we can, else None.
    """
    if not isinstance(sym, str) or not sym.strip():
        return None
    x = sym.strip()

    # already looks like a coingecko id (contains '-' or all lowercase word)
    if re.fullmatch(r"[a-z0-9\-]+", x):
        # ex: bitcoin, avalanche-2, matic-network
        return x

    # convert "BTC/USDT" -> "BTC", "BTCUSDT" -> "BTC"
    x = x.upper()
    if "/" in x:
        x = x.split("/")[0]
    if x.endswith("USDT"):
        x = x[:-4]

    return TICKER_TO_COINGECKO_ID.get(x)

def load_correlation_universe_ids() -> list[str]:
    """
    Read data/market/correlation_universe.json and return CoinGecko IDs.
    """
    try:
        if not CORRELATION_UNIVERSE_FILE.exists():
            return []
        raw = json.loads(CORRELATION_UNIVERSE_FILE.read_text(encoding="utf-8"))
        syms = raw.get("symbols") if isinstance(raw, dict) else None
        if not isinstance(syms, list):
            return []
        out = []
        for sym in syms:
            cid = _normalize_symbol_to_cg_id(sym)
            if cid:
                out.append(cid)
        # unique, preserve order
        seen = set()
        uniq = []
        for cid in out:
            if cid not in seen:
                seen.add(cid)
                uniq.append(cid)
        return uniq
    except Exception as e:
        logger.warning("[price_fetcher] Failed to load correlation universe: %s", e)
        return []

SELECTED_TOKENS_FILE = DATA_ROOT / "selected_tokens.json"
DYNAMIC_SELECTED_TOKENS_FILE = DATA_ROOT / "trading" / "selected_tokens.dynamic.json"

# RC2 Market Momentum Entry Quality Foundation V1.
# 15m candles over seven days:
# 4 candles/hour * 24h * 7d = 672.
MARKET_MOMENTUM_OHLCV_INTERVAL = "15m"
MARKET_MOMENTUM_OHLCV_LIMIT = 672

# Liste de base (Option 3)
BASE_TOKENS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "AVAXUSDT",
    "MATICUSDT",
]

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
MEXC_KLINES_URL = "https://api.mexc.com/api/v3/klines"

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------

def load_selected_tokens() -> List[str]:
    """
    Charge selected_tokens.json et renvoie une liste de symboles au format XXXUSDT.

    Formats supportés :
    - { "tokens": ["BTC", "ETHUSDT", ...] }
    - ["BTC", "ETHUSDT", ...]
    """
    tokens: List[str] = []

    if not SELECTED_TOKENS_FILE.exists():
        logger.warning(
            "[price_fetcher] selected_tokens.json introuvable (%s), on utilisera uniquement la liste de base.",
            SELECTED_TOKENS_FILE,
        )
        return []

    try:
        with SELECTED_TOKENS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.exception(
            "[price_fetcher] Erreur de lecture de %s : %s", SELECTED_TOKENS_FILE, e
        )
        return []

    # Format dict { "tokens": [...] }
    if isinstance(data, dict) and "tokens" in data:
        raw_tokens = data.get("tokens") or []
        if isinstance(raw_tokens, list):
            tokens = [str(t) for t in raw_tokens]
    # Format liste simple
    elif isinstance(data, list):
        tokens = [str(t) for t in data]
    else:
        logger.warning(
            "[price_fetcher] Format inattendu pour selected_tokens.json (type racine: %s)",
            type(data),
        )

    # Normalisation en XXXUSDT (si pas déjà suffixé)
    normalized: List[str] = []
    for t in tokens:
        t = t.strip().upper()
        if not t:
            continue
        if not t.endswith("USDT"):
            t = t + "USDT"
        normalized.append(t)

    # On évite les doublons
    normalized = sorted(set(normalized))

    logger.info(
        "[price_fetcher] Tokens chargés depuis selected_tokens.json : %s", normalized
    )
    return normalized


def load_dynamic_market_movers() -> List[str]:
    """
    Load current market_momentum tokens selected by token_selector_v2_2.

    This enriches the OHLCV quality universe without removing the existing
    legacy selected-token universe during RC2.
    """
    if not DYNAMIC_SELECTED_TOKENS_FILE.exists():
        return []

    try:
        raw = json.loads(
            DYNAMIC_SELECTED_TOKENS_FILE.read_text(encoding="utf-8")
        )
    except Exception as exc:
        logger.warning(
            "[price_fetcher] dynamic selected tokens unreadable: %s",
            exc,
        )
        return []

    items = raw.get("items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return []

    out: List[str] = []

    for row in items:
        if not isinstance(row, dict):
            continue

        if not bool(row.get("market_momentum")):
            continue

        token = str(row.get("token") or "").strip().upper()
        pair = str(
            row.get("pair")
            or (f"{token}USDT" if token else "")
        ).strip().upper()

        if pair and pair.endswith("USDT"):
            out.append(pair)

    return sorted(set(out))


def merge_token_lists() -> List[str]:
    """
    RC2 trading OHLCV universe.

    Preserve the existing selected-token universe and enrich it with current
    dynamic market movers so that entry-quality scoring can evaluate the
    actual assets proposed by discovery.
    """
    selected = load_selected_tokens()
    dynamic_movers = load_dynamic_market_movers()

    merged = sorted(set(selected + dynamic_movers))

    logger.info(
        "[price_fetcher] OHLCV universe selected=%s dynamic_movers=%s merged=%s",
        selected,
        dynamic_movers,
        merged,
    )

    return merged


def fetch_binance_klines(symbol: str, interval: str = MARKET_MOMENTUM_OHLCV_INTERVAL, limit: int = MARKET_MOMENTUM_OHLCV_LIMIT) -> List[List[Any]]:
    """
    Récupère les klines Binance pour un symbole donné.
    Retour brut : liste de listes.
    """
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            logger.info(
                "[price_fetcher] Binance OK pour %s (%d bougies)", symbol, len(data)
            )
            return data
        else:
            logger.warning(
                "[price_fetcher] Réponse Binance inattendue pour %s (type: %s)",
                symbol,
                type(data),
            )
            return []
    except Exception as e:
        logger.warning("[price_fetcher] Binance KO pour %s : %s", symbol, e)
        return []


def fetch_mexc_klines(symbol: str, interval: str = MARKET_MOMENTUM_OHLCV_INTERVAL, limit: int = MARKET_MOMENTUM_OHLCV_LIMIT) -> List[List[Any]]:
    """
    Récupère les klines MEXC pour un symbole donné.
    Retour brut : liste de listes.
    """
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(MEXC_KLINES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            logger.info(
                "[price_fetcher] MEXC OK pour %s (%d bougies)", symbol, len(data)
            )
            return data
        else:
            logger.warning(
                "[price_fetcher] Réponse MEXC inattendue pour %s (type: %s)",
                symbol,
                type(data),
            )
            return []
    except Exception as e:
        logger.warning("[price_fetcher] MEXC KO pour %s : %s", symbol, e)
        return []


def klines_to_candles(
    klines: List[List[Any]],
    source: str,
) -> List[Dict[str, Any]]:
    """
    Convertit les klines bruts (Binance/MEXC) en liste de dicts standardisés.

    Kline typique :
    [
      0 openTime,
      1 open,
      2 high,
      3 low,
      4 close,
      5 volume,
      6 closeTime,
      ...
    ]
    """
    candles: List[Dict[str, Any]] = []
    for row in klines:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        try:
            ts = int(row[0])
            o = float(row[1])
            h = float(row[2])
            l = float(row[3])
            c = float(row[4])
            v = float(row[5])
        except Exception:
            continue

        candles.append(
            {
                "ts": ts,          # timestamp en ms (openTime)
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
                "source": source,  # "binance" ou "mexc"
            }
        )
    return candles


def _latest_candle_age_seconds(
    candles: List[Dict[str, Any]],
) -> Optional[float]:
    """
    Age of the latest standardized candle.

    Dynamic market-momentum OHLCV uses 15m bars. A stale last candle
    means the market data cannot be used for current entry-quality
    scoring, even if the provider returned HTTP 200.
    """
    if not candles:
        return None

    latest_ts = None

    for candle in candles:
        if not isinstance(candle, dict):
            continue

        raw = (
            candle.get("ts")
            if candle.get("ts") is not None
            else candle.get("timestamp")
        )

        if raw is None:
            continue

        try:
            value = float(raw)
        except Exception:
            continue

        # Binance/MEXC timestamps are normally milliseconds.
        if value > 10_000_000_000:
            value /= 1000.0

        if latest_ts is None or value > latest_ts:
            latest_ts = value

    if latest_ts is None:
        return None

    return max(
        0.0,
        datetime.now(timezone.utc).timestamp()
        - latest_ts,
    )


MARKET_MOMENTUM_MAX_OHLCV_AGE_SECONDS = int(
    os.getenv(
        "NSC_MARKET_MOMENTUM_MAX_OHLCV_AGE_SECONDS",
        str(45 * 60),
    )
)


def build_asset_entry(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Construit une entrée 'asset' pour un symbole donné, en fusionnant Binance + MEXC.

    Stratégie simple :
    - Si Binance a des données : on prend Binance.
    - Sinon, on prend MEXC.
    - Si aucun des deux n'a de données : on renvoie None.
    """
    binance_raw = fetch_binance_klines(symbol)
    mexc_raw = fetch_mexc_klines(symbol)

    candles: List[Dict[str, Any]] = []
    source_used = None

    if binance_raw:
        candles = klines_to_candles(binance_raw, "binance")
        source_used = "binance"
    elif mexc_raw:
        candles = klines_to_candles(mexc_raw, "mexc")
        source_used = "mexc"
    else:
        logger.warning(
            "[price_fetcher] Aucun prix disponible pour %s sur Binance/MEXC", symbol
        )
        return None

    if not candles:
        logger.warning(
            "[price_fetcher] Aucune bougie exploitable pour %s (après parsing)", symbol
        )
        return None

    latest_age_seconds = _latest_candle_age_seconds(
        candles
    )

    if (
        latest_age_seconds is None
        or latest_age_seconds
        > MARKET_MOMENTUM_MAX_OHLCV_AGE_SECONDS
    ):
        logger.warning(
            "[price_fetcher] STALE OHLCV rejected for %s "
            "source=%s age_seconds=%s max=%s",
            symbol,
            source_used,
            latest_age_seconds,
            MARKET_MOMENTUM_MAX_OHLCV_AGE_SECONDS,
        )
        return None

    logger.info(
        "[price_fetcher] Asset %s construit (%d bougies, source=%s)",
        symbol,
        len(candles),
        source_used,
    )

    return {
        "symbol": symbol,
        "env": NSC_ENV,
        "source": source_used,
        "ohlcv_age_seconds": round(
            latest_age_seconds,
            3,
        ),
        "ohlcv_fresh": True,
        "candles": candles,
    }


def run_price_fetcher() -> Dict[str, Any]:
    """
    Pipeline principal :
    - charge tokens dynamiques uniquement
    - fetch Binance+MEXC
    - construit la liste assets[]
    - écrit ohlcv_combined.json
    """
    logger.info(
        "[price_fetcher] Démarrage – ENV=%s DATA_ROOT=%s", NSC_ENV, DATA_ROOT
    )

    tokens = merge_token_lists()
    assets: List[Dict[str, Any]] = []

    for symbol in tokens:
        asset_entry = build_asset_entry(symbol)
        if asset_entry is not None:
            assets.append(asset_entry)

    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": NSC_ENV,
        "assets": assets,
    }

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(
            "[price_fetcher] Fichier sauvegardé : %s (assets=%d)",
            OUTPUT_FILE,
            len(assets),
        )
    except Exception as e:
        logger.exception(
            "[price_fetcher] Erreur lors de l'écriture de %s : %s", OUTPUT_FILE, e
        )
        raise

    return result


if __name__ == "__main__":
    data = run_price_fetcher()
    print(
        f"[price_fetcher] Done – assets={len(data.get('assets', []))} "
        f"output={OUTPUT_FILE}"
    )
