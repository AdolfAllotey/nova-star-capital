"""
Weak Signals Engine Pro
-----------------------

Objectif :
- Scanner l'état global des moteurs "Pro" (momentum, liquidité, cycle, story, flow,
  volatilité, meta-score, risk engine)
- Détecter des signaux faibles :
    - weak_watch  : signaux positifs naissants, mais pas encore assez forts pour un "go" plein pot
    - weak_avoid  : signaux de détérioration / risques latents, sans hard veto

Entrées (JSON attendus dans data/analysis) :
- momentum_engine_4_0.json
- liquidity_engine_pro.json
- cycle_engine_pro.json
- story_engine_pro.json
- flow_engine_pro.json
- volatility_engine_pro.json
- meta_score_engine_pro.json
- risk_engine_pro.json

Sortie :
- data/analysis/weak_signals_engine_pro.json
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = logging.getLogger(__name__)


def _load_index(data: Dict[str, Any], key: str = "symbol") -> Dict[str, Dict[str, Any]]:
    """
    Construit un index {symbol -> asset_dict} à partir d'un JSON de type { "assets": [...] }.
    """
    assets = data.get("assets", []) if isinstance(data, dict) else []
    index: Dict[str, Dict[str, Any]] = {}
    for a in assets:
        symbol = a.get(key)
        if symbol:
            index[symbol] = a
    return index


def _build_inputs(data_dir: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Charge les différents moteurs Pro et construit un dictionnaire :
    inputs_by_symbol[symbol] = { momentum=..., liquidity=..., ... }
    """
    # Chargement des JSON (robuste : default={})
    momentum_data = load_json_file(
        os.path.join(data_dir, "analysis", "momentum_engine_4_0.json"),
        default={}
    )
    liquidity_data = load_json_file(
        os.path.join(data_dir, "analysis", "liquidity_engine_pro.json"),
        default={}
    )
    cycle_data = load_json_file(
        os.path.join(data_dir, "analysis", "cycle_engine_pro.json"),
        default={}
    )
    story_data = load_json_file(
        os.path.join(data_dir, "analysis", "story_engine_pro.json"),
        default={}
    )
    flow_data = load_json_file(
        os.path.join(data_dir, "analysis", "flow_engine_pro.json"),
        default={}
    )
    volatility_data = load_json_file(
        os.path.join(data_dir, "analysis", "volatility_engine_pro.json"),
        default={}
    )
    meta_data = load_json_file(
        os.path.join(data_dir, "analysis", "meta_score_engine_pro.json"),
        default={}
    )
    risk_data = load_json_file(
        os.path.join(data_dir, "analysis", "risk_engine_pro.json"),
        default={}
    )

    # Index par symbol
    momentum_idx = _load_index(momentum_data)
    liquidity_idx = _load_index(liquidity_data)
    cycle_idx = _load_index(cycle_data)
    story_idx = _load_index(story_data)
    flow_idx = _load_index(flow_data)
    volatility_idx = _load_index(volatility_data)
    meta_idx = _load_index(meta_data)
    risk_idx = _load_index(risk_data)

    # Ensemble de tous les symbols connus
    symbols = set(
        list(momentum_idx.keys())
        + list(liquidity_idx.keys())
        + list(cycle_idx.keys())
        + list(story_idx.keys())
        + list(flow_idx.keys())
        + list(volatility_idx.keys())
        + list(meta_idx.keys())
        + list(risk_idx.keys())
    )

    inputs_by_symbol: Dict[str, Dict[str, Any]] = {}

    for symbol in symbols:
        inputs_by_symbol[symbol] = {
            "momentum": momentum_idx.get(symbol),
            "liquidity": liquidity_idx.get(symbol),
            "cycle": cycle_idx.get(symbol),
            "story": story_idx.get(symbol),
            "flow": flow_idx.get(symbol),
            "volatility": volatility_idx.get(symbol),
            "meta": meta_idx.get(symbol),
            "risk": risk_idx.get(symbol),
        }

    return inputs_by_symbol, sorted(symbols)


def compute_weak_signals_pro(data_dir: str) -> Dict[str, Any]:
    """
    Calcule les signaux faibles Pro à partir des différents moteurs.

    Règles (simplifiées mais robustes) :

    - weak_watch (positif) si :
        * pas de hard veto
        * meta_score_pro ∈ [50, 65)
        * momentum_regime ∈ {neutral, long_bias}
        * flow_direction ∈ {neutral, inflow}
        * story_regime pas dans {weak_story, no_story}

    - weak_avoid (négatif) si :
        * pas de hard veto
        * meta_score_pro ∈ [40, 55)
        * et au moins un des éléments de fragilité :
            - cycle_regime ∈ {caution, danger}
            - flow_direction == outflow
            - story_regime ∈ {weak_story, no_story}
            - risk_flag == caution
    """
    inputs_by_symbol, symbols = _build_inputs(data_dir)

    assets_output: List[Dict[str, Any]] = []
    nb_weak_watch = 0
    nb_weak_avoid = 0

    for symbol in symbols:
        ctx = inputs_by_symbol.get(symbol, {})

        m = ctx.get("momentum") or {}
        l = ctx.get("liquidity") or {}
        c = ctx.get("cycle") or {}
        s = ctx.get("story") or {}
        f = ctx.get("flow") or {}
        v = ctx.get("volatility") or {}
        meta = ctx.get("meta") or {}
        r = ctx.get("risk") or {}

        # Flags de veto
        m_flags = m.get("flags") or {}
        l_flags = l.get("flags") or {}
        f_flags = f.get("flags") or {}
        r_flags = r.get("flags") or {}

        hard_veto = any([
            bool(m_flags.get("hard_veto")),
            bool(l_flags.get("hard_veto")),
            bool(f_flags.get("hard_veto")),
            bool(r_flags.get("hard_veto")),
        ])

        # On ignore complètement si hard veto
        if hard_veto:
            continue

        momentum_regime = m.get("regime")
        liquidity_regime = l.get("regime")
        cycle_regime = c.get("cycle_regime")
        cycle_score = c.get("cycle_phase_score")
        story_regime = s.get("story_regime")
        flow_direction = f.get("direction")
        volatility_regime = v.get("volatility_regime")
        risk_flag = r.get("risk_flag")
        meta_score = meta.get("meta_score_pro")

        # Si aucun meta_score exploitable, on se contente d'observer sans le tagger
        if meta_score is None:
            continue

        reasons: List[str] = []
        weak_kind: str | None = None

        # --------- Règle weak_watch (positif / opportunité à surveiller) ---------
        if (
            50.0 <= meta_score < 65.0
            and momentum_regime in ("neutral", "long_bias", None)
            and flow_direction in ("neutral", "inflow", None)
            and story_regime not in ("weak_story", "no_story")
        ):
            weak_kind = "weak_watch"
            reasons.append("Meta-score modéré mais cohérent avec un contexte neutre/positif")
            if momentum_regime in ("neutral", "long_bias"):
                reasons.append(f"Momentum {momentum_regime}")
            if flow_direction in ("neutral", "inflow"):
                reasons.append(f"Flux {flow_direction or 'neutres'}")
            if story_regime:
                reasons.append(f"Story regime {story_regime}")

        # --------- Règle weak_avoid (fragilité / risque latent) ---------
        if weak_kind is None and 40.0 <= meta_score < 55.0:
            fragilities: List[str] = []

            if cycle_regime in ("caution", "danger"):
                fragilities.append(f"Cycle {cycle_regime}")
            if flow_direction == "outflow":
                fragilities.append("Flux sortants (outflow)")
            if story_regime in ("weak_story", "no_story"):
                fragilities.append(f"Story fragile ({story_regime})")
            if risk_flag == "caution":
                fragilities.append("Risk engine en mode caution")

            if fragilities:
                weak_kind = "weak_avoid"
                reasons.extend(fragilities)

        if weak_kind is None:
            # Pas de signal faible explicite pour cet asset
            continue

        if weak_kind == "weak_watch":
            nb_weak_watch += 1
        elif weak_kind == "weak_avoid":
            nb_weak_avoid += 1

        assets_output.append(
            {
                "symbol": symbol,
                "kind": weak_kind,
                "meta_score_pro": round(meta_score, 2),
                "momentum_regime": momentum_regime,
                "liquidity_regime": liquidity_regime,
                "cycle_regime": cycle_regime,
                "cycle_score": cycle_score,
                "story_regime": story_regime,
                "flow_direction": flow_direction,
                "volatility_regime": volatility_regime,
                "risk_flag": risk_flag,
                "reasons": reasons,
            }
        )

    nb_assets = len(symbols)

    # Global flag : simple et prudent
    if nb_weak_avoid >= max(1, nb_assets // 2):
        global_flag = "caution"
    else:
        global_flag = "ok"

    stats = {
        "nb_assets": nb_assets,
        "nb_weak_watch": nb_weak_watch,
        "nb_weak_avoid": nb_weak_avoid,
        "global_flag": global_flag,
    }

    return {
        "stats": stats,
        "assets": assets_output,
    }


def main() -> None:
    data_dir = get_data_dir()
    logger.info("[weak_signals_engine_pro] DATA_DIR=%s", data_dir)

    result = compute_weak_signals_pro(data_dir)

    out_path = os.path.join(data_dir, "analysis", "weak_signals_engine_pro.json")
    save_json_file(out_path, result)

    stats = result.get("stats", {})
    logger.info(
        "[weak_signals_engine_pro] weak_signals_engine_pro.json sauvegardé (%s, watch=%s, avoid=%s, flag=%s).",
        out_path,
        stats.get("nb_weak_watch"),
        stats.get("nb_weak_avoid"),
        stats.get("global_flag"),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
