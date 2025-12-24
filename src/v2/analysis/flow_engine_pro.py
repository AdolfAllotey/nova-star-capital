"""
flow_engine_pro.py

Flow Engine Pro – synthétise un score de "flow" par asset en combinant :
- Momentum Engine 4.0
- Liquidity Engine Pro
- Story Engine Pro (narrative)
- Cross-Asset Engine Pro
- Filtre ML sur les signaux (signal_candidates_filtered)
- Contexte global (market_regime, emotional_regime)

Sortie : data/analysis/flow_engine_pro.json

Structure :
{
  "generated_at": "...",
  "stats": {
    "nb_assets": ...,
    "by_direction": {
      "inflow": ...,
      "neutral": ...,
      "outflow": ...
    },
    "nb_hard_veto": ...,
    "nb_soft_veto": ...,
    "global_flag": "ok|caution|danger"
  },
  "assets": [
    {
      "symbol": "bitcoin",
      "flow_score": 57.3,
      "direction": "neutral",
      "drivers": {
        "momentum_regime": "neutral",
        "liquidity_regime": "deep",
        "story_regime": "weak_story",
        "cross_asset_flag": "caution",
        "ml_decision": "watch"
      },
      "flags": {
        "hard_veto": false,
        "soft_veto": true
      },
      "reasons": [
        "Momentum neutre / mitigé",
        "Liquidité profonde",
        "Narrative fragile / non alignée",
        "Contexte cross-asset prudent (flag=caution)",
        "Signal ML en 'watch'"
      ]
    },
    ...
  ]
}
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
)
from src.v2.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_root_and_data_dir() -> Tuple[Path, Path]:
    """
    Calcule ROOT_DIR et DATA_DIR à partir des variables d'env, avec fallback
    robuste basé sur l'emplacement du fichier.
    """
    this_file = Path(__file__).resolve()
    # src/v2/analysis/flow_engine_pro.py → parents[3] = .../app
    default_root = this_file.parents[3]

    root_dir = Path(os.environ.get("NSC_ROOT_DIR", default_root))
    data_dir = Path(os.environ.get("NSC_DATA_DIR", root_dir / "data"))

    return root_dir, data_dir


def _index_by_key(items: List[Dict[str, Any]], key: str = "symbol") -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item in items or []:
        k = item.get(key)
        if isinstance(k, str):
            out[k] = item
    return out


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Dataclasses pour la sortie
# ---------------------------------------------------------------------------


@dataclass
class FlowAsset:
    symbol: str
    flow_score: float
    direction: str  # "inflow" | "neutral" | "outflow"
    drivers: Dict[str, Any]
    flags: Dict[str, Any]
    reasons: List[str]


@dataclass
class FlowOverview:
    generated_at: str
    stats: Dict[str, Any]
    assets: List[FlowAsset]


# ---------------------------------------------------------------------------
# Chargement des inputs
# ---------------------------------------------------------------------------


def _load_json(path: Path, default: Any) -> Any:
    return load_json_file(path, default=default)


def _load_momentum(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = data_dir / "analysis" / "momentum_engine_4_0.json"
    raw = _load_json(path, default={})
    assets = raw.get("assets") if isinstance(raw, dict) else None
    if not isinstance(assets, list):
        assets = []
    return _index_by_key(assets, key="symbol")


def _load_liquidity(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = data_dir / "analysis" / "liquidity_engine_pro.json"
    raw = _load_json(path, default={})
    assets = raw.get("assets") if isinstance(raw, dict) else None
    if not isinstance(assets, list):
        assets = []
    return _index_by_key(assets, key="symbol")


def _load_story(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = data_dir / "analysis" / "story_engine_pro.json"
    raw = _load_json(path, default={})
    assets = raw.get("assets") if isinstance(raw, dict) else None
    if not isinstance(assets, list):
        assets = []
    return _index_by_key(assets, key="symbol")


def _load_market_regime(data_dir: Path) -> Dict[str, Any]:
    path = data_dir / "market" / "market_regime.json"
    raw = _load_json(path, default={})
    return raw if isinstance(raw, dict) else {}


def _load_emotional_regime(data_dir: Path) -> Dict[str, Any]:
    path = data_dir / "analysis" / "emotional_regime.json"
    raw = _load_json(path, default={})
    return raw if isinstance(raw, dict) else {}


def _load_cross_asset(data_dir: Path) -> Dict[str, Any]:
    path = data_dir / "analysis" / "cross_asset_engine_pro.json"
    raw = _load_json(path, default={})
    return raw if isinstance(raw, dict) else {}


def _load_ml_signals(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Charge signal_candidates_filtered.json et indexe par symbol.
    On attend typiquement une liste de dicts avec 'symbol' et 'decision'.
    """
    path = data_dir / "analysis" / "signal_candidates_filtered.json"
    raw = _load_json(path, default=[])
    if not isinstance(raw, list):
        raw = []
    return _index_by_key(raw, key="symbol")


# ---------------------------------------------------------------------------
# Scoring du flow
# ---------------------------------------------------------------------------


def _score_flow_for_asset(
    symbol: str,
    momentum: Optional[Dict[str, Any]],
    liquidity: Optional[Dict[str, Any]],
    story: Optional[Dict[str, Any]],
    cross_asset: Dict[str, Any],
    ml_signal: Optional[Dict[str, Any]],
    market_regime: Dict[str, Any],
    emotional_regime: Dict[str, Any],
) -> FlowAsset:
    score = 50.0
    reasons: List[str] = []
    flags = {
        "hard_veto": False,
        "soft_veto": False,
    }

    # ---------------- Momentum 4.0 ----------------
    m_regime = None
    if momentum:
        m_regime = momentum.get("regime", "neutral")
        m_flags = momentum.get("flags") or {}
        momentum_score = float(momentum.get("momentum_score", 50.0))

        if m_regime == "strong_long":
            score += 15.0
            reasons.append("Momentum fort (regime=strong_long)")
        elif m_regime == "long_bias":
            score += 7.0
            reasons.append("Momentum positif (regime=long_bias)")
        elif m_regime in ("avoid", "block"):
            score -= 15.0
            reasons.append(f"Momentum défavorable (regime={m_regime})")

        if m_flags.get("hard_veto"):
            flags["hard_veto"] = True
            score -= 25.0
            reasons.append("Hard veto momentum")
        if m_flags.get("soft_veto"):
            flags["soft_veto"] = True
            score -= 10.0
            reasons.append("Soft veto momentum")

        # Petit ajustement continu autour de 50
        score += (momentum_score - 50.0) * 0.15

    # ---------------- Liquidité ----------------
    if liquidity:
        l_regime = liquidity.get("regime", "ok")
        if l_regime == "deep":
            score += 10.0
            reasons.append("Liquidité profonde")
        elif l_regime == "ok":
            score += 3.0
            reasons.append("Liquidité correcte")
        elif l_regime == "shallow":
            score -= 10.0
            reasons.append("Liquidité faible (shallow)")
        elif l_regime == "avoid":
            score -= 20.0
            reasons.append("Liquidité à éviter (avoid)")

        l_flags = liquidity.get("flags") or {}
        if l_flags.get("hard_veto"):
            flags["hard_veto"] = True
            score -= 20.0
            reasons.append("Hard veto liquidité")
        if l_flags.get("soft_veto"):
            flags["soft_veto"] = True
            score -= 10.0
            reasons.append("Soft veto liquidité")

    # ---------------- Story / Narrative ----------------
    if story:
        story_regime = story.get("story_regime") or story.get("regime") or "unknown"
        if story_regime == "strong_story":
            score += 10.0
            reasons.append("Story / narrative très forte")
        elif story_regime == "healthy_story":
            score += 5.0
            reasons.append("Story / narrative saine")
        elif story_regime == "weak_story":
            score -= 5.0
            reasons.append("Narrative fragile / non alignée")
        elif story_regime == "no_story":
            score -= 7.0
            reasons.append("Pas de narrative claire (no_story)")

    # ---------------- Cross-Asset Engine Pro ----------------
    cross_flag = cross_asset.get("global_flag", "ok")
    if cross_flag == "danger":
        score -= 15.0
        reasons.append("Contexte cross-asset dangereux (flag=danger)")
    elif cross_flag == "caution":
        score -= 5.0
        reasons.append("Contexte cross-asset prudent (flag=caution)")

    # ---------------- Market & Emotional Regime ----------------
    mr_flag = market_regime.get("regime", "neutral")
    if mr_flag == "bear":
        score -= 7.0
        reasons.append("Régime marché défensif (bear)")
    elif mr_flag == "bull":
        score += 5.0
        reasons.append("Régime marché porteur (bull)")

    emo = emotional_regime.get("emotional_regime") or emotional_regime.get("mode")
    if emo == "stressed":
        score -= 5.0
        reasons.append("Emotional regime stressé (stressed)")
    elif emo == "euphoric":
        score -= 3.0
        reasons.append("Emotional regime euphoric (prudence)")

    # ---------------- ML Filter ----------------
    ml_decision = None
    if ml_signal:
        ml_decision = ml_signal.get("decision") or ml_signal.get("ml_decision")
        if ml_decision == "accept":
            score += 10.0
            reasons.append("Signal ML accepté (decision=accept)")
        elif ml_decision == "watch":
            score += 3.0
            reasons.append("Signal ML en 'watch'")
        elif ml_decision == "reject":
            score -= 10.0
            reasons.append("Signal ML rejeté (decision=reject)")

    # Clamp score
    score = _clamp(score)

    # Direction du flow
    if score >= 65.0:
        direction = "inflow"
    elif score <= 40.0:
        direction = "outflow"
    else:
        direction = "neutral"

    drivers = {
        "momentum_regime": m_regime,
        "liquidity_regime": liquidity.get("regime") if liquidity else None,
        "story_regime": story.get("story_regime") if story else None,
        "cross_asset_flag": cross_flag,
        "market_regime": mr_flag,
        "emotional_regime": emo,
        "ml_decision": ml_decision,
    }

    return FlowAsset(
        symbol=symbol,
        flow_score=round(score, 2),
        direction=direction,
        drivers=drivers,
        flags=flags,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Agrégation globale
# ---------------------------------------------------------------------------


def compute_flow_overview(data_dir: Path) -> FlowOverview:
    # Chargement des différentes briques
    momentum_idx = _load_momentum(data_dir)
    liquidity_idx = _load_liquidity(data_dir)
    story_idx = _load_story(data_dir)
    cross_asset = _load_cross_asset(data_dir)
    ml_idx = _load_ml_signals(data_dir)
    market_regime = _load_market_regime(data_dir)
    emotional_regime = _load_emotional_regime(data_dir)

    all_symbols = (
        set(momentum_idx.keys())
        | set(liquidity_idx.keys())
        | set(story_idx.keys())
        | set(ml_idx.keys())
    )

    assets: List[FlowAsset] = []

    for symbol in sorted(all_symbols):
        m = momentum_idx.get(symbol)
        l = liquidity_idx.get(symbol)
        s = story_idx.get(symbol)
        ml = ml_idx.get(symbol)

        fa = _score_flow_for_asset(
            symbol=symbol,
            momentum=m,
            liquidity=l,
            story=s,
            cross_asset=cross_asset,
            ml_signal=ml,
            market_regime=market_regime,
            emotional_regime=emotional_regime,
        )
        assets.append(fa)

    nb_assets = len(assets)
    by_direction = {"inflow": 0, "neutral": 0, "outflow": 0}
    nb_hard_veto = 0
    nb_soft_veto = 0

    for a in assets:
        by_direction[a.direction] = by_direction.get(a.direction, 0) + 1
        if a.flags.get("hard_veto"):
            nb_hard_veto += 1
        if a.flags.get("soft_veto"):
            nb_soft_veto += 1

    # Global flag
    global_flag = "ok"
    if nb_hard_veto > 0 or by_direction["outflow"] > max(1, nb_assets // 2):
        global_flag = "danger"
    elif by_direction["outflow"] > 0 or cross_asset.get("global_flag") in ("caution", "danger"):
        global_flag = "caution"

    stats = {
        "nb_assets": nb_assets,
        "by_direction": by_direction,
        "nb_hard_veto": nb_hard_veto,
        "nb_soft_veto": nb_soft_veto,
        "global_flag": global_flag,
    }

    overview = FlowOverview(
        generated_at=datetime.now(timezone.utc).isoformat(),
        stats=stats,
        assets=assets,
    )
    return overview


# ---------------------------------------------------------------------------
# Entrée CLI
# ---------------------------------------------------------------------------


def main() -> None:
    root_dir, data_dir = _get_root_and_data_dir()
    logger.info("[flow_engine_pro] ROOT_DIR=%s, DATA_DIR=%s", root_dir, data_dir)

    analysis_dir = data_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    overview = compute_flow_overview(data_dir)

    out_path = analysis_dir / "flow_engine_pro.json"
    serializable = {
        "generated_at": overview.generated_at,
        "stats": overview.stats,
        "assets": [asdict(a) for a in overview.assets],
    }
    save_json_file(out_path, serializable)

    logger.info(
        "[flow_engine_pro] flow_engine_pro.json sauvegardé (%s, assets=%d, global_flag=%s).",
        out_path,
        overview.stats["nb_assets"],
        overview.stats["global_flag"],
    )


if __name__ == "__main__":
    main()
