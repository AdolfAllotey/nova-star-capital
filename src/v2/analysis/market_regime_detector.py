# src/v2/analysis/market_regime_detector.py
from __future__ import annotations

import os
import time
from datetime import datetime, timezone  # NSC_MARKET_REGIME_CANONICAL_WRITE_V1
import secrets  # NSC_MARKET_REGIME_RUN_ID_V1
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

logger = get_logger("market_regime_detector")


# ---------------------------------------------------------------------------
# Paths / env
# ---------------------------------------------------------------------------

def get_env() -> str:
    return os.environ.get("NSC_ENV", "PREPROD")


def get_data_dir() -> Path:
    root = os.environ.get("NSC_ROOT_DIR") or os.getcwd()
    return Path(os.environ.get("NSC_DATA_DIR", str(Path(root) / "data")))


def now_ts() -> int:
    return int(time.time())


def _analysis_paths(data_dir: Path) -> Dict[str, Path]:
    analysis_dir = data_dir / "analysis"
    return {
        "analysis_dir": analysis_dir,
        "sentiment": data_dir / "sentiment_overview.json",
        "market_conditions": analysis_dir / "market_conditions_engine_pro.json",
        "volatility_state": analysis_dir / "volatility_state_machine_pro.json",
        "coherence": analysis_dir / "market_coherence_engine_pro.json",
        "meta_score": analysis_dir / "meta_score_engine_pro.json",
        "out": analysis_dir / "market_regime_detector.json",
        "out_canon": analysis_dir / "market_regime.json",  # NSC_MARKET_REGIME_CANONICAL_OUTPUT_V1

        "state": data_dir / "state" / "market_regime_state.json",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _to_float(x: Any, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _score_01_from_100(score_100: Any, default_01: float = 0.50) -> float:
    s = _to_float(score_100, default_01 * 100.0)
    return _clamp(s / 100.0, 0.0, 1.0)


def _safe_get(d: Any, path: List[str], default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _compute_meta_avg(meta: Dict[str, Any]) -> Optional[float]:
    """
    meta_score_engine_pro.json peut être :
    - {"avg": 62.3, ...}
    - {"assets":[{"symbol":"BTC","score":...}, ...], "avg_score": ...}
    - ou autre structure
    On essaye plusieurs patterns, sinon None.
    """
    if not isinstance(meta, dict) or not meta:
        return None

    for key in ("avg", "avg_score", "avgScore", "meta_avg"):
        v = meta.get(key)
        if isinstance(v, (int, float)):
            return float(v)

    # assets list -> moyenne
    assets = meta.get("assets")
    if isinstance(assets, list) and assets:
        vals = []
        for a in assets:
            if isinstance(a, dict):
                for k in ("score", "meta_score", "value"):
                    if isinstance(a.get(k), (int, float)):
                        vals.append(float(a[k]))
                        break
        if vals:
            return sum(vals) / len(vals)

    return None


def _risk_mode_from_global_flag(flag: str) -> str:
    f = (flag or "").lower().strip()
    if f in ("danger", "emergency"):
        return "risk_off"
    if f == "caution":
        return "reduced"
    return "normal"


# ---------------------------------------------------------------------------
# Voting logic (simple, stable, extensible)
# ---------------------------------------------------------------------------

def decide_regime(
    sentiment_avg: float,
    market_conditions_regime: str,
    market_conditions_score_100: float,
    coherence_01: float,
    meta_avg_100: Optional[float],
) -> Tuple[str, str, Dict[str, int], List[str], Dict[str, Any]]:
    """
    Retourne:
      regime: bull|bear|neutral
      risk_mode: normal|reduced|risk_off
      votes: dict
      reasons: list[str]
      inputs: dict (exposé)
    """
    reasons: List[str] = []
    votes = {"bull": 0, "bear": 0, "neutral": 0}

    # 1) Sentiment vote
    if sentiment_avg >= 0.25:
        votes["bull"] += 1
        reasons.append(f"sentiment_avg={sentiment_avg:.3f} >= 0.25")
    elif sentiment_avg <= -0.15:
        votes["bear"] += 1
        reasons.append(f"sentiment_avg={sentiment_avg:.3f} <= -0.15")
    else:
        votes["neutral"] += 1
        reasons.append(f"sentiment_avg={sentiment_avg:.3f} in neutral band")

    # 2) Market conditions vote (regime + score)
    mc_reg = (market_conditions_regime or "neutral").lower().strip()
    if mc_reg in ("bull", "risk_on"):
        votes["bull"] += 1
        reasons.append(f"market_conditions_regime={mc_reg}")
    elif mc_reg in ("bear", "risk_off"):
        votes["bear"] += 1
        reasons.append(f"market_conditions_regime={mc_reg}")
    else:
        # si neutral, on regarde le score
        if market_conditions_score_100 >= 60:
            votes["bull"] += 1
            reasons.append(f"market_conditions_score={market_conditions_score_100:.2f} >= 60")
        elif market_conditions_score_100 <= 40:
            votes["bear"] += 1
            reasons.append(f"market_conditions_score={market_conditions_score_100:.2f} <= 40")
        else:
            votes["neutral"] += 1
            reasons.append(f"market_conditions_regime={mc_reg}")

    # 3) Coherence vote
    # coherence_01 proche 0.5 => neutre ; >0.65 => bull ; <0.35 => bear
    if coherence_01 >= 0.65:
        votes["bull"] += 1
        reasons.append(f"coherence_01={coherence_01:.3f} >= 0.65")
    elif coherence_01 <= 0.35:
        votes["bear"] += 1
        reasons.append(f"coherence_01={coherence_01:.3f} <= 0.35")
    else:
        votes["neutral"] += 1
        reasons.append(f"coherence_01={coherence_01:.3f} in neutral band")

    # 4) Meta-score vote (si disponible)
    if meta_avg_100 is None:
        reasons.append("meta_avg missing")
    else:
        if meta_avg_100 >= 60:
            votes["bull"] += 1
            reasons.append(f"meta_avg={meta_avg_100:.2f} >= 60")
        elif meta_avg_100 <= 40:
            votes["bear"] += 1
            reasons.append(f"meta_avg={meta_avg_100:.2f} <= 40")
        else:
            votes["neutral"] += 1
            reasons.append(f"meta_avg={meta_avg_100:.2f} in neutral band")

    # Décision finale : majorité simple ; en cas d'égalité -> neutral
    max_vote = max(votes.values())
    winners = [k for k, v in votes.items() if v == max_vote]
    regime = winners[0] if len(winners) == 1 else "neutral"

    # risk_mode : si market_conditions score trop faible => reduced ; sinon normal
    risk_mode = "normal"
    if market_conditions_score_100 < 45:
        risk_mode = "reduced"

    inputs = {
        "sentiment": {"avg_score": sentiment_avg},
        "market_conditions": {"regime": mc_reg, "score": float(market_conditions_score_100)},
        "coherence": {"score": float(coherence_01)},
        "meta_score": {"avg": meta_avg_100},
    }

    return regime, risk_mode, votes, reasons, inputs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    data_dir = get_data_dir()
    env = get_env()
    paths = _analysis_paths(data_dir)

    ensure_dir(str(paths["analysis_dir"]))
    ensure_dir(str((data_dir / "state")))

    # Load inputs
    sentiment = load_json_file(paths["sentiment"], default={})
    market_conditions = load_json_file(paths["market_conditions"], default={})
    coherence = load_json_file(paths["coherence"], default={})
    meta_score = load_json_file(paths["meta_score"], default={})

    sentiment_avg = _to_float(_safe_get(sentiment, ["sentiment", "avg_score"], 0.0), 0.0)
    sentiment_bucket = str(_safe_get(sentiment, ["sentiment", "bucket"], "neutral") or "neutral")
    sentiment_total = int(_safe_get(sentiment, ["counts", "total"], 0) or 0)
    sentiment_by_source = _safe_get(sentiment, ["counts", "by_source"], {}) or {}

    mc_regime = str(market_conditions.get("regime", "neutral") or "neutral")
    mc_score = _to_float(market_conditions.get("score", 50.0), 50.0)
    mc_global_flag = str(market_conditions.get("global_flag", "unknown") or "unknown")

    coherence_score_01 = 0.50
    # ton coherence engine peut avoir "score" en 0..1 ou 0..100 : on supporte les deux
    coh_raw = coherence.get("score", 50.0)
    coh_val = _to_float(coh_raw, 50.0)
    coherence_score_01 = coh_val if coh_val <= 1.0 else _score_01_from_100(coh_val, 0.50)

    meta_avg = _compute_meta_avg(meta_score)

    # Decide
    logger.info("[market_regime_detector] Calcul du régime de marché...")
    regime, risk_mode, votes, reasons, inputs_core = decide_regime(
        sentiment_avg=sentiment_avg,
        market_conditions_regime=mc_regime,
        market_conditions_score_100=mc_score,
        coherence_01=coherence_score_01,
        meta_avg_100=meta_avg,
    )

    # Global override via market_conditions flag
    risk_mode_flag = _risk_mode_from_global_flag(mc_global_flag)
    if risk_mode_flag == "risk_off":
        # priorité maximale
        risk_mode = "risk_off"
        if "market_conditions_global_flag=danger/emergency -> risk_off" not in reasons:
            reasons.append("market_conditions_global_flag=danger/emergency -> risk_off")
    elif risk_mode_flag == "reduced" and risk_mode == "normal":
        risk_mode = "reduced"
        reasons.append("market_conditions_global_flag=caution -> reduced")

    out = {
        "generated_at": now_ts(),
        "timestamp": now_ts(),
        "env": env,
        "writer": "market_regime_detector",  # NSC_MARKET_REGIME_RUN_ID_V1
        "run_id": (str(os.environ.get("NSC_RUN_ID") or "").strip() or (str(int(time.time()*1000)) + "-" + secrets.token_hex(4))),
        "source": "market_regime_detector",
        "writer": "market_regime_detector",
        "run_id": (str(os.environ.get("NSC_RUN_ID") or "").strip() or None),
        "regime": regime,
        "risk_mode": risk_mode,
        "votes": votes,
        "reasons": reasons,
        "inputs": {
            "sentiment": {
                "avg_score": sentiment_avg,
                "bucket": sentiment_bucket,
                "total": sentiment_total,
                "by_source": sentiment_by_source,
            },
            "market_conditions": {
                "regime": mc_regime,
                "score": mc_score,
                "global_flag": mc_global_flag,
            },
            "coherence": {"score": coherence_score_01},
            "meta_score": {"avg": meta_avg},
        },
    }

    save_json_file(paths["out"], out)
    # NSC_MARKET_REGIME_CANONICAL_OUTPUT_V1
    try:
        save_json_file(paths["out_canon"], out)
    except Exception:
        logger.exception("[market_regime_detector] failed to write canonical market_regime.json")
    state = {
        "updated_at": now_ts(),
        "env": env,
        "regime": regime,
        "risk_mode": risk_mode,
    }
    # NSC_MARKET_REGIME_CANONICAL_WRITE_V1
    # Canonical market_regime.json write
    try:
        if isinstance(state, dict):
            _rid = str(os.environ.get('NSC_RUN_ID') or '').strip()
            if not _rid:
                _rid = f"mr-1767124938-ba451831"
            state.setdefault('writer', 'market_regime_detector')
            state['run_id'] = _rid
            state.setdefault('env', env)
            state.setdefault('generated_at', now_ts())
            state.setdefault('timestamp', now_ts())
            state.setdefault('timestamp_iso', datetime.now(timezone.utc).isoformat())
            save_json_file(paths['out_canon'], state)
    except Exception:
        logger.exception('[market_regime_detector] canonical write failed')
    save_json_file(paths["state"], state)
    logger.info(
        "[market_regime_detector] OK regime=%s risk_mode=%s -> %s",
        regime, risk_mode, str(paths["out"]),
    )


if __name__ == "__main__":
    main()
