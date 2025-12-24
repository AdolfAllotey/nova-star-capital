import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

# ---------------------------------------------------------------------------
# Config & paths
# ---------------------------------------------------------------------------

LOGGER_NAME = "hype_cycle_engine_light"
logger = get_logger(LOGGER_NAME)

# On part du principe : .../app/src/v2/analysis/hype_cycle_engine_light.py
# -> ROOT_DIR = .../app, DATA_DIR = .../app/data
ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
MARKET_DIR = DATA_DIR / "market"


@dataclass
class AssetInputs:
    symbol: str
    momentum_score: float = 0.0
    meta_score: float = 0.0
    sentiment_score: float = 0.5
    ret_1d: float = 0.0
    ret_7d: float = 0.0


@dataclass
class HypeResult:
    symbol: str
    stage: str
    hype_score: float
    risk_flag: str
    reasons: List[str]


# ---------------------------------------------------------------------------
# Helpers: chargement des données
# ---------------------------------------------------------------------------


def _load_momentum_scores() -> Dict[str, AssetInputs]:
    """
    Charge momentum_scores.json et retourne un dict symbol -> AssetInputs (partiel).

    Formats possibles gérés :
    1) Liste directe :
       [
         {"symbol": "bitcoin", "momentum_score": 63.2, "meta_score": 55.1, ...},
         ...
       ]

    2) Dict avec clé "assets" ou "scores" :
       {
         "timestamp": "...",
         "assets": [ {...}, {...} ]
       }

    3) Dict de symboles :
       {
         "bitcoin": {"momentum_score": 63.2, "meta_score": 55.1, ...},
         ...
       }
    """
    path = ANALYSIS_DIR / "momentum_scores.json"
    data = load_json_file(path, default=[]) or []

    assets_raw: List[Dict[str, Any]]

    if isinstance(data, list):
        # Cas 1: liste directe
        assets_raw = data
    elif isinstance(data, dict):
        # Essayer de trouver une liste d'assets à l'intérieur
        candidate = data.get("assets") or data.get("scores") or data.get("data")
        if isinstance(candidate, list):
            assets_raw = candidate
        elif isinstance(candidate, dict):
            assets_raw = list(candidate.values())
        else:
            # Peut-être directement un dict de symboles -> objet
            assets_raw = list(data.values())
    else:
        assets_raw = []

    result: Dict[str, AssetInputs] = {}
    for item in assets_raw:
        if not isinstance(item, dict):
            continue

        symbol = str(item.get("symbol") or item.get("asset") or "").lower()
        if not symbol:
            continue

        momentum_score = float(item.get("momentum_score", item.get("score", 0.0) or 0.0))
        meta_score = float(item.get("meta_score", item.get("meta", 0.0) or 0.0))

        result[symbol] = AssetInputs(
            symbol=symbol,
            momentum_score=momentum_score,
            meta_score=meta_score,
        )

    logger.info("[%s] Momentum scores chargés pour %d assets.", LOGGER_NAME, len(result))
    return result


def _load_sentiment() -> Dict[str, float]:
    """
    Charge sentiment_overview.json et retourne un dict symbol -> sentiment (0..1).

    Formats gérés :
    1) Dict avec "assets":
       {
         "global_sentiment": 0.51,
         "assets": {
           "bitcoin": {"sentiment": 0.55, ...},
           ...
         }
       }

    2) Dict simple de symboles:
       {
         "bitcoin": {"sentiment": 0.55, ...},
         ...
       }

    3) Liste :
       [
         {"symbol": "bitcoin", "sentiment": 0.55, ...},
         ...
       ]
    """
    path = MARKET_DIR / "sentiment_overview.json"
    data = load_json_file(path, default={}) or {}
    global_sent = 0.5

    if isinstance(data, dict):
        global_sent = float(data.get("global_sentiment", 0.5))
        assets_data = data.get("assets")
        if assets_data is None:
            # Peut-être directement un dict de symboles
            assets_data = data
    else:
        assets_data = data

    sentiments: Dict[str, float] = {}

    if isinstance(assets_data, dict):
        for symbol, info in assets_data.items():
            if not isinstance(info, dict):
                continue
            try:
                sentiments[str(symbol).lower()] = float(info.get("sentiment", global_sent))
            except Exception:
                sentiments[str(symbol).lower()] = global_sent

    elif isinstance(assets_data, list):
        for item in assets_data:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or item.get("asset") or "").lower()
            if not symbol:
                continue
            try:
                sentiments[symbol] = float(item.get("sentiment", global_sent))
            except Exception:
                sentiments[symbol] = global_sent

    logger.info(
        "[%s] Sentiment chargé pour %d assets (global_sent=%.2f).",
        LOGGER_NAME,
        len(sentiments),
        global_sent,
    )
    return sentiments


def _load_price_action_features() -> Dict[str, Dict[str, Any]]:
    """
    Charge price_action_features.json (si présent) et retourne symbol -> features dict.

    Formats possibles :
    1) {
         "assets": [ {"symbol": "...", "ret_1d": ..., "ret_7d": ...}, ... ]
       }
    2) Liste directe : [ {...}, {...} ]
    3) Dict de symboles : { "bitcoin": {...}, ... }
    """
    path = ANALYSIS_DIR / "price_action_features.json"
    data = load_json_file(path, default={}) or {}

    assets_raw: List[Dict[str, Any]]
    if isinstance(data, list):
        assets_raw = data
    elif isinstance(data, dict):
        candidate = data.get("assets") or data.get("data")
        if isinstance(candidate, list):
            assets_raw = candidate
        elif isinstance(candidate, dict):
            assets_raw = list(candidate.values())
        else:
            assets_raw = list(data.values())
    else:
        assets_raw = []

    result: Dict[str, Dict[str, Any]] = {}
    for item in assets_raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or item.get("asset") or "").lower()
        if not symbol:
            continue
        result[symbol] = item

    logger.info(
        "[%s] Price action features chargés pour %d assets.",
        LOGGER_NAME,
        len(result),
    )
    return result


def _merge_inputs() -> Dict[str, AssetInputs]:
    """
    Fusionne momentum, sentiment et price_action en un dict symbol -> AssetInputs.
    On adopte la liste des symboles provenant des momentum_scores.
    """
    momentum = _load_momentum_scores()
    sentiments = _load_sentiment()
    pa_features = _load_price_action_features()

    for symbol, inp in momentum.items():
        sent = sentiments.get(symbol, 0.5)
        pa = pa_features.get(symbol, {})
        ret_1d = float(pa.get("ret_1d", 0.0) or 0.0)
        ret_7d = float(pa.get("ret_7d", 0.0) or 0.0)

        inp.sentiment_score = sent
        inp.ret_1d = ret_1d
        inp.ret_7d = ret_7d

    return momentum


# ---------------------------------------------------------------------------
# Logique de scoring Hype Cycle
# ---------------------------------------------------------------------------


def _compute_hype_score(inputs: AssetInputs) -> float:
    """
    Calcule un score de hype 0..100 à partir du momentum, meta et sentiment.
    Logique volontairement simple mais robuste.
    """
    base = inputs.momentum_score  # déjà sur 0..100 dans NSC

    # Ajustement sentiment
    if inputs.sentiment_score >= 0.7:
        base += 10.0
    elif inputs.sentiment_score <= 0.3:
        base -= 10.0

    # Ajustement sur ret_7d : fort pump récent => un peu plus de hype
    try:
        if inputs.ret_7d >= 0.15:
            base += 5.0
        elif inputs.ret_7d <= -0.10:
            base -= 5.0
    except Exception:
        pass

    # PETIT ajustement sur ret_1d (reversals)
    try:
        if inputs.ret_7d > 0.15 and inputs.ret_1d < -0.03:
            # Sortie de pump récente avec rouge aujourd'hui -> distribution potentielle
            base += 3.0
    except Exception:
        pass

    # Clamp 0..100
    if base < 0.0:
        base = 0.0
    if base > 100.0:
        base = 100.0
    return base


def _classify_stage(inputs: AssetInputs, hype_score: float) -> HypeResult:
    """
    Classe l'asset dans un stade de hype à partir du hype_score et des retours.
    Stades :
      - apathy
      - accumulation
      - early_trend
      - momentum
      - hype
      - distribution
    """
    reasons: List[str] = []
    stage: str

    # Distribution : hype score élevé, gros 7d vert, mais 1d rouge
    if hype_score >= 70 and inputs.ret_7d > 0.10 and inputs.ret_1d < -0.03:
        stage = "distribution"
        reasons.append("hype_score>=70, strong_7d_up, red_today")
    else:
        if hype_score < 25:
            stage = "apathy"
            reasons.append("hype_score<25")
        elif hype_score < 45:
            stage = "accumulation"
            reasons.append("25<=hype_score<45")
        elif hype_score < 60:
            stage = "early_trend"
            reasons.append("45<=hype_score<60")
        elif hype_score < 75:
            stage = "momentum"
            reasons.append("60<=hype_score<75")
        else:
            stage = "hype"
            reasons.append("hype_score>=75")

    # Risk flag
    if stage in ("hype", "distribution"):
        risk_flag = "risk"
    elif stage == "momentum":
        risk_flag = "watch"
    else:
        risk_flag = "normal"

    return HypeResult(
        symbol=inputs.symbol,
        stage=stage,
        hype_score=round(hype_score, 2),
        risk_flag=risk_flag,
        reasons=reasons,
    )


def compute_hype_cycle() -> Dict[str, Any]:
    """
    Calcule le Hype Cycle pour tous les assets disposant d'un momentum score.
    """
    logger.info("[%s] ROOT_DIR=%s, DATA_DIR=%s", LOGGER_NAME, ROOT_DIR, DATA_DIR)

    merged = _merge_inputs()
    results: List[HypeResult] = []

    for symbol, inp in merged.items():
        hype_score = _compute_hype_score(inp)
        res = _classify_stage(inp, hype_score)
        results.append(res)

    # Agrégation
    counts: Dict[str, int] = {}
    risk_counts = {"risk": 0, "watch": 0, "normal": 0}

    for r in results:
        counts[r.stage] = counts.get(r.stage, 0) + 1
        risk_counts[r.risk_flag] = risk_counts.get(r.risk_flag, 0) + 1

    nb_assets = len(results)
    nb_hype = counts.get("hype", 0)
    nb_distribution = counts.get("distribution", 0)

    if nb_assets == 0:
        global_comment = "aucun asset disponible pour le Hype Cycle (momentum_scores.json vide ?)"
    elif nb_hype + nb_distribution == 0:
        global_comment = "aucun asset en hype/distribution (régime narratif sain)"
    elif nb_hype + nb_distribution <= max(1, nb_assets // 4):
        global_comment = "quelques actifs en hype/distribution (surveiller mais ok)"
    else:
        global_comment = "plusieurs actifs en hype/distribution (risque de surchauffe)"

    overview = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nb_assets": nb_assets,
        "counts": counts,
        "risk_counts": risk_counts,
        "nb_hype": nb_hype,
        "nb_distribution": nb_distribution,
        "global_comment": global_comment,
        "assets": [
            {
                "symbol": r.symbol,
                "stage": r.stage,
                "hype_score": r.hype_score,
                "risk_flag": r.risk_flag,
                "reasons": r.reasons,
            }
            for r in sorted(results, key=lambda x: x.hype_score, reverse=True)
        ],
    }

    return overview


# ---------------------------------------------------------------------------
# Sauvegarde & main
# ---------------------------------------------------------------------------


def save_hype_cycle(overview: Dict[str, Any]) -> Path:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSIS_DIR / "hype_cycle_overview.json"
    save_json_file(out_path, overview)
    logger.info(
        "[%s] hype_cycle_overview.json sauvegardé (%s, nb_assets=%d).",
        LOGGER_NAME,
        out_path,
        overview.get("nb_assets", 0),
    )
    return out_path


def main() -> None:
    overview = compute_hype_cycle()
    save_hype_cycle(overview)


if __name__ == "__main__":
    main()
