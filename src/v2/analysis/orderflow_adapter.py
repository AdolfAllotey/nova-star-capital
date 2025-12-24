from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Chemins & constantes
# ---------------------------------------------------------------------------

DATA_DIR = Path(get_data_dir()).resolve()
ROOT_DIR = DATA_DIR.parent

MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"

ORDERBOOK_SNAPSHOTS_PATH = MARKET_DIR / "orderbook_snapshots.json"
ORDERFLOW_ADAPTER_PATH = ANALYSIS_DIR / "orderflow_adapter.json"

TOP_LEVELS = 5
SPREAD_HARD_BLOCK_PCT = 0.6  # % → blocage si spread > 0.6
SPREAD_CAUTION_PCT = 0.4     # % → mode prudence

# Seuils spoofing (heuristique simple)
SPOOF_CAUTION_THRESHOLD = 0.5
SPOOF_BLOCK_THRESHOLD = 0.7


@dataclass
class OrderbookSide:
    prices: List[float]
    sizes: List[float]


@dataclass
class OrderbookSnapshot:
    symbol: str
    bids: OrderbookSide
    asks: OrderbookSide
    timestamp: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _parse_side(levels: Any, is_bid: bool) -> OrderbookSide:
    """
    Prend une liste de niveaux [[price, size], ...] et renvoie un OrderbookSide.
    On garde TOP_LEVELS max, on nettoie les NaN et <= 0.
    """
    prices: List[float] = []
    sizes: List[float] = []

    if isinstance(levels, list):
        for lvl in levels[:TOP_LEVELS]:
            if not isinstance(lvl, (list, tuple)) or len(lvl) < 2:
                continue
            p = _safe_float(lvl[0])
            s = _safe_float(lvl[1])
            if p <= 0 or s <= 0:
                continue
            prices.append(p)
            sizes.append(s)

    # Tri cohérent au cas où
    if prices:
        combined = list(zip(prices, sizes))
        # bids: prix décroissants, asks: prix croissants
        reverse = is_bid
        combined.sort(key=lambda x: x[0], reverse=reverse)
        prices, sizes = zip(*combined)
        prices = list(prices)
        sizes = list(sizes)

    return OrderbookSide(prices=prices, sizes=sizes)


def _parse_orderbook_snapshot(symbol: str, raw: Dict[str, Any]) -> Optional[OrderbookSnapshot]:
    """
    Parse un snapshot de carnet pour un symbole donné.

    Format attendu (flexible) :
    {
      "bids": [[prix, taille], ...],
      "asks": [[prix, taille], ...],
      "timestamp": "..."
    }
    """
    if not isinstance(raw, dict):
        return None

    bids_raw = raw.get("bids", [])
    asks_raw = raw.get("asks", [])

    bids = _parse_side(bids_raw, is_bid=True)
    asks = _parse_side(asks_raw, is_bid=False)

    if not bids.prices or not asks.prices:
        # Carnet inutilisable
        return None

    ts = raw.get("timestamp")
    if ts is not None:
        ts = str(ts)

    return OrderbookSnapshot(symbol=symbol, bids=bids, asks=asks, timestamp=ts)


def load_orderbook_snapshots() -> List[OrderbookSnapshot]:
    """
    Charge les snapshots de carnet depuis ORDERBOOK_SNAPSHOTS_PATH.

    On gère deux formats possibles :
    1) dict { "BTCUSDT": {...}, "ETHUSDT": {...}, ... }
    2) list [{"symbol": "...", "bids": [...], "asks": [...]}, ...]
    """
    raw = load_json_file(ORDERBOOK_SNAPSHOTS_PATH, default=None)

    snapshots: List[OrderbookSnapshot] = []

    if raw is None:
        logger.warning(
            "[orderflow_adapter] Aucun fichier de carnet trouvé (%s).",
            ORDERBOOK_SNAPSHOTS_PATH,
        )
        return []

    # Format dict par symbole
    if isinstance(raw, dict) and not isinstance(raw, list):
        for sym, ob in raw.items():
            snap = _parse_orderbook_snapshot(str(sym), ob)
            if snap is not None:
                snapshots.append(snap)

    # Format liste
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol") or item.get("base") or item.get("pair")
            if not sym:
                continue
            snap = _parse_orderbook_snapshot(str(sym), item)
            if snap is not None:
                snapshots.append(snap)

    else:
        logger.warning(
            "[orderflow_adapter] Format inattendu pour %s (type=%s).",
            ORDERBOOK_SNAPSHOTS_PATH,
            type(raw),
        )

    logger.info(
        "[orderflow_adapter] %d snapshots de carnet chargés depuis %s",
        len(snapshots),
        ORDERBOOK_SNAPSHOTS_PATH,
    )
    return snapshots


# ---------------------------------------------------------------------------
# Calcul des métriques orderflow
# ---------------------------------------------------------------------------

def compute_basic_metrics(snapshot: OrderbookSnapshot) -> Dict[str, float]:
    """
    Calcule :
      - best_bid, best_ask
      - mid_price, spread_abs, spread_pct
      - bid_volume_top, ask_volume_top
      - imbalance (entre -1 et 1)
    """
    best_bid = snapshot.bids.prices[0]
    best_ask = snapshot.asks.prices[0]

    mid = (best_bid + best_ask) / 2.0 if (best_bid > 0 and best_ask > 0) else 0.0
    spread_abs = max(0.0, best_ask - best_bid)
    spread_pct = (spread_abs / mid * 100.0) if mid > 0 else 0.0

    bid_vol = sum(snapshot.bids.sizes)
    ask_vol = sum(snapshot.asks.sizes)

    denom = bid_vol + ask_vol
    if denom > 0:
        imbalance = (bid_vol - ask_vol) / denom  # [-1, 1]
    else:
        imbalance = 0.0

    return {
        "best_bid": float(best_bid),
        "best_ask": float(best_ask),
        "mid_price": float(mid),
        "spread_abs": float(spread_abs),
        "spread_pct": float(spread_pct),
        "bid_volume_top": float(bid_vol),
        "ask_volume_top": float(ask_vol),
        "imbalance": float(imbalance),
    }


def compute_spoof_score(snapshot: OrderbookSnapshot, metrics: Dict[str, float]) -> float:
    """
    Heuristique simple de probabilité de spoofing (0 → 1).

    Idée :
      - si un seul niveau absorbe la majorité du volume d'un côté
      - ET fort déséquilibre (imbalance) en faveur de ce côté
      - ET spread relativement serré

    Ce n'est pas du tout parfait, mais suffisant pour une première garde-fou.
    """
    bid_sizes = snapshot.bids.sizes
    ask_sizes = snapshot.asks.sizes

    bid_vol = metrics.get("bid_volume_top", 0.0)
    ask_vol = metrics.get("ask_volume_top", 0.0)
    spread_pct = metrics.get("spread_pct", 0.0)
    imbalance = metrics.get("imbalance", 0.0)

    total_vol = bid_vol + ask_vol
    if total_vol <= 0:
        return 0.0

    max_bid = max(bid_sizes) if bid_sizes else 0.0
    max_ask = max(ask_sizes) if ask_sizes else 0.0
    max_side = max(max_bid, max_ask)

    concentration = max_side / total_vol if total_vol > 0 else 0.0
    imbalance_abs = abs(imbalance)

    spoof_raw = 0.0

    if concentration > 0.4:
        spoof_raw += (concentration - 0.4) * 1.5

    if imbalance_abs > 0.4:
        spoof_raw += (imbalance_abs - 0.4) * 1.0

    if spread_pct < 0.5:
        spoof_raw += 0.2

    spoof_score = max(0.0, min(1.0, spoof_raw))
    return float(spoof_score)


def classify_orderflow_risk(spread_pct: float, spoof_score: float) -> Tuple[str, str]:
    """
    Retourne (risk_flag, kill_switch_mode_hint)

    risk_flag ∈ {"ok", "caution", "block"}
    kill_switch_mode_hint ∈ {"none", "soft_block", "hard_block"}
    """
    if spread_pct > SPREAD_HARD_BLOCK_PCT or spoof_score >= SPOOF_BLOCK_THRESHOLD:
        return "block", "hard_block"

    if spread_pct > SPREAD_CAUTION_PCT or spoof_score >= SPOOF_CAUTION_THRESHOLD:
        return "caution", "soft_block"

    return "ok", "none"


# ---------------------------------------------------------------------------
# Moteur principal
# ---------------------------------------------------------------------------

def compute_orderflow_adapter() -> Dict[str, Any]:
    """
    Analyse le carnet (top 5) pour chaque symbole, calcule :
      - spread_pct
      - order imbalance
      - spoof_score (heuristique)
      - risk_flag et kill_switch_mode_hint

    Sauvegarde le tout dans orderflow_adapter.json.
    """
    logger.info(
        "[orderflow_adapter] ROOT_DIR=%s, DATA_DIR=%s",
        ROOT_DIR,
        DATA_DIR,
    )

    snapshots = load_orderbook_snapshots()
    results: List[Dict[str, Any]] = []

    nb_block = 0
    nb_caution = 0

    for snap in snapshots:
        metrics = compute_basic_metrics(snap)
        spoof_score = compute_spoof_score(snap, metrics)
        spread_pct = metrics.get("spread_pct", 0.0)

        risk_flag, ks_hint = classify_orderflow_risk(spread_pct, spoof_score)

        if risk_flag == "block":
            nb_block += 1
        elif risk_flag == "caution":
            nb_caution += 1

        entry: Dict[str, Any] = {
            "symbol": snap.symbol,
            "timestamp": snap.timestamp,
            "metrics": metrics,
            "spoof_score": float(spoof_score),
            "risk_flag": risk_flag,
            "kill_switch_hint": ks_hint,
        }

        if ks_hint != "none":
            entry["local_kill_switch"] = {
                "scope": f"symbol:{snap.symbol}",
                "mode": ks_hint,
                "source": "orderflow_adapter",
                "reason": (
                    f"orderflow_risk={risk_flag}, "
                    f"spread={spread_pct:.3f}%, spoof_score={spoof_score:.2f}"
                ),
            }

        results.append(entry)

    if nb_block > 0:
        global_flag = "block"
    elif nb_caution > 0:
        global_flag = "caution"
    else:
        global_flag = "ok"

    now_ts = datetime.now(timezone.utc).isoformat()

    payload: Dict[str, Any] = {
        "as_of": now_ts,
        "global_flag": global_flag,
        "stats": {
            "nb_symbols": len(results),
            "nb_block": nb_block,
            "nb_caution": nb_caution,
        },
        "symbols": results,
    }

    locals_vetos: List[Dict[str, Any]] = []
    for r in results:
        local = r.get("local_kill_switch")
        if local:
            locals_vetos.append(local)

    payload["locals"] = locals_vetos

    save_json_file(ORDERFLOW_ADAPTER_PATH, payload)
    logger.info(
        "[orderflow_adapter] orderflow_adapter.json sauvegardé (%s) – symbols=%d, global_flag=%s",
        ORDERFLOW_ADAPTER_PATH,
        len(results),
        global_flag,
    )

    return payload


# ---------------------------------------------------------------------------
# Entrée CLI
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        compute_orderflow_adapter()
    except Exception:
        logger.exception("[orderflow_adapter] Erreur lors du calcul orderflow")
        raise


if __name__ == "__main__":
    main()
