"""
NSC Trading — Market Coherence Engine V1.

Coherence measures compatibility between three independent market dimensions:

1. Breadth:
   structural market participation (% above MA200).
2. Volatility:
   tactical cross-asset stress.
3. Correlation:
   systemic cross-asset concentration.

Important semantic contract:
- coherence is NOT market direction;
- coherence is NOT a second market-regime engine;
- scores from upstream engines are NOT averaged;
- Market Conditions and Market Regime are deliberately excluded to avoid
  duplicate voting;
- missing/stale/invalid authority => unknown / caution / 50;
- a coherent defensive configuration can have high coherence.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.v2.utils.file_utils import get_data_dir, save_json_file

try:
    from src.v2.utils.logger import get_logger
except ImportError:
    from src.v2.logger import get_logger  # type: ignore

from src.v2.utils.event_bus import publish_event


logger = get_logger("market_coherence_engine_pro")


# G152_COHERENCE_V1_COMPATIBILITY_AUTHORITY
BREADTH_MAX_AGE_HOURS = 20.0
FUTURE_SKEW_HOURS = 5.0 / 60.0

BREADTH_STRONG = 0.60
BREADTH_WEAK = 0.40


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: Optional[datetime] = None) -> str:
    value = value or _utc_now()
    return value.astimezone(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        out = float(value)
        if out != out:
            return None
        return out
    except Exception:
        return None


def _parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_hours(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 3600.0


def _breadth_state(
    analysis_dir: Path,
    now: datetime,
) -> Tuple[bool, str, Dict[str, Any], str]:
    path = analysis_dir / "breadth.json"
    raw = _load_json(path)

    ts = raw.get("ts") or raw.get("timestamp") or raw.get("generated_at")
    age = _age_hours(ts, now)
    pct = _float(raw.get("breadth_pct_above_ma200"))
    usable = raw.get("tickers_usable")
    total = raw.get("tickers_total")
    status = str(raw.get("status") or "").strip().lower()

    valid = (
        bool(raw)
        and status == "ok"
        and pct is not None
        and 0.0 <= pct <= 1.0
        and age is not None
        and age >= -FUTURE_SKEW_HOURS
        and age <= BREADTH_MAX_AGE_HOURS
    )

    if not valid:
        state = "unknown"
        reason = (
            "Breadth unavailable/stale/invalid "
            f"(status={status or 'missing'}, age_hours={age}, pct={pct})."
        )
    elif pct >= BREADTH_STRONG:
        state = "supportive"
        reason = f"Breadth strong ({pct:.3f} above MA200)."
    elif pct <= BREADTH_WEAK:
        state = "defensive"
        reason = f"Breadth weak ({pct:.3f} above MA200)."
    else:
        state = "neutral"
        reason = f"Breadth neutral ({pct:.3f} above MA200)."

    meta = {
        "authority": "breadth",
        "path": str(path),
        "valid": valid,
        "state": state,
        "value": pct,
        "status": status or None,
        "timestamp": ts,
        "age_hours": round(age, 6) if age is not None else None,
        "max_age_hours": BREADTH_MAX_AGE_HOURS,
        "source": raw.get("source"),
        "universe": raw.get("universe"),
        "tickers_usable": usable,
        "tickers_total": total,
    }

    return valid, state, meta, reason


def _volatility_state(
    analysis_dir: Path,
    now: datetime,
) -> Tuple[bool, str, Dict[str, Any], str]:
    path = analysis_dir / "volatility_state_machine_pro.json"
    raw = _load_json(path)

    regime = str(raw.get("regime") or "").strip().lower()
    flag = str(
        raw.get("global_flag") or raw.get("flag") or ""
    ).strip().lower()

    source_fresh = raw.get("source_fresh") is True

    source_ts = (
        raw.get("source_generated_at")
        or raw.get("generated_at")
        or raw.get("timestamp")
    )
    age = _age_hours(source_ts, now)

    max_age = _float(raw.get("source_max_age_hours"))
    if max_age is None or max_age <= 0:
        max_age = 1.0

    valid = (
        bool(raw)
        and source_fresh
        and age is not None
        and age >= -FUTURE_SKEW_HOURS
        and age <= max_age
        and regime not in ("", "unknown")
    )

    if not valid:
        state = "unknown"
        reason = (
            "Volatility unavailable/stale/invalid "
            f"(regime={regime or 'missing'}, "
            f"source_fresh={source_fresh}, age_hours={age})."
        )
    elif regime == "panic" or flag == "risk_off":
        state = "defensive"
        reason = f"Volatility defensive ({regime}/{flag})."
    elif regime in ("stressed", "accelerating") or flag == "caution":
        state = "caution"
        reason = f"Volatility caution ({regime}/{flag})."
    elif regime == "calm" or flag == "supportive":
        state = "supportive"
        reason = f"Volatility supportive ({regime}/{flag})."
    else:
        state = "neutral"
        reason = f"Volatility neutral ({regime}/{flag})."

    meta = {
        "authority": "volatility_state",
        "path": str(path),
        "valid": valid,
        "state": state,
        "regime": regime or None,
        "global_flag": flag or None,
        "score": _float(raw.get("score")),
        "timestamp": raw.get("timestamp"),
        "source": raw.get("source"),
        "source_generated_at": source_ts,
        "source_fresh": source_fresh,
        "source_age_hours_runtime": (
            round(age, 6) if age is not None else None
        ),
        "source_max_age_hours": max_age,
        "writer": raw.get("writer"),
        "run_id": raw.get("run_id"),
    }

    return valid, state, meta, reason


def _correlation_state(
    analysis_dir: Path,
    now: datetime,
) -> Tuple[bool, str, Dict[str, Any], str]:
    path = analysis_dir / "correlation_regime.json"
    raw = _load_json(path)

    regime = str(raw.get("regime") or "").strip().lower()
    flag = str(raw.get("global_flag") or "").strip().lower()

    source_fresh = raw.get("source_fresh") is True
    source_ts = (
        raw.get("source_generated_at")
        or raw.get("generated_at")
        or raw.get("timestamp")
    )
    age = _age_hours(source_ts, now)

    max_age = _float(raw.get("source_max_age_hours"))
    if max_age is None or max_age <= 0:
        max_age = 1.0

    pair_count = raw.get("pair_count")
    if pair_count is None:
        pair_count = raw.get("nb_pairs")

    valid = (
        bool(raw)
        and source_fresh
        and age is not None
        and age >= -FUTURE_SKEW_HOURS
        and age <= max_age
        and regime not in ("", "unknown")
        and isinstance(pair_count, (int, float))
        and pair_count > 0
    )

    if not valid:
        state = "unknown"
        reason = (
            "Correlation unavailable/stale/invalid "
            f"(regime={regime or 'missing'}, "
            f"source_fresh={source_fresh}, age_hours={age}, "
            f"pairs={pair_count})."
        )
    elif regime == "panic" or flag == "risk_off":
        state = "defensive"
        reason = f"Correlation defensive ({regime}/{flag})."
    elif regime == "high_corr" or flag == "caution":
        state = "caution"
        reason = f"Correlation caution ({regime}/{flag})."
    elif regime == "diversified" or flag == "risk_on":
        state = "supportive"
        reason = f"Correlation supportive ({regime}/{flag})."
    else:
        state = "neutral"
        reason = f"Correlation neutral ({regime}/{flag})."

    meta = {
        "authority": "correlation",
        "path": str(path),
        "valid": valid,
        "state": state,
        "regime": regime or None,
        "global_flag": flag or None,
        "score": _float(raw.get("score")),
        "timestamp": raw.get("timestamp"),
        "source": raw.get("source"),
        "source_generated_at": source_ts,
        "source_fresh": source_fresh,
        "source_age_hours_runtime": (
            round(age, 6) if age is not None else None
        ),
        "source_max_age_hours": max_age,
        "pair_count": pair_count,
        "writer": raw.get("writer"),
        "run_id": raw.get("run_id"),
    }

    return valid, state, meta, reason


def _classify_compatibility(
    breadth: str,
    volatility: str,
    correlation: str,
) -> Tuple[str, str, float, str]:
    """
    Return:
      coherence_regime, global_flag, coherence_score, directional_context

    Score means AGREEMENT / COHERENCE, not risk appetite.
    """

    states = (breadth, volatility, correlation)

    if "unknown" in states:
        return "unknown", "caution", 50.0, "unknown"

    supportive = sum(s == "supportive" for s in states)
    defensive = sum(s == "defensive" for s in states)
    caution = sum(s == "caution" for s in states)
    neutral = sum(s == "neutral" for s in states)

    # Full directional agreement.
    if supportive == 3:
        return "coherent", "ok", 90.0, "supportive"

    if defensive == 3:
        return "coherent", "caution", 90.0, "defensive"

    # Two authorities agree and the third is merely neutral.
    if supportive == 2 and neutral == 1:
        return "coherent", "ok", 80.0, "supportive"

    if defensive == 2 and neutral == 1:
        return "coherent", "caution", 80.0, "defensive"

    # Two authorities agree while the third expresses caution.
    if supportive == 2 and caution == 1:
        return "mostly_coherent", "caution", 70.0, "supportive"

    if defensive == 2 and caution == 1:
        return "mostly_coherent", "caution", 75.0, "defensive"

    # Explicit supportive/defensive conflict is genuine divergence.
    if supportive > 0 and defensive > 0:
        return "divergent", "caution", 30.0, "mixed"

    # Caution combined with neutral is uncertainty rather than contradiction.
    if caution > 0 and supportive == 0 and defensive == 0:
        if caution >= 2:
            return "mostly_coherent", "caution", 65.0, "caution"
        return "mixed", "caution", 55.0, "caution"

    # One directional authority, remaining authorities neutral.
    if supportive == 1 and neutral == 2:
        return "mixed", "ok", 60.0, "supportive"

    if defensive == 1 and neutral == 2:
        return "mixed", "caution", 60.0, "defensive"

    # All neutral.
    if neutral == 3:
        return "coherent", "ok", 75.0, "neutral"

    return "mixed", "caution", 50.0, "mixed"


def build_coherence_state(
    data_dir: Path,
    env: str,
) -> Dict[str, Any]:
    now = _utc_now()
    analysis_dir = data_dir / "analysis"

    b_valid, b_state, b_meta, b_reason = _breadth_state(
        analysis_dir, now
    )
    v_valid, v_state, v_meta, v_reason = _volatility_state(
        analysis_dir, now
    )
    c_valid, c_state, c_meta, c_reason = _correlation_state(
        analysis_dir, now
    )

    all_valid = b_valid and v_valid and c_valid

    if all_valid:
        regime, global_flag, score, directional_context = (
            _classify_compatibility(
                b_state,
                v_state,
                c_state,
            )
        )
    else:
        regime = "unknown"
        global_flag = "caution"
        score = 50.0
        directional_context = "unknown"

    timestamp = _iso_utc(now)

    state: Dict[str, Any] = {
        "schema_version": 2,
        "timestamp": timestamp,
        "generated_at": timestamp,
        "env": env,
        "symbol": "global",
        "writer": "market_coherence_engine_pro",
        "run_id": (
            str(os.environ.get("NSC_RUN_ID") or "").strip()
            or f"anon-{secrets.token_hex(8)}"
        ),
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "score_semantics": "cross_authority_agreement_not_risk_appetite",
        "directional_context": directional_context,
        "source_fresh": all_valid,
        "authorities_required": 3,
        "authorities_valid": sum((b_valid, v_valid, c_valid)),
        "components": {
            "breadth": b_meta,
            "volatility": v_meta,
            "correlation": c_meta,
        },
        "metrics": {
            "breadth_state": b_state,
            "volatility_state": v_state,
            "correlation_state": c_state,
            "all_authorities_valid": all_valid,
        },
        "reasons": [
            b_reason,
            v_reason,
            c_reason,
            (
                "Coherence derived from compatibility states; "
                "upstream numeric scores are not averaged."
            ),
        ],
    }

    return state


def _severity(flag: str) -> str:
    if flag in ("danger", "critical", "risk_off"):
        return "critical"
    if flag in ("caution", "warning"):
        return "warning"
    return "info"


def main() -> None:
    data_dir = Path(get_data_dir())
    env = str(os.environ.get("NSC_ENV") or "PREPROD").strip()

    logger.info(
        "[market_coherence_engine_pro] DATA_DIR=%s env=%s",
        data_dir,
        env,
    )

    state = build_coherence_state(data_dir=data_dir, env=env)

    out_path = data_dir / "analysis" / "market_coherence_engine_pro.json"
    save_json_file(out_path, state)

    logger.info(
        "[market_coherence_engine_pro] regime=%s flag=%s "
        "score=%.2f direction=%s valid=%s/3",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
        state.get("directional_context"),
        state.get("authorities_valid"),
    )

    try:
        publish_event(
            event_type="market.coherence.state",
            source="market_coherence_engine_pro",
            severity=_severity(str(state.get("global_flag") or "")),
            payload=state,
        )
    except Exception:
        logger.exception(
            "[market_coherence_engine_pro] event publication failed"
        )


if __name__ == "__main__":
    main()
