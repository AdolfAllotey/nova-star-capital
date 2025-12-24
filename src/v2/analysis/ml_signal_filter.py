"""
ml_signal_filter.py
---------------------------------
Filtre "ML léger" pour les signaux Nova Star Capital (hedge fund light).

Objectifs :
  - Lire les signaux de signal_voting (signal_candidates.json)
  - Extraire quelques features simples :
      * momentum_meta_score (0–100)
      * confidence (0–1)
      * regime_risk_on (0/1)
      * whale_score (0–100) si dispo
      * narrative_score (0–100) si dispo
  - Appliquer un modèle linéaire très léger (pseudo-ML) :
      score_raw = w · x + b
      proba = sigmoid(score_raw) dans [0, 1]
  - Décider :
      * proba >= threshold_accept → "accept"
      * threshold_watch <= proba < threshold_accept → "watch"
      * sinon → "reject"

Entrées :
  - data/analysis/signal_candidates.json
  - data/analysis/ml_signal_filter_config.json (optionnel)

Sorties :
  - data/analysis/ml_signal_filter_output.json        (détails par signal)
  - data/analysis/signal_candidates_filtered.json    (signaux "accept" uniquement)

Version PREPROD : aucun ordre réel ; uniquement des fichiers JSON.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("ml_signal_filter")

# ---------------------------------------------------------------------------
# DATA_DIR aligné sur le reste
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
MARKET_DIR = DATA_DIR / "market"

ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

SIGNAL_CANDIDATES_FILE = ANALYSIS_DIR / "signal_candidates.json"
ML_CONFIG_FILE = ANALYSIS_DIR / "ml_signal_filter_config.json"
ML_OUTPUT_FILE = ANALYSIS_DIR / "ml_signal_filter_output.json"
FILTERED_CANDIDATES_FILE = ANALYSIS_DIR / "signal_candidates_filtered.json"

MARKET_REGIME_FILE = MARKET_DIR / "market_regime.json"

logger.info(f"[ml_signal_filter] ROOT_DIR={ROOT_DIR}, DATA_DIR={DATA_DIR}")

# ---------------------------------------------------------------------------
# file_utils fallback
# ---------------------------------------------------------------------------

try:
    from src.v2.utils.file_utils import load_json_file, save_json_file  # type: ignore
except Exception:  # pragma: no cover
    load_json_file = None
    save_json_file = None

    import json

    def _load_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Erreur lors du chargement JSON: %s", path)
            return default

    def _save_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                import json as _json
                _json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.exception("Erreur lors de l'écriture JSON: %s", path)
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclasses / Config
# ---------------------------------------------------------------------------

@dataclass
class MLConfig:
    w_meta: float = 0.04          # pondération du momentum_meta_score (0–100)
    w_confidence: float = 1.0     # pondération de la confiance (0–1)
    w_risk_on: float = 0.5        # bonus si regime_risk_on=1
    w_whale: float = 0.01         # pondération whale_score (0–100)
    w_narrative: float = 0.01     # pondération narrative_score (0–100)
    bias: float = -2.0            # biais global

    threshold_accept: float = 0.7
    threshold_watch: float = 0.5

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MLConfig":
        kwargs = {}
        for field in cls.__dataclass_fields__.keys():  # type: ignore
            if field in d:
                kwargs[field] = d[field]
        return cls(**kwargs)


@dataclass
class MLSignalResult:
    symbol: str
    action_initial: str
    final_score_initial: float

    momentum_meta_score: float
    confidence: float
    regime_risk_on: float
    whale_score: float
    narrative_score: float

    linear_score: float
    proba: float
    ml_decision: str  # accept / watch / reject

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _load_ml_config() -> MLConfig:
    data = _load_json(ML_CONFIG_FILE, default=None)
    if isinstance(data, dict):
        cfg = MLConfig.from_dict(data)
        logger.info(
            "[ml_signal_filter] Config ML chargée depuis %s (threshold_accept=%.2f, threshold_watch=%.2f)",
            ML_CONFIG_FILE,
            cfg.threshold_accept,
            cfg.threshold_watch,
        )
        return cfg

    logger.warning(
        "[ml_signal_filter] Fichier de config ML absent ou invalide (%s), utilisation des valeurs par défaut.",
        ML_CONFIG_FILE,
    )
    return MLConfig()


def _load_regime_risk_on() -> float:
    """
    Retourne 1.0 si regime_risk_on=1 ou regime 'bull', sinon 0.0.
    """
    data = _load_json(MARKET_REGIME_FILE, default={})
    if not isinstance(data, dict):
        return 0.0

    risk_on = data.get("risk_on")
    if risk_on is True or risk_on == 1:
        return 1.0

    regime = str(data.get("regime") or "").lower()
    if regime.startswith("bull"):
        return 1.0

    return 0.0


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 1.0 if x > 0 else 0.0


def _load_signal_candidates() -> List[Dict[str, Any]]:
    data = _load_json(SIGNAL_CANDIDATES_FILE, default=[])
    if not isinstance(data, list):
        logger.warning(
            "[ml_signal_filter] Format inattendu pour %s (attendu list).",
            SIGNAL_CANDIDATES_FILE,
        )
        return []
    return data


# ---------------------------------------------------------------------------
# Core ML filter
# ---------------------------------------------------------------------------

def evaluate_signal(
    signal: Dict[str, Any],
    cfg: MLConfig,
    regime_risk_on: float,
) -> MLSignalResult:
    symbol = str(signal.get("symbol") or "")
    action_initial = str(signal.get("action") or "").lower()
    final_score_initial = _safe_float(signal.get("final_score", 0.0), 0.0)

    inputs = signal.get("inputs") or {}

    meta = _safe_float(
        inputs.get("momentum_meta_score", signal.get("meta_score", 0.0)),
        0.0,
    )
    confidence = _safe_float(signal.get("confidence", 0.0), 0.0)

    whale_score = _safe_float(inputs.get("whale_score"), 0.0)
    narrative_score = _safe_float(inputs.get("narrative_score"), 0.0)

    # Normalisations approximatives
    meta_n = meta / 100.0
    whale_n = whale_score / 100.0
    narrative_n = narrative_score / 100.0

    linear = (
        cfg.w_meta * meta_n
        + cfg.w_confidence * confidence
        + cfg.w_risk_on * regime_risk_on
        + cfg.w_whale * whale_n
        + cfg.w_narrative * narrative_n
        + cfg.bias
    )

    proba = _sigmoid(linear)

    if proba >= cfg.threshold_accept:
        decision = "accept"
    elif proba >= cfg.threshold_watch:
        decision = "watch"
    else:
        decision = "reject"

    return MLSignalResult(
        symbol=symbol,
        action_initial=action_initial,
        final_score_initial=final_score_initial,
        momentum_meta_score=meta,
        confidence=confidence,
        regime_risk_on=regime_risk_on,
        whale_score=whale_score,
        narrative_score=narrative_score,
        linear_score=linear,
        proba=proba,
        ml_decision=decision,
    )


def run_ml_filter() -> None:
    cfg = _load_ml_config()
    regime_risk_on = _load_regime_risk_on()

    signals = _load_signal_candidates()
    logger.info("[ml_signal_filter] %d signaux chargés depuis %s.", len(signals), SIGNAL_CANDIDATES_FILE)

    results: List[MLSignalResult] = []
    filtered_signals: List[Dict[str, Any]] = []

    for s in signals:
        res = evaluate_signal(s, cfg, regime_risk_on)
        results.append(res)

        if res.ml_decision == "accept":
            s_copy = dict(s)
            s_copy.setdefault("ml_filter", {})
            s_copy["ml_filter"].update(
                {
                    "proba": res.proba,
                    "decision": res.ml_decision,
                    "linear_score": res.linear_score,
                }
            )
            filtered_signals.append(s_copy)

    # Sauvegardes
    _save_json(ML_OUTPUT_FILE, [r.to_dict() for r in results])
    _save_json(FILTERED_CANDIDATES_FILE, filtered_signals)

    logger.info(
        "[ml_signal_filter] Résultats ML sauvegardés dans %s (n=%d), signaux filtrés dans %s (n_accept=%d).",
        ML_OUTPUT_FILE,
        len(results),
        FILTERED_CANDIDATES_FILE,
        len(filtered_signals),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    run_ml_filter()


if __name__ == "__main__":
    main()
