"""
Microstructure Ultra Engine PRO – NSC

Objectif :
- Lire les snapshots de carnet d’ordres et de trades récents.
- Calculer des métriques microstructure avancées :
  - spread en bps
  - profondeur top5 bid/ask
  - order imbalance
  - trade imbalance
  - volatilité courte (1m / 5m si possible)
  - side de pression (buy / sell / neutral)
- Produire un score & un régime microstructure :
  - normal / fast_market / illiquid / buy_pressure / sell_pressure / unknown
- Sauvegarder un JSON d’analyse pour le reste du système.
- Publier un event sur le Message Bus : type = "microstructure.ultra.state".
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers locaux (pour éviter toute dépendance fragile à file_utils)
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Retourne le DATA_DIR NSC.

    - Utilise la variable d'env NSC_DATA_DIR si présente.
    - Sinon, fallback sur 'data' (chemin relatif au cwd).
    """
    base = os.environ.get("NSC_DATA_DIR", "data")
    data_dir = Path(base).resolve()
    return data_dir


def load_json_default(path: Path, default: Any) -> Any:
    """
    Charge un fichier JSON, ou retourne 'default' si le fichier n'existe pas
    ou est invalide. Loggue en warning en cas de problème.
    """
    try:
        if not path.exists():
            logger.warning(
                "[microstructure_ultra_engine_pro] JSON file not found: %s → returning default",
                path,
            )
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[microstructure_ultra_engine_pro] Error reading %s: %s → returning default",
            path,
            exc,
        )
        return default


def save_json(path: Path, data: Any) -> None:
    """
    Sauvegarde un dictionnaire en JSON (indenté).
    Crée les dossiers parents si nécessaire.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        logger.info("Saved JSON file: %s", path)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[microstructure_ultra_engine_pro] Impossible de sauvegarder %s: %s",
            path,
            exc,
        )


# ---------------------------------------------------------------------------
# Modèle de sortie
# ---------------------------------------------------------------------------

@dataclass
class MicrostructureMetrics:
    spread_bps: Optional[float] = None
    mid_price: Optional[float] = None
    top5_bid_volume: float = 0.0
    top5_ask_volume: float = 0.0
    order_imbalance: Optional[float] = None
    trade_imbalance_1m: Optional[float] = None
    volatility_1m: Optional[float] = None
    volatility_5m: Optional[float] = None
    pressure_side: str = "neutral"  # "buy" / "sell" / "neutral"


@dataclass
class MicrostructureState:
    timestamp: str
    env: str
    symbol: str
    regime: str                # normal / fast_market / illiquid / buy_pressure / sell_pressure / unknown
    global_flag: str           # ok / caution / stress
    score: float
    reasons: List[str]
    metrics: MicrostructureMetrics


# ---------------------------------------------------------------------------
# Parsing des inputs
# ---------------------------------------------------------------------------

def _parse_orderbook(orderbook: Dict[str, Any]) -> Tuple[MicrostructureMetrics, List[str]]:
    """
    Extrait les métriques de carnet :
    - best bid / ask
    - spread en bps
    - profondeur top5
    - order imbalance
    """
    reasons: List[str] = []
    m = MicrostructureMetrics()

    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []

    def _extract_levels(levels: List[Any]) -> List[Tuple[float, float]]:
        parsed: List[Tuple[float, float]] = []
        for lvl in levels:
            price: Optional[float] = None
            size: Optional[float] = None

            if isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                price = float(lvl[0])
                size = float(lvl[1])
            elif isinstance(lvl, dict):
                if "price" in lvl:
                    price = float(lvl["price"])
                if "size" in lvl:
                    size = float(lvl["size"])
                elif "quantity" in lvl:
                    size = float(lvl["quantity"])

            if price is not None and size is not None:
                parsed.append((price, size))

        return parsed

    bids_parsed = _extract_levels(bids)
    asks_parsed = _extract_levels(asks)

    if not bids_parsed or not asks_parsed:
        reasons.append("Carnet incomplet (pas assez de bids/asks).")
        return m, reasons

    # Best bid / ask
    best_bid_price, _ = max(bids_parsed, key=lambda x: x[0])
    best_ask_price, _ = min(asks_parsed, key=lambda x: x[0])

    mid = (best_bid_price + best_ask_price) / 2.0
    m.mid_price = mid

    if mid > 0:
        m.spread_bps = (best_ask_price - best_bid_price) / mid * 10_000.0
    else:
        m.spread_bps = None
        reasons.append("Mid price <= 0, spread_bps non calculable.")

    # Profondeur top5
    m.top5_bid_volume = sum(size for _, size in bids_parsed[:5])
    m.top5_ask_volume = sum(size for _, size in asks_parsed[:5])

    total_depth = m.top5_bid_volume + m.top5_ask_volume
    if total_depth > 0:
        m.order_imbalance = (m.top5_bid_volume - m.top5_ask_volume) / total_depth
    else:
        m.order_imbalance = None
        reasons.append("Profondeur totale nulle, order_imbalance non calculable.")

    return m, reasons


def _parse_trades(trades: List[Dict[str, Any]]) -> Tuple[float, Optional[float], Optional[float], List[str]]:
    """
    Analyse des trades récents (on suppose déjà filtré sur 1-5 minutes par upstream) :

    Retourne :
    - trade_imbalance_1m
    - volatility_1m
    - volatility_5m (placeholder si pas assez d'info)
    """
    reasons: List[str] = []

    if not trades:
        return 0.0, None, None, ["Aucun trade récent disponible."]

    # On tolère plusieurs formats : dict avec side/price/size
    buys_size = 0.0
    sells_size = 0.0
    prices: List[float] = []

    for t in trades:
        side = str(t.get("side", "")).lower()
        size_raw = t.get("size") or t.get("qty") or t.get("quantity") or 0.0
        price_raw = t.get("price") or t.get("p") or None

        try:
            size = float(size_raw)
        except Exception:  # noqa: BLE001
            size = 0.0

        try:
            price = float(price_raw) if price_raw is not None else None
        except Exception:  # noqa: BLE001
            price = None

        if price is not None:
            prices.append(price)

        if side in ("buy", "b", "bid"):
            buys_size += max(size, 0.0)
        elif side in ("sell", "s", "ask"):
            sells_size += max(size, 0.0)

    total_sz = buys_size + sells_size
    if total_sz > 0:
        trade_imbalance = (buys_size - sells_size) / total_sz
    else:
        trade_imbalance = 0.0
        reasons.append("Taille totale des trades nulle, trade_imbalance fixé à 0.")

    # Volatilité simple : écart-type normalisé sur les prix
    volatility_1m: Optional[float] = None
    volatility_5m: Optional[float] = None

    if len(prices) >= 2:
        avg = sum(prices) / len(prices)
        if avg > 0:
            var = sum((p - avg) ** 2 for p in prices) / (len(prices) - 1)
            volatility_1m = (var ** 0.5) / avg
            # Pour l’instant, on n’a qu’un horizon → on copie sur 5m
            volatility_5m = volatility_1m
        else:
            reasons.append("Prix moyen <= 0, volatilité non calculable.")
    else:
        reasons.append("Pas assez de trades pour calculer une volatilité robuste.")

    return trade_imbalance, volatility_1m, volatility_5m, reasons


# ---------------------------------------------------------------------------
# Scoring & régime
# ---------------------------------------------------------------------------

def _derive_state(
    ts: str,
    env: str,
    symbol: str,
    metrics: MicrostructureMetrics,
    extra_reasons: Optional[List[str]] = None,
) -> MicrostructureState:
    """
    Traduit les métriques en :
    - regime
    - global_flag
    - score
    - reasons
    """
    reasons: List[str] = list(extra_reasons or [])

    # Defaults si données manquantes
    if metrics.spread_bps is None or metrics.order_imbalance is None:
        regime = "unknown"
        global_flag = "caution"
        score = 50.0
        reasons.append(
            "Données microstructure incomplètes (spread ou order_imbalance manquants)."
        )
        return MicrostructureState(
            timestamp=ts,
            env=env,
            symbol=symbol,
            regime=regime,
            global_flag=global_flag,
            score=score,
            reasons=reasons,
            metrics=metrics,
        )

    spread = metrics.spread_bps
    depth = metrics.top5_bid_volume + metrics.top5_ask_volume
    oi = metrics.order_imbalance or 0.0
    ti = metrics.trade_imbalance_1m or 0.0
    vol = metrics.volatility_1m or 0.0

    # Détection side de pression
    if ti > 0.25 and oi > 0.25:
        metrics.pressure_side = "buy"
    elif ti < -0.25 and oi < -0.25:
        metrics.pressure_side = "sell"
    else:
        metrics.pressure_side = "neutral"

    # Logique de régime simple mais exploitable
    regime = "normal"
    global_flag = "ok"
    score = 65.0

    # 1) Cas illiquid / stressé
    if spread > 25 or depth < 1.0:
        regime = "illiquid"
        global_flag = "stress"
        score = 35.0
        reasons.append(
            f"Microstructure illiquide (spread={spread:.1f} bps, depth={depth:.3f})."
        )

    # 2) Cas fast market (forte vol + trade imbalance marqué)
    if vol > 0.02 and abs(ti) > 0.4:
        regime = "fast_market"
        global_flag = "stress"
        score = 40.0
        reasons.append(
            f"Fast market (vol={vol:.3%}, trade_imbalance={ti:.2f})."
        )

    # 3) Cas pression acheteuse / vendeuse
    if regime == "normal":
        if metrics.pressure_side == "buy":
            regime = "buy_pressure"
            global_flag = "ok"
            score = 70.0
            reasons.append(
                f"Pression acheteuse (order_imbalance={oi:.2f}, trade_imbalance={ti:.2f})."
            )
        elif metrics.pressure_side == "sell":
            regime = "sell_pressure"
            global_flag = "caution"
            score = 55.0
            reasons.append(
                f"Pression vendeuse (order_imbalance={oi:.2f}, trade_imbalance={ti:.2f})."
            )
        else:
            reasons.append(
                f"Microstructure normale (spread={spread:.1f} bps, depth={depth:.3f}, vol={vol:.3%})."
            )

    # 4) Sanity checks / bornes
    score = max(0.0, min(100.0, score))

    return MicrostructureState(
        timestamp=ts,
        env=env,
        symbol=symbol,
        regime=regime,
        global_flag=global_flag,
        score=score,
        reasons=reasons,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Entrée principale, appelée via :

        python -m src.v2.analysis.microstructure_ultra_engine_pro
    """
    import datetime as dt

    env = os.environ.get("NSC_ENV", "PREPROD")
    data_dir = get_data_dir()
    logger.info(
        "[microstructure_ultra_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    # Emplacement des inputs (on garde ça simple et robuste)
    orderbook_path = data_dir / "market" / "orderbook_snapshot.json"
    trades_path = data_dir / "market" / "recent_trades.json"

    # Emplacement de la sortie
    output_path = data_dir / "analysis" / "microstructure_ultra_engine_pro.json"

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Chargement des inputs
    orderbook_raw = load_json_default(orderbook_path, default={})
    trades_raw = load_json_default(trades_path, default=[])

    symbol = (
        orderbook_raw.get("symbol")
        or orderbook_raw.get("pair")
        or "global"
    )

    metrics, reasons_ob = _parse_orderbook(orderbook_raw)
    ti, vol1, vol5, reasons_trades = _parse_trades(trades_raw)

    metrics.trade_imbalance_1m = ti
    metrics.volatility_1m = vol1
    metrics.volatility_5m = vol5

    all_reasons = reasons_ob + reasons_trades

    state = _derive_state(
        ts=now_ts,
        env=env,
        symbol=symbol,
        metrics=metrics,
        extra_reasons=all_reasons,
    )

    # Sauvegarde du JSON d'analyse
    payload: Dict[str, Any] = {
        "timestamp": state.timestamp,
        "env": state.env,
        "symbol": state.symbol,
        "regime": state.regime,
        "global_flag": state.global_flag,
        "score": state.score,
        "reasons": state.reasons,
        "metrics": asdict(state.metrics),
    }

    save_json(output_path, payload)
    logger.info(
        "[microstructure_ultra_engine_pro] microstructure_ultra_engine_pro.json sauvegardé (regime=%s, global_flag=%s, score=%.2f)",
        state.regime,
        state.global_flag,
        state.score,
    )

    # ------------------------------------------------------------------ #
    # Publication sur le Message Bus PRO
    # ------------------------------------------------------------------ #
    severity = "info"
    if state.global_flag == "caution":
        severity = "warning"
    elif state.global_flag == "stress":
        severity = "critical"

    try:
        publish_event(
            "microstructure.ultra.state",
            "microstructure_ultra_engine_pro",
            severity,
            payload=payload,
        )
        logger.info(
            "[microstructure_ultra_engine_pro] Event microstructure.ultra.state publié (severity=%s, regime=%s, score=%.2f)",
            severity,
            state.regime,
            state.score,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[microstructure_ultra_engine_pro] Impossible de publier l'event microstructure.ultra.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
