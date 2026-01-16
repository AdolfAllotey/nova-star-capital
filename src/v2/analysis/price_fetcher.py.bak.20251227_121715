import os
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
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/opt/nsc/app/data")).resolve()

MARKET_DIR = DATA_ROOT / "market"
MARKET_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = MARKET_DIR / "ohlcv_combined.json"
SELECTED_TOKENS_FILE = DATA_ROOT / "selected_tokens.json"

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


def merge_token_lists() -> List[str]:
    """
    Implémente l'Option 3 : fusion selected_tokens.json + BASE_TOKENS.
    """
    selected = load_selected_tokens()
    merged = sorted(set(selected + BASE_TOKENS))
    logger.info(
        "[price_fetcher] Liste finale de tokens (Option 3 = selected + base) : %s",
        merged,
    )
    return merged


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> List[List[Any]]:
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


def fetch_mexc_klines(symbol: str, interval: str = "1h", limit: int = 200) -> List[List[Any]]:
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
        "candles": candles,
    }


def run_price_fetcher() -> Dict[str, Any]:
    """
    Pipeline principal :
    - fusion tokens (selected_tokens + base)
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
