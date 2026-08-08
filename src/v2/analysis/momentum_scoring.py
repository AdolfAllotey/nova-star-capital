from __future__ import annotations
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes & configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(get_data_dir()).resolve()

# Seuils de scoring momentum
MIN_META_FALLBACK = 30.0       # comportement legacy (sans early pump)
MIN_META_WITH_PUMP = 40.0      # règle Saison 2.5 quand early_pump dispo
EARLY_PUMP_MIN = 0.6           # early_pump_score minimal

MOMENTUM_FILE = DATA_DIR / "analysis" / "momentum_scores.json"
CANDIDATES_FILE = DATA_DIR / "analysis" / "momentum_candidates.json"
OHLCV_FILE = DATA_DIR / "market" / "ohlcv_combined.json"
SENTIMENT_FILE = DATA_DIR / "market" / "sentiment_overview.json"


# ---------------------------------------------------------------------------
# Helpers de chargement
# ---------------------------------------------------------------------------

def _load_ohlcv(data_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    Charge ohlcv_combined.json et normalise sous la forme:
    { "bitcoin": [ {"high":..,"low":..,"close":..}, ... ], ... }

    Formats supportés en entrée :
    - dict: symbol -> list[bar]
    - dict: symbol -> {"candles": [bar, ...]}
    - dict: symbol -> {"high":[...], "low":[...], "close":[...]}  (reconstruit des barres)
    - list: [{symbol: ..., ...}, ...]
    """
    path = data_dir / "market" / "ohlcv_combined.json"
    raw = load_json_file(path, default={})
    raw = ohlcv_v2_to_legacy_rows(raw)

    by_symbol: Dict[str, List[Dict[str, Any]]] = {}

    # Cas dict par symbol
    if isinstance(raw, dict):
        for sym, v in raw.items():
            symbol = str(sym).lower().strip()
            if not symbol:
                continue

            # 1) symbol -> list[bar]
            if isinstance(v, list):
                by_symbol[symbol] = v
                continue

            # 2) symbol -> {"candles": [...]}
            if isinstance(v, dict) and isinstance(v.get("candles"), list):
                by_symbol[symbol] = v.get("candles") or []
                continue

            # 3) symbol -> {"high":[...], "low":[...], "close":[...]}
            if isinstance(v, dict) and all(k in v for k in ("high", "low", "close")):
                highs = v.get("high") or []
                lows = v.get("low") or []
                closes = v.get("close") or []
                if isinstance(highs, list) and isinstance(lows, list) and isinstance(closes, list):
                    bars: List[Dict[str, Any]] = []
                    for h, l, c in zip(highs, lows, closes):
                        bars.append({"high": h, "low": l, "close": c})
                    by_symbol[symbol] = bars
                    continue

        if by_symbol:
            return by_symbol

    # Cas liste d'entrées avec champ "symbol"
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            symbol = (row.get("symbol") or "").lower().strip()
            if not symbol:
                continue
            by_symbol.setdefault(symbol, []).append(row)
        return by_symbol

    logger.warning("[momentum_scoring] Format inattendu pour %s: type=%s", path, type(raw))
    return {}



def _load_early_pump_scores(data_dir: Path) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Charge les early_pump_score par symbole depuis market/sentiment_overview.json.

    Format attendu (résumé) :
    {
      "global": {
        "avg_sentiment": ...,
        "early_pump_max": ...,
        "early_pump_flag": ...
      },
      "symbols": [
        { "symbol": "bitcoin", "early_pump_score": 0.72, ... },
        ...
      ]
    }
    """
    data = load_json_file(SENTIMENT_FILE, default={})

    scores: Dict[str, float] = {}
    symbols = data.get("symbols") or []

    for entry in symbols:
        symbol = (entry.get("symbol") or "").lower().strip()
        score = entry.get("early_pump_score")
        if symbol and isinstance(score, (int, float)):
            scores[symbol] = float(score)

    global_info = data.get("global") or {}
    global_flag = global_info.get("early_pump_flag")
    global_max = global_info.get("early_pump_max", 0.0)

    logger.info(
        "[momentum_scoring] early_pump chargé: %d symbols, global_flag=%s, max=%.2f",
        len(scores),
        global_flag,
        global_max,
    )

    return scores, {
        "global_flag": global_flag,
        "early_pump_max": global_max,
        "nb_symbols_with_pump": len(scores),
    }


# ---------------------------------------------------------------------------
# Scoring momentum (simplifié mais cohérent)
# ---------------------------------------------------------------------------

def _compute_basic_momentum(candles: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calcule un score de momentum simplifié 0-100 à partir de l'historique OHLCV.

    Hypothèses:
    - candles triés par timestamp croissant (si ce n'est pas le cas, on trie).
    - on utilise quelques features simples :
      - variation 15m
      - variation 60m
      - distance à MA20
      - proximité du plus-haut 7j
    """
    if not candles or len(candles) < 5:
        return {
            "momentum_score": 50.0,
            "meta_score": 50.0,
            "ret_15m": 0.0,
            "ret_60m": 0.0,
            "distance_ma20": 0.0,
            "near_7d_high": 0.0,
        }
    # Tri : si les timestamps sont absents (None), on garde l'ordre d'entrée.
    def _ts(c: Dict[str, Any]) -> Any:
        return c.get("timestamp")

    try:
        ts_vals = [c.get("timestamp") for c in candles if isinstance(c, dict)]
        has_real_ts = any(t is not None for t in ts_vals)

        if has_real_ts:
            # fallback stable : (is_none, timestamp) évite les comparaisons None/None
            candles_sorted = sorted(
                candles,
                key=lambda c: (c.get("timestamp") is None, c.get("timestamp")),
            )
        else:
            candles_sorted = list(candles)
    except Exception:
        candles_sorted = list(candles)

    closes = [float(c.get("close", c.get("c", 0.0)) or 0.0) for c in candles_sorted]
    if not closes or all(v <= 0 for v in closes):
        return {
            "momentum_score": 50.0,
            "meta_score": 50.0,
            "ret_15m": 0.0,
            "ret_60m": 0.0,
            "distance_ma20": 0.0,
            "near_7d_high": 0.0,
        }

    last = closes[-1]
    n = len(closes)

    # Variation "15m" et "60m" approximatives (on prend quelques pas en arrière)
    idx_15 = max(0, n - 4)
    idx_60 = max(0, n - 12)

    ret_15m = (last - closes[idx_15]) / closes[idx_15] if closes[idx_15] > 0 else 0.0
    ret_60m = (last - closes[idx_60]) / closes[idx_60] if closes[idx_60] > 0 else 0.0

    # MA20
    window_ma = closes[-20:] if n >= 20 else closes
    ma20 = sum(window_ma) / len(window_ma) if window_ma else last
    distance_ma20 = (last - ma20) / ma20 if ma20 > 0 else 0.0

    # Plus-haut 7j (ou tout l'historique dispo)
    high_7d = max(closes)
    near_7d_high = (last / high_7d) if high_7d > 0 else 0.0

    # Normalisation rudimentaire vers 0-100
    def _clip(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    # On pondère les différents critères
    s_ret_15 = _clip(ret_15m * 100, -50, 50)      # -50 à 50
    s_ret_60 = _clip(ret_60m * 50, -50, 50)       # -50 à 50
    s_ma20 = _clip(distance_ma20 * 100, -50, 50)  # -50 à 50
    s_high = _clip((near_7d_high - 0.9) * 200, -50, 50)  # proche du plus haut → >0

    raw_score = 0.35 * s_ret_15 + 0.35 * s_ret_60 + 0.2 * s_ma20 + 0.1 * s_high
    # raw_score est approximativement dans [-50, 50] → on mappe vers [0, 100]
    momentum_score = _clip(raw_score + 50.0, 0.0, 100.0)

    # Pour l’instant, meta_score == momentum_score (on pourra raffiner plus tard)
    meta_score = momentum_score

    return {
        "momentum_score": float(momentum_score),
        "meta_score": float(meta_score),
        "ret_15m": float(ret_15m),
        "ret_60m": float(ret_60m),
        "distance_ma20": float(distance_ma20),
        "near_7d_high": float(near_7d_high),
    }


# ================================
# NSC_SCORING_V2_HELPERS BEGIN
# ================================
def _nsc_safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

def _nsc_clip(x, lo=0.0, hi=100.0):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return max(lo, min(hi, x))

def _nsc_norm_0_100(x, lo, hi):
    x = _nsc_safe_float(x, lo)
    if hi <= lo:
        return 0.0
    return _nsc_clip((x - lo) / (hi - lo) * 100.0, 0.0, 100.0)

def _nsc_build_meta_score_v2(
    ret_15m=None,
    ret_60m=None,
    vol_ratio=None,
    distance_ma20=None,
    sentiment_score=None,
    early_pump_score=None,
    volume_spike=None,
    risk_mode=None,
    correlation_gate_active=None,
):
    ret_15m = _nsc_safe_float(ret_15m, 0.0)
    ret_60m = _nsc_safe_float(ret_60m, 0.0)
    vol_ratio = _nsc_safe_float(vol_ratio, 1.0)
    distance_ma20 = _nsc_safe_float(distance_ma20, 0.0)
    sentiment_score = _nsc_safe_float(sentiment_score, 0.0)
    early_pump_score = _nsc_safe_float(early_pump_score, 0.0)
    volume_spike = _nsc_safe_float(volume_spike, vol_ratio)

    momentum_15 = _nsc_norm_0_100(ret_15m, -5.0, 10.0)
    momentum_60 = _nsc_norm_0_100(ret_60m, -10.0, 20.0)
    momentum = 0.45 * momentum_15 + 0.55 * momentum_60

    volume = _nsc_norm_0_100(vol_ratio, 0.5, 3.0)
    structure = _nsc_norm_0_100(distance_ma20, -10.0, 15.0)
    sentiment = _nsc_norm_0_100(sentiment_score, -1.0, 1.0)

    base = (
        momentum * 0.40
        + volume * 0.20
        + sentiment * 0.20
        + structure * 0.20
    )

    bonus = 0.0
    malus = 0.0

    if momentum >= 80:
        bonus += 15.0
    elif momentum >= 70:
        bonus += 8.0

    if volume_spike >= 2.5:
        bonus += 10.0
    elif volume_spike >= 1.8:
        bonus += 5.0

    if sentiment_score >= 0.60:
        bonus += 10.0
    elif sentiment_score >= 0.40:
        bonus += 5.0

    if early_pump_score >= 0.70:
        bonus += 10.0
    elif early_pump_score >= 0.50:
        bonus += 5.0

    if risk_mode in {"reduced", "risk_off"}:
        malus += 10.0

    if bool(correlation_gate_active):
        malus += 10.0

    final_score = _nsc_clip(base + bonus - malus, 0.0, 100.0)

    return {
        "momentum_component": round(momentum, 4),
        "volume_component": round(volume, 4),
        "sentiment_component": round(sentiment, 4),
        "structure_component": round(structure, 4),
        "bonus": round(bonus, 4),
        "malus": round(malus, 4),
        "meta_score_v2": round(final_score, 4),
    }
# ================================
# NSC_SCORING_V2_HELPERS END
# ================================

# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------


def _load_symbol_sentiment_scores(data_dir: Path) -> Dict[str, float]:
    """
    Safe fallback helper.
    Returns per-symbol sentiment scores when available, otherwise {}.
    """
    candidates = [
        data_dir / "market" / "sentiment_overview.json",
        data_dir / "analysis" / "sentiment_overview.json",
        data_dir / "sentiment_overview.json",
    ]

    out: Dict[str, float] = {}

    for path in candidates:
        raw = load_json_file(path, default=None)
        if not raw:
            continue

        if isinstance(raw, dict):
            items = raw.get("items") or raw.get("symbols") or raw.get("scores") or raw
            if isinstance(items, list):
                for row in items:
                    if not isinstance(row, dict):
                        continue
                    sym = str(row.get("symbol") or row.get("token") or "").lower().strip()
                    val = row.get("sentiment_score") or row.get("avg_sentiment") or row.get("score")
                    try:
                        if sym and val is not None:
                            out[sym] = float(val)
                    except Exception:
                        pass

            elif isinstance(items, dict):
                for sym, payload in items.items():
                    try:
                        if isinstance(payload, dict):
                            val = payload.get("sentiment_score") or payload.get("avg_sentiment") or payload.get("score")
                        else:
                            val = payload
                        if val is not None:
                            out[str(sym).lower().strip()] = float(val)
                    except Exception:
                        pass

        if out:
            return out

    return {}


def compute_momentum_scores(data_dir: Path | None = None) -> Dict[str, Any]:
    """
    Calcule les scores de momentum et les candidats, en intégrant early_pump_score.

    - Lit ohlcv_combined.json
    - Calcule un momentum_score 0-100 et meta_score (pour l’instant identique)
    - Lit sentiment_overview.json pour récupérer early_pump_score par symbole
    - Applique la règle:
        * si early_pump_data dispo:
            - si symbole a early_pump_score → candidat si meta >= 70 et pump >= 0.6
            - sinon → fallback meta >= 60
        * si aucune early_pump_data → legacy meta >= 60
    """
    if data_dir is None:
        data_dir = DATA_DIR

    logger.info("[momentum_scoring] DATA_DIR sélectionné: %s", data_dir)

    ohlcv_by_symbol = _load_ohlcv(data_dir)
    if not ohlcv_by_symbol:
        logger.warning(
            "[momentum_scoring] Aucun OHLCV trouvé dans %s – pas de scores générés.",
            OHLCV_FILE,
        )
        result = {
            "stats": {
                "nb_assets": 0,
                "nb_candidates": 0,
                "min_meta_fallback": MIN_META_FALLBACK,
                "min_meta_with_pump": MIN_META_WITH_PUMP,
                "early_pump_min": EARLY_PUMP_MIN,
                "has_early_pump_data": False,
            },
            "scores": {},
        }
        save_json_file(MOMENTUM_FILE, result)
        save_json_file(CANDIDATES_FILE, [])
        return result

    early_pump_scores, early_pump_meta = _load_early_pump_scores(data_dir)
    sentiment_scores = _load_symbol_sentiment_scores(data_dir)

    risk_limits = load_json_file(data_dir / "trading" / "risk_limits.json", default={}) or {}
    risk_mode = str(risk_limits.get("mode") or risk_limits.get("risk_mode") or "normal").lower()

    correlation_gate_state = load_json_file(
        data_dir / "state" / "correlation_gate_state.json",
        default={}
    ) or {}
    correlation_gate_active = bool(correlation_gate_state.get("active", False))

    risk_limits = load_json_file(data_dir / "trading" / "risk_limits.json", default={}) or {}
    risk_mode = str(
        risk_limits.get("mode")
        or risk_limits.get("risk_mode")
        or "normal"
    ).lower()

    correlation_gate_state = load_json_file(
        data_dir / "state" / "correlation_gate_state.json",
        default={}
    ) or {}
    correlation_gate_active = bool(correlation_gate_state.get("active", False))
    has_pump_data = len(early_pump_scores) > 0

    scores: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []

    for symbol, candles in ohlcv_by_symbol.items():
        symbol_norm = symbol.lower().strip()
        m = _compute_basic_momentum(candles)
        # ================================
        # NSC_V3_OVERRIDE_META
        # ================================
        legacy_meta_score = float(m["meta_score"])

        sentiment_score = sentiment_scores.get(symbol)
        sentiment_score = float(sentiment_score) if sentiment_score is not None else 0.0

        early_pump = early_pump_scores.get(symbol)
        early_pump = float(early_pump) if early_pump is not None else 0.0

        v4 = _nsc_build_meta_score_v2(
            ret_15m=m.get("ret_15m", 0.0),
            ret_60m=m.get("ret_60m", 0.0),
            vol_ratio=m.get("vol_ratio", 1.0),
            distance_ma20=m.get("distance_ma20", 0.0),
            sentiment_score=sentiment_score,
            early_pump_score=early_pump,
            volume_spike=m.get("vol_ratio", 1.0),
            risk_mode=risk_mode,
            correlation_gate_active=correlation_gate_active,
        )

        overlay_score = float(v4.get("meta_score_v2", legacy_meta_score))

        # V4 hybride : on conserve la hiérarchie legacy
        # et on applique seulement un overlay partiel
        meta_score = round(legacy_meta_score * 0.7 + overlay_score * 0.3, 4)

        bonus = float(v4.get("bonus", 0.0) or 0.0)
        malus = float(v4.get("malus", 0.0) or 0.0)
        momentum_component = float(v4.get("momentum_component", 0.0) or 0.0)
        volume_component = float(v4.get("volume_component", 0.0) or 0.0)
        structure_component = float(v4.get("structure_component", 0.0) or 0.0)
        sentiment_component = float(v4.get("sentiment_component", 0.0) or 0.0)

        

        early_pump = early_pump_scores.get(symbol_norm)

        # ------------------------------------------------------------------
        # Gating momentum + early_pump (Saison 2.5)
        # ------------------------------------------------------------------
        if has_pump_data:
            if early_pump is not None:
                # Règle stricte: momentum fort + early pump confirmé
                is_candidate = (
                    meta_score >= MIN_META_WITH_PUMP and early_pump >= EARLY_PUMP_MIN
                )
                gating_reason = (
                    f"meta={meta_score:.2f}>= {MIN_META_WITH_PUMP} "
                    f"et early_pump={early_pump:.2f}>= {EARLY_PUMP_MIN}"
                    if is_candidate
                    else (
                        f"rejeté: meta={meta_score:.2f}, early_pump="
                        f"{'None' if early_pump is None else f'{early_pump:.2f}'}"
                    )
                )
            else:
                # Pas de data early_pump pour ce symbole → fallback momentum seul
                is_candidate = meta_score >= MIN_META_FALLBACK
                gating_reason = (
                    f"fallback sans early_pump, meta={meta_score:.2f}"
                    f">={MIN_META_FALLBACK}"
                    if is_candidate
                    else f"rejeté (fallback): meta={meta_score:.2f}"
                )
        else:
            # Aucun fichier / aucune data early pump → comportement legacy
            is_candidate = meta_score >= MIN_META_FALLBACK
            gating_reason = (
                f"legacy sans sentiment, meta={meta_score:.2f}>={MIN_META_FALLBACK}"
                if is_candidate
                else f"rejeté: meta={meta_score:.2f}"
            )

        # Entrée complète pour momentum_scores.json
        score_entry: Dict[str, Any] = {
            "symbol": symbol_norm,
            "momentum_score": m["momentum_score"],
            "meta_score": meta_score,
            "legacy_meta_score": legacy_meta_score,
            "ret_15m": m["ret_15m"],
            "ret_60m": m["ret_60m"],
            "distance_ma20": m["distance_ma20"],
            "near_7d_high": m["near_7d_high"],
            "risk_mode": risk_mode,
            "correlation_gate_active": correlation_gate_active,
            "early_pump_score": early_pump,
            "early_pump_gating_reason": gating_reason,
        }

        # On peut définir un petit "regime" de momentum à titre indicatif
        if score_entry["momentum_score"] >= 70:
            score_entry["momentum_regime"] = "strong"
        elif score_entry["momentum_score"] >= 55:
            score_entry["momentum_regime"] = "medium"
        elif score_entry["momentum_score"] >= 45:
            score_entry["momentum_regime"] = "neutral"
        else:
            score_entry["momentum_regime"] = "weak"

        scores.append(score_entry)

        # Candidats filtrés pour momentum_candidates.json
        if is_candidate:
            candidates.append(
                {
                    "symbol": symbol_norm,
                    "meta_score": meta_score,
                    "legacy_meta_score": legacy_meta_score,
                    "momentum_score": m["momentum_score"],
                    "early_pump_score": early_pump,
                    "momentum_regime": score_entry["momentum_regime"],
                }
            )

    stats = {
        "nb_assets": len(scores),
        "nb_candidates": len(candidates),
        "min_meta_fallback": MIN_META_FALLBACK,
        "min_meta_with_pump": MIN_META_WITH_PUMP,
        "early_pump_min": EARLY_PUMP_MIN,
        "has_early_pump_data": has_pump_data,
        "early_pump": early_pump_meta,
    }

    # Convertit la liste 'scores' en dict: symbol -> score (format objet attendu downstream)
    score_map: Dict[str, Dict[str, Any]] = {}
    for row in scores:
        if isinstance(row, dict) and row.get("symbol"):
            score_map[str(row["symbol"]).lower().strip()] = row
    result = {
        "stats": stats,
        "scores": score_map,
    }

    save_json_file(MOMENTUM_FILE, result)
    save_json_file(CANDIDATES_FILE, candidates)

    logger.info(
        "Calcul de momentum terminé: %d assets, %d candidats (fallback=%s, pump_data=%s)",
        stats["nb_assets"],
        stats["nb_candidates"],
        MIN_META_FALLBACK,
        has_pump_data,
    )

    logger.info(
        "Scores de momentum sauvegardés (%s) et candidats (%s)",
        str(MOMENTUM_FILE),
        str(CANDIDATES_FILE),
    )

    return result


def main() -> None:
    compute_momentum_scores(DATA_DIR)


if __name__ == "__main__":
    main()


# ================================
# NSC_V3_SENTIMENT_HELPER
# ================================
def _load_symbol_sentiment_scores(data_dir):
    from src.v2.utils.file_utils import load_json_file

    data = load_json_file(data_dir / "market" / "sentiment_overview.json", default={}) or {}
    out = {}

    for entry in (data.get("symbols") or []):
        symbol = str(entry.get("symbol") or "").lower()
        val = entry.get("sentiment_score") or entry.get("avg_sentiment") or entry.get("score")
        try:
            out[symbol] = float(val)
        except:
            continue

    return out
