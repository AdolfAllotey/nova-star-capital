from __future__ import annotations

import logging
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = get_logger(__name__)

DATA_DIR = Path(get_data_dir()).resolve()
ANALYSIS_DIR = DATA_DIR / "analysis"
BACKTEST_DIR = DATA_DIR / "backtests"

STRATEGY_FILE = BACKTEST_DIR / "strategy_perf_30d.json"
OUTPUT_FILE = ANALYSIS_DIR / "strategy_weights.json"


# ---------- Modèle de données ----------


@dataclass
class StrategyPerf:
    name: str
    pnl_30d: float          # PnL absolu sur 30j
    sharpe_30d: float       # Sharpe approx 30j
    winrate_30d: float      # 0–1
    max_dd_30d: float       # drawdown max (en % ou en unité normalisée)
    trades_30d: int         # nombre de trades
    meta_score: float       # meta-score interne (0–100) si dispo
    enabled: bool = True    # flag activable


@dataclass
class StrategyWeight:
    name: str
    raw_score: float
    weight: float
    normalized_weight: float
    reasons: List[str]


# ---------- Utilitaires de scoring ----------


def _normalize(values: List[float]) -> List[float]:
    """Normalise une liste de scores en [0, 1]. Si tout est égal → 1/len."""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if math.isclose(min_v, max_v):
        # Tous identiques → tout le monde égal
        n = len(values)
        return [1.0 / n] * n
    return [(v - min_v) / (max_v - min_v) for v in values]


def _safe_get(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_strategy_perf() -> Dict[str, StrategyPerf]:
    """
    Charge le fichier de perf 30j multi-stratégies.

    Format attendu (exemple) :
    {
      "momentum": {
        "pnl_30d": 120.5,
        "sharpe_30d": 1.4,
        "winrate_30d": 0.62,
        "max_dd_30d": -0.12,
        "trades_30d": 45,
        "meta_score": 72.0,
        "enabled": true
      },
      "whale": {...},
      "sniper": {...}
    }

    Si le fichier n'existe pas → fallback égalitaire.
    """
    raw = load_json_file(str(STRATEGY_FILE), default={})
    if not raw:
        logger.warning(
            "[strategy_selector] Aucun fichier de perf trouvé (%s), "
            "utilisation d'un fallback égalitaire.",
            STRATEGY_FILE,
        )
        # Fallback : 3 stratégies égalitaires, PnL neutre.
        return {
            "momentum": StrategyPerf(
                name="momentum",
                pnl_30d=0.0,
                sharpe_30d=0.0,
                winrate_30d=0.5,
                max_dd_30d=-0.1,
                trades_30d=0,
                meta_score=50.0,
                enabled=True,
            ),
            "whale": StrategyPerf(
                name="whale",
                pnl_30d=0.0,
                sharpe_30d=0.0,
                winrate_30d=0.5,
                max_dd_30d=-0.1,
                trades_30d=0,
                meta_score=50.0,
                enabled=True,
            ),
            "sniper": StrategyPerf(
                name="sniper",
                pnl_30d=0.0,
                sharpe_30d=0.0,
                winrate_30d=0.5,
                max_dd_30d=-0.1,
                trades_30d=0,
                meta_score=50.0,
                enabled=True,
            ),
        }

    result: Dict[str, StrategyPerf] = {}
    for name, d in raw.items():
        sp = StrategyPerf(
            name=name,
            pnl_30d=_safe_get(d, "pnl_30d", 0.0),
            sharpe_30d=_safe_get(d, "sharpe_30d", 0.0),
            winrate_30d=_safe_get(d, "winrate_30d", 0.5),
            max_dd_30d=_safe_get(d, "max_dd_30d", -0.1),
            trades_30d=int(d.get("trades_30d", 0) or 0),
            meta_score=_safe_get(d, "meta_score", 50.0),
            enabled=bool(d.get("enabled", True)),
        )
        result[name] = sp

    return result


def _compute_scores(perfs: Dict[str, StrategyPerf]) -> Dict[str, StrategyWeight]:
    """
    Calcule un score global par stratégie, puis des poids normalisés.

    Logique "hedge-fund light" :
      - PnL 30j : + (important)
      - Sharpe  : +
      - Winrate : +
      - Drawdown (max_dd_30d, négatif) : pénalisant
      - trades_30d trop faibles → légère pénalité (manque de robustesse)
      - meta_score : bonus
    """
    active = [p for p in perfs.values() if p.enabled]
    if not active:
        logger.warning("[strategy_selector] Aucune stratégie 'enabled' trouvée.")
        return {}

    # 1) Normalisation PnL, Sharpe, Winrate, Meta, et pénalité drawdown
    pnl_list = [p.pnl_30d for p in active]
    sharpe_list = [p.sharpe_30d for p in active]
    winrate_list = [p.winrate_30d for p in active]
    dd_list = [p.max_dd_30d for p in active]      # plus proche de 0 = mieux
    meta_list = [p.meta_score for p in active]

    pnl_norm = _normalize(pnl_list)
    sharpe_norm = _normalize(sharpe_list)
    winrate_norm = _normalize(winrate_list)
    # drawdown : moins négatif = mieux → on prend -dd pour normaliser
    dd_norm = _normalize([-dd for dd in dd_list])
    meta_norm = _normalize(meta_list)

    # 2) Pondération des composantes (peut être ajustée ensuite)
    # Idée : 30% PnL, 25% Sharpe, 15% Winrate, 15% Drawdown, 15% Meta
    alpha_pnl = 0.30
    alpha_sharpe = 0.25
    alpha_winrate = 0.15
    alpha_dd = 0.15
    alpha_meta = 0.15

    weights: Dict[str, StrategyWeight] = {}

    for idx, p in enumerate(active):
        score = (
            alpha_pnl * pnl_norm[idx]
            + alpha_sharpe * sharpe_norm[idx]
            + alpha_winrate * winrate_norm[idx]
            + alpha_dd * dd_norm[idx]
            + alpha_meta * meta_norm[idx]
        )

        reasons = [
            f"PnL_30d_norm={pnl_norm[idx]:.2f}",
            f"Sharpe_30d_norm={sharpe_norm[idx]:.2f}",
            f"Winrate_30d_norm={winrate_norm[idx]:.2f}",
            f"Drawdown_norm={dd_norm[idx]:.2f}",
            f"Meta_norm={meta_norm[idx]:.2f}",
        ]

        # Légère pénalité si très peu de trades (ex: < 10)
        if p.trades_30d < 10:
            score *= 0.9
            reasons.append("Pénalité faible nombre de trades (<10)")

        weights[p.name] = StrategyWeight(
            name=p.name,
            raw_score=score,
            weight=score,  # normalisation ensuite
            normalized_weight=0.0,
            reasons=reasons,
        )

    # 3) Normalisation pour obtenir des poids qui somme à 1
    total = sum(w.weight for w in weights.values())
    if total <= 0:
        # Si tout est 0 → égalitaire
        n = len(weights)
        for w in weights.values():
            w.normalized_weight = 1.0 / n
            w.reasons.append("Fallback égalitaire (scores tous nuls).")
    else:
        for w in weights.values():
            w.normalized_weight = w.weight / total

    return weights


def compute_strategy_weights() -> Dict[str, Any]:
    """
    Fonction principale :
      - charge la perf 30j multi-stratégies
      - calcule les scores + poids
      - sauvegarde dans strategy_weights.json

    Format de sortie :

    {
      "summary": {
        "nb_strategies": 3,
        "total_weight": 1.0,
        "best_strategy": "momentum"
      },
      "strategies": [
        {
          "name": "momentum",
          "raw_score": 0.83,
          "weight": 0.83,
          "normalized_weight": 0.52,
          "reasons": [...]
        },
        ...
      ]
    }
    """
    perfs = _load_strategy_perf()
    weights = _compute_scores(perfs)

    if not weights:
        payload = {
            "summary": {
                "nb_strategies": 0,
                "total_weight": 0.0,
                "best_strategy": None,
            },
            "strategies": [],
        }
        save_json_file(str(OUTPUT_FILE), payload)
        logger.info(
            "[strategy_selector] Aucun poids calculé, fichier vide sauvegardé (%s).",
            OUTPUT_FILE,
        )
        return payload

    strategies_list = [asdict(w) for w in weights.values()]
    total_weight = sum(w["normalized_weight"] for w in strategies_list)
    best_strategy = max(
        strategies_list, key=lambda d: d["normalized_weight"]
    )["name"]

    payload = {
        "summary": {
            "nb_strategies": len(strategies_list),
            "total_weight": total_weight,
            "best_strategy": best_strategy,
        },
        "strategies": strategies_list,
    }

    save_json_file(str(OUTPUT_FILE), payload)
    logger.info(
        "[strategy_selector] strategy_weights calculés et sauvegardés (%s): nb_strategies=%d, best=%s",
        OUTPUT_FILE,
        len(strategies_list),
        best_strategy,
    )
    return payload


def main() -> None:
    compute_strategy_weights()


if __name__ == "__main__":
    main()
