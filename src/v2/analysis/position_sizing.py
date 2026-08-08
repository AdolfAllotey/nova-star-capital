from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

DATA_DIR = Path(get_data_dir()).resolve()
ANALYSIS_DIR = DATA_DIR / "analysis"
TRADING_DIR = DATA_DIR / "trading"
# NSC_PATCH: load capital allocation (capital_per_trade) [AFTER_TRADING_DIR]
capital_per_trade = None
try:
    cap = load_json_file(str(TRADING_DIR / 'capital_allocation.json'), default={}) or {}
    if isinstance(cap.get('capital_per_trade'), (int, float)):
        capital_per_trade = float(cap['capital_per_trade'])
except Exception:
    capital_per_trade = None

SIGNAL_CANDIDATES_FILE = ANALYSIS_DIR / "signal_candidates.json"
RISK_LIMITS_FILE = TRADING_DIR / "risk_limits.json"
STRATEGY_WEIGHTS_FILE = ANALYSIS_DIR / "strategy_weights.json"
OUTPUT_FILE = TRADING_DIR / "sized_signals.json"


# ---------------------------------------------------------------------------
# Chargement des inputs
# ---------------------------------------------------------------------------


def _load_signal_candidates() -> List[Dict[str, Any]]:
    """
    Charge les signaux candidats issus de signal_voting.

    Format attendu (exemple) :
    [
      {
        "symbol": "bitcoin",
        "side": "buy",
        "strategy": "momentum",
        "base_weight": 1.0,
        ...
      },
      ...
    ]
    """
    data = load_json_file(str(SIGNAL_CANDIDATES_FILE), default=[])
    if not isinstance(data, list):
        logger.warning(
            "[position_sizing] signal_candidates.json n'est pas une liste (%s).",
            SIGNAL_CANDIDATES_FILE,
        )
        return []
    logger.info(
        "[position_sizing] %d signaux candidats chargés depuis %s",
        len(data),
        SIGNAL_CANDIDATES_FILE,
    )
    return data


def _load_risk_limits() -> Dict[str, Any]:
    """
    Charge les limites de risque globales produites par risk_controller.

    Format attendu (exemple) :
    {
      "mode": "reduced",          # normal / reduced / paused
      "risk_on_off": "on",        # on / off
      "size_factor": 0.5,         # multiplicateur global
      "max_positions": 50,
      ...
    }
    """
    defaults = {
        "mode": "normal",
        "risk_on_off": "on",
        "size_factor": 1.0,
        "max_positions": 50,
    }
    data = load_json_file(str(RISK_LIMITS_FILE), default={})
    if not isinstance(data, dict):
        logger.warning(
            "[position_sizing] risk_limits.json invalide, utilisation des valeurs par défaut."
        )
        return defaults

    merged = {**defaults, **data}
    logger.info(
        "[position_sizing] Risk limits chargés: mode=%s, risk_on_off=%s, size_factor=%.2f, max_positions=%d",
        merged.get("mode"),
        merged.get("risk_on_off"),
        float(merged.get("size_factor", 1.0)),
        int(merged.get("max_positions", 50)),
    )
    return merged


def _load_strategy_weights() -> Dict[str, float]:
    """
    Charge les poids de stratégie calculés par strategy_selector.

    Format attendu (strategy_weights.json) :
    {
      "summary": {...},
      "strategies": [
        {
          "name": "momentum",
          "normalized_weight": 0.55,
          ...
        },
        ...
      ]
    }

    Retourne un dict { strategy_name: normalized_weight }.
    """
    data = load_json_file(str(STRATEGY_WEIGHTS_FILE), default={})
    strategies = data.get("strategies", [])
    if not isinstance(strategies, list) or not strategies:
        logger.warning(
            "[position_sizing] Aucun poids de stratégie trouvé dans %s, "
            "fallback sur poids=1.0 pour toutes les stratégies.",
            STRATEGY_WEIGHTS_FILE,
        )
        return {}

    weights: Dict[str, float] = {}
    for s in strategies:
        name = s.get("name")
        if not name:
            continue
        try:
            w = float(s.get("normalized_weight", 1.0))
        except (TypeError, ValueError):
            w = 1.0
        weights[name] = w

    best = max(weights.items(), key=lambda kv: kv[1])[0] if weights else None
    logger.info(
        "[position_sizing] strategy_weights.json chargé (%s): %d stratégies, best=%s",
        STRATEGY_WEIGHTS_FILE,
        len(weights),
        best,
    )
    return weights


# ---------------------------------------------------------------------------
# Sizing des signaux
# ---------------------------------------------------------------------------


def _size_signals(
    signals: List[Dict[str, Any]],
    risk_limits: Dict[str, Any],
    strategy_weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Applique :
      - le size_factor global (risk_controller),
      - le poids de stratégie (strategy_selector),
      - le base_weight par signal.

    Règles :
      - Si risk_on_off="off" ou mode="paused" → final_size_multiplier=0.
      - Sinon : final_size_multiplier = base_weight * size_factor * strategy_weight
      - On borne final_size_multiplier à [0, 1].
    """
    risk_on_off = risk_limits.get("risk_on_off", "on")
    mode = risk_limits.get("mode", "normal")
    size_factor = float(risk_limits.get("size_factor", 1.0))
    strategy_intensity = risk_limits.get("strategy_intensity_factors", {}) or {}
    max_positions = int(risk_limits.get("max_positions", 50))
    # NSC_PATCH: load capital_per_trade from capital_allocation.json
    capital_per_trade = None
    try:
        cap = load_json_file(str(TRADING_DIR / "capital_allocation.json"), default={}) or {}
        cpt = cap.get("capital_per_trade")
        if isinstance(cpt, (int, float)):
            capital_per_trade = float(cpt)
    except Exception:
        logger.exception("[position_sizing] failed to load capital_allocation.json")

    sized: List[Dict[str, Any]] = []

    if not signals:
        logger.info("[position_sizing] Aucun signal à sizer.")
        return sized

    # Hard stop global
    if risk_on_off == "off" or mode == "paused":
        logger.info(
            "[position_sizing] Risk OFF ou mode paused (risk_on_off=%s, mode=%s) → tous les signaux à 0.",
            risk_on_off,
            mode,
        )
        for sig in signals:
            sig_out = dict(sig)
            notes = sig_out.get("notes", [])
            if not isinstance(notes, list):
                notes = [str(notes)]
            notes.append(f"Risk controller: risk_on_off={risk_on_off}, mode={mode} → taille=0.")
            sig_out["final_size_multiplier"] = 0.0
            sig_out["final_weight"] = 0.0
            sig_out["notes"] = notes
            sized.append(sig_out)
        return sized

    # Sinon, risk ON / modes normal ou reduced
    logger.info(
        "[position_sizing] Sizing des signaux avec risk_on_off=%s, mode=%s, size_factor=%.2f",
        risk_on_off,
        mode,
        size_factor,
    )

    # On limite quand même le nombre de positions potentielles
    signals_limited = signals[:max_positions]

    for sig in signals_limited:
        sig_out = dict(sig)

        symbol = sig.get("symbol", "?")
        strategy = sig.get("strategy", "unknown")
        base_weight = sig.get("base_weight", 1.0)

        try:
            base_weight = float(base_weight)
        except (TypeError, ValueError):
            base_weight = 1.0

        if base_weight < 0:
            base_weight = 0.0

        # Poids de stratégie (fallback=1.0)
        strat_weight = float(strategy_weights.get(strategy, 1.0))

        # Multiplicateur brut
        strategy = str(sig.get("strategy", "unknown")).lower()
        strategy_factor = float(strategy_intensity.get(strategy, 1.0) or 1.0)

        # NSC PREPROD QUALITY FILTER:
        # Weak crypto momentum signals must not create new exposure.
        try:
            meta_score = float(sig.get("meta_score", sig.get("momentum_score", 0.0)) or 0.0)
        except Exception:
            meta_score = 0.0

        momentum_regime = str(sig.get("momentum_regime", "") or "").lower()

        quality_block = False
        quality_reasons = []

        if meta_score < 35.0:
            quality_block = True
            quality_reasons.append(f"quality_block: meta_score={meta_score:.2f}<35")

        if momentum_regime == "weak":
            quality_block = True
            quality_reasons.append("quality_block: momentum_regime=weak")

        raw_mult = base_weight * size_factor * strat_weight * strategy_factor

        if quality_block:
            raw_mult = 0.0

        # Bornes [0, 1]
        final_mult = max(0.0, min(1.0, raw_mult))

        notes = sig_out.get("notes", [])
        if not isinstance(notes, list):
            notes = [str(notes)]

        notes.append(f"Base weight={base_weight:.2f}")
        notes.append(f"Risk size_factor={size_factor:.2f} (mode={mode})")
        if strategy_weights:
            notes.append(
                f"Strategy weight[{strategy}]={strat_weight:.2f} "
                f"(influencé par perf 30j)"
            )
        else:
            notes.append("Strategy weights indisponibles → fallback 1.0.")

        if "quality_reasons" in locals() and quality_reasons:
            notes.extend(quality_reasons)
        notes.append(f"final_size_multiplier={final_mult:.3f}")

        sig_out["final_size_multiplier"] = final_mult
        # Pour l’instant, on assimile final_weight à final_size_multiplier
        sig_out["final_weight"] = final_mult
        # NSC_PATCH: write notional_eur = capital_per_trade * final_size_multiplier
        if isinstance(capital_per_trade, (int, float)):
            sig_out["notional_eur"] = float(capital_per_trade) * float(final_mult)
        else:
            sig_out["notional_eur"] = None
        sig_out["notes"] = notes

        sized.append(sig_out)

    logger.info(
        "[position_sizing] Terminé, %d signaux sizés (max_positions=%d).",
        len(sized),
        max_positions,
    )
    return sized


def compute_position_sizing() -> List[Dict[str, Any]]:
    """
    Pipeline complet :
      - charge signaux candidats,
      - charge risk_limits (risk_controller),
      - charge strategy_weights (strategy_selector),
      - produit sized_signals.json.
    """
    signals = _load_signal_candidates()
    risk_limits = _load_risk_limits()
    strategy_weights = _load_strategy_weights()

    sized = _size_signals(signals, risk_limits, strategy_weights)

    save_json_file(str(OUTPUT_FILE), sized)
    logger.info(
        "[position_sizing] sized_signals sauvegardé (%s, n=%d, risk_on_off=%s, size_factor=%.2f)",
        OUTPUT_FILE,
        len(sized),
        risk_limits.get("risk_on_off", "on"),
        float(risk_limits.get("size_factor", 1.0)),
    )

    return sized


def main() -> None:
    compute_position_sizing()


if __name__ == "__main__":
    main()
