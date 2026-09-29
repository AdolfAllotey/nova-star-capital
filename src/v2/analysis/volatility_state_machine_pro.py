from __future__ import annotations

import os
import time
import secrets  # NSC_VOLATILITY_RUN_ID_WRITER_V1
import math
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers env / data_dir
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Renvoie le dossier data de NSC.

    - Si NSC_DATA_DIR est défini : on l'utilise.
    - Sinon : 'data' relatif au cwd (/opt/nsc/app).
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    return Path(base).resolve()


def get_env() -> str:
    """Renvoie l'environnement courant ('PREPROD' par défaut)."""
    return os.getenv("NSC_ENV", "PREPROD")


# ---------------------------------------------------------------------------
# Dataclass & helpers
# ---------------------------------------------------------------------------

@dataclass
class VolatilityMetrics:
    realized_vol_20d: Optional[float]
    realized_vol_5d: Optional[float]
    implied_vol_index: Optional[float]
    vol_of_vol: Optional[float]
    cross_section_vol: Optional[float]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def load_volatility_metrics(raw: Any) -> VolatilityMetrics:
    """
    Charge les métriques de volatilité à partir d'une structure flexible.

    Structure recommandée (mais non obligatoire) :

    {
      "realized_vol_20d": 0.35,
      "realized_vol_5d": 0.40,
      "implied_vol_index": 0.30,
      "vol_of_vol": 0.20,
      "cross_section_vol": 0.25
    }

    Les valeurs sont attendues en vol annualisée (ex : 0.20 = 20 %).
    """
    if not isinstance(raw, dict):
        raw = {}

    return VolatilityMetrics(
        realized_vol_20d=_get_float(raw.get("realized_vol_20d")),
        realized_vol_5d=_get_float(raw.get("realized_vol_5d")),
        implied_vol_index=_get_float(raw.get("implied_vol_index")),
        vol_of_vol=_get_float(raw.get("vol_of_vol")),
        cross_section_vol=_get_float(raw.get("cross_section_vol")),
    )


# ---------------------------------------------------------------------------
# Logic Volatility State Machine
# ---------------------------------------------------------------------------

def infer_vol_regime_and_score(
    metrics: VolatilityMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de volatilité + flag + score simple.

    Intuition très simplifiée :
    - vol faible & stable → "calm" → plutôt supportive
    - vol modérée → "normal"
    - vol élevée mais pas extrême → "stressed"
    - vol très élevée / vol-of-vol élevée → "panic"
    """

    reasons: List[str] = []

    rv20 = metrics.realized_vol_20d
    rv5 = metrics.realized_vol_5d
    iv = metrics.implied_vol_index
    vov = metrics.vol_of_vol
    xsec = metrics.cross_section_vol

    # Cas sans données
    if all(v is None for v in (rv20, rv5, iv, vov, xsec)):
        reasons.append("Aucune donnée de volatilité exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # On utilise rv20 comme anchor si dispo
    anchor = rv20 if rv20 is not None else rv5 if rv5 is not None else iv

    if anchor is None:
        reasons.append("Volatilité partiellement renseignée – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Seuils grossiers mais cohérents avec un univers crypto/offensif :
    # anchor ≈ 0.15 = calme, 0.20–0.40 normal/stressé, >0.40 très agité
    panic = False
    stressed = False
    calm = False

    if anchor <= 0.18:
        calm = True
    elif 0.18 < anchor <= 0.35:
        stressed = False
    elif 0.35 < anchor <= 0.55:
        stressed = True
    else:
        panic = True

    # On renforce panic si vol-of-vol très élevé
    if vov is not None and vov >= 0.35:
        panic = True
        stressed = False

    # On renforce stressed si dispersion forte
    if not panic and xsec is not None and xsec >= 0.30:
        stressed = True

    if panic:
        regime = "panic"
        global_flag = "risk_off"
        score = 30.0
        reasons.append(
            f"Régime de volatilité PANIC (anchor≈{anchor:.2f}, vol_of_vol={vov if vov is not None else 'N/A'}, "
            f"cross_section_vol={xsec if xsec is not None else 'N/A'})."
        )
    elif stressed:
        regime = "stressed"
        global_flag = "caution"
        score = 42.0
        reasons.append(
            f"Régime de volatilité STRESSED (anchor≈{anchor:.2f}, cross_section_vol={xsec if xsec is not None else 'N/A'})."
        )
    elif calm:
        regime = "calm"
        global_flag = "supportive"
        score = 65.0
        reasons.append(
            f"Régime de volatilité CALM (anchor≈{anchor:.2f})."
        )
    else:
        regime = "normal"
        global_flag = "neutral"
        score = 55.0
        reasons.append(
            f"Régime de volatilité NORMAL (anchor≈{anchor:.2f})."
        )

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    if global_flag == "risk_off":
        return "critical"
    if global_flag == "supportive":
        return "info"
    if global_flag == "neutral":
        return "warning"
    if global_flag == "caution":
        return "warning"
    return "info"


def build_volatility_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    G152_DYNAMIC_VOLATILITY_STATE_AUTHORITY_V1

    Canonical authority:
      analysis/volatility_engine_pro.json

    The legacy analysis/volatility_metrics.json manual baseline is no longer
    an authoritative input for trading risk.

    D2 intentionally does not reinterpret raw 15m realised volatility as the
    legacy annualised 5d/20d/IV model. The engine's own per-asset regime and
    flags are aggregated instead.

    Fail-safe contract:
      missing / invalid / empty dynamic engine -> unknown / caution / 50.
    """

    engine_path = data_dir / "analysis" / "volatility_engine_pro.json"
    eng = load_json_file(str(engine_path), default={})

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _unknown(reason: str) -> Tuple[Dict[str, Any], str]:
        state: Dict[str, Any] = {
            "timestamp": now_ts,
            "env": env,
            "symbol": "global",
            "regime": "unknown",
            "global_flag": "caution",
            "score": 50.0,
            "source": "volatility_engine_pro",
            "source_path": str(engine_path),
            "temporal_semantics": "15m_realised_volatility_4h_24h_7d",
            "assets_count": 0,
            "metrics": {
                "vol_4h_mean": None,
                "vol_24h_mean": None,
                "vol_7d_mean": None,
                "vol_ratio_4h_24h_mean": None,
                "vol_ratio_24h_7d_mean": None,
                "spike_fraction": None,
                "extreme_fraction": None,
            },
            "reasons": [reason],
        }
        return state, severity_from_flag("caution")

    if not isinstance(eng, dict):
        return _unknown("Dynamic volatility engine payload invalid.")

    # G152_VOLATILITY_FRESHNESS_GUARD_V1
    #
    # The derived volatility state must never remain supportive because an
    # old raw engine artifact survived on disk. The raw engine is expected
    # to be produced from the current 15m OHLCV cycle.
    #
    # We intentionally use generated_at from the producer payload rather
    # than filesystem mtime as the authoritative temporal provenance.
    max_raw_age_hours = 1.0
    max_future_skew_minutes = 5.0

    raw_generated_at = eng.get("generated_at")
    if not isinstance(raw_generated_at, str) or not raw_generated_at.strip():
        return _unknown(
            "Dynamic volatility engine missing generated_at provenance."
        )

    try:
        raw_dt = dt.datetime.fromisoformat(
            raw_generated_at.strip().replace("Z", "+00:00")
        )
        if raw_dt.tzinfo is None:
            raw_dt = raw_dt.replace(tzinfo=dt.timezone.utc)
        else:
            raw_dt = raw_dt.astimezone(dt.timezone.utc)

        current_dt = dt.datetime.now(dt.timezone.utc)
        raw_age_seconds = (current_dt - raw_dt).total_seconds()
    except Exception:
        return _unknown(
            "Dynamic volatility engine generated_at provenance invalid."
        )

    if raw_age_seconds < -(max_future_skew_minutes * 60.0):
        return _unknown(
            "Dynamic volatility engine generated_at is materially in the future."
        )

    if raw_age_seconds > (max_raw_age_hours * 3600.0):
        return _unknown(
            f"Dynamic volatility engine stale: age_hours="
            f"{raw_age_seconds / 3600.0:.3f} > {max_raw_age_hours:.3f}."
        )

    raw_age_hours = max(0.0, raw_age_seconds / 3600.0)

    assets = eng.get("assets")
    if not isinstance(assets, list) or not assets:
        return _unknown("Dynamic volatility engine missing or contains no assets.")

    valid_assets = [a for a in assets if isinstance(a, dict)]
    if not valid_assets:
        return _unknown("Dynamic volatility engine contains no valid asset payloads.")

    def _floats(key: str) -> List[float]:
        out: List[float] = []
        for asset in valid_assets:
            value = asset.get(key)
            if value is None:
                continue
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
        return out

    def _mean(values: List[float]) -> Optional[float]:
        return (sum(values) / len(values)) if values else None

    v4 = _floats("vol_4h")
    v24 = _floats("vol_24h")
    v7d = _floats("vol_7d")
    r4_24 = _floats("vol_ratio_4h_24h")
    r24_7d = _floats("vol_ratio_24h_7d")

    regime_counts: Dict[str, int] = {}
    spike_count = 0
    extreme_count = 0

    for asset in valid_assets:
        regime = str(asset.get("vol_regime") or "unknown").strip().lower()
        regime_counts[regime] = regime_counts.get(regime, 0) + 1

        flags = asset.get("flags")
        if not isinstance(flags, dict):
            flags = {}

        if flags.get("vol_spike") is True:
            spike_count += 1
        if flags.get("extreme_vol") is True:
            extreme_count += 1

    n = len(valid_assets)
    spike_fraction = spike_count / n
    extreme_fraction = extreme_count / n

    # D2 deliberately consumes the engine's already-classified regime rather
    # than inventing a second incompatible absolute-volatility calibration.
    #
    # Conservative aggregation:
    # - any extreme asset => at least caution
    # - >= 25% extreme => risk_off
    # - >= 50% high/extreme => caution
    # - >= 25% tactical spikes => caution
    # - otherwise majority regime determines calm/normal.
    high_count = regime_counts.get("high", 0)
    stressed_fraction = (high_count + extreme_count) / n

    if extreme_fraction >= 0.25:
        regime = "panic"
        global_flag = "risk_off"
        score = 30.0
        reason = (
            f"Cross-asset volatility panic: extreme_fraction="
            f"{extreme_fraction:.3f}."
        )
    elif extreme_count > 0:
        regime = "stressed"
        global_flag = "caution"
        score = 42.0
        reason = (
            f"Extreme volatility detected on {extreme_count}/{n} assets."
        )
    elif stressed_fraction >= 0.50:
        regime = "stressed"
        global_flag = "caution"
        score = 42.0
        reason = (
            f"Broad high/extreme volatility: stressed_fraction="
            f"{stressed_fraction:.3f}."
        )
    elif spike_fraction >= 0.25:
        regime = "accelerating"
        global_flag = "caution"
        score = 48.0
        reason = (
            f"Broad tactical volatility acceleration: spike_fraction="
            f"{spike_fraction:.3f}."
        )
    else:
        calm_count = regime_counts.get("calm", 0)
        normal_count = regime_counts.get("normal", 0)

        if calm_count > normal_count:
            regime = "calm"
            global_flag = "supportive"
            score = 65.0
            reason = f"Cross-asset volatility predominantly calm ({calm_count}/{n})."
        else:
            regime = "normal"
            global_flag = "neutral"
            score = 55.0
            reason = f"Cross-asset volatility predominantly normal/non-toxic ({n} assets)."

    state = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "source": "volatility_engine_pro",
        "source_path": str(engine_path),
        "source_generated_at": eng.get("generated_at"),
        "source_age_hours": round(raw_age_hours, 6),
        "source_max_age_hours": max_raw_age_hours,
        "source_fresh": True,
        "temporal_semantics": "15m_realised_volatility_4h_24h_7d",
        "assets_count": n,
        "regime_counts": regime_counts,
        "metrics": {
            "vol_4h_mean": _mean(v4),
            "vol_24h_mean": _mean(v24),
            "vol_7d_mean": _mean(v7d),
            "vol_ratio_4h_24h_mean": _mean(r4_24),
            "vol_ratio_24h_7d_mean": _mean(r24_7d),
            "spike_fraction": spike_fraction,
            "extreme_fraction": extreme_fraction,
            "stressed_fraction": stressed_fraction,
        },
        "reasons": [
            reason,
            "Authority=dynamic volatility_engine_pro; legacy manual volatility_metrics ignored.",
        ],
    }

    return state, severity_from_flag(global_flag)


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[volatility_state_machine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_volatility_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "volatility_state_machine_pro.json"
    # NSC_VOLATILITY_ATTACH_RUN_META_V3
    try:
        _rid = str(os.environ.get('NSC_RUN_ID') or '').strip()
    except Exception:
        _rid = ''
    if isinstance(state, dict):
        state.setdefault('writer', 'volatility_state_machine_pro')
        state.setdefault('run_id', _rid or f"{int(time.time()*1000)}-{secrets.token_hex(4)}")

    # NSC_VOLATILITY_CANONICAL_WRITE_V3
    try:
        canon_path = (data_dir / 'analysis' / 'volatility_state.json')
        # NSC_VOLATILITY_CANON_FLAG_SEVERITY_FIX_V2
        try:
            if isinstance(state, dict):
                # Normalize global_flag -> flag
                if state.get('flag') is None and state.get('global_flag') is not None:
                    state['flag'] = state.get('global_flag')
                # Backfill severity if missing
                if state.get('severity') is None:
                    state['severity'] = severity_from_flag(str(state.get('flag') or ''))
        except Exception:
            logger.exception('[volatility_state_machine_pro] canonical normalize failed')
        save_json_file(canon_path, state)
    except Exception:
        logger.exception('[volatility_state_machine_pro] failed to write canonical volatility_state.json')
    # NSC_VOLATILITY_FLAG_SEVERITY_FIX_V1
    if isinstance(state, dict):
        # Normalize flag/global_flag -> flag
        if state.get('flag') is None and state.get('global_flag') is not None:
            state['flag'] = state.get('global_flag')
        # Backfill severity if missing
        if state.get('severity') is None:
            try:
                state['severity'] = severity_from_flag(str(state.get('flag') or ''))
            except Exception:
                state['severity'] = None
    save_json_file(output_path, state)
    logger.info(
        "[volatility_state_machine_pro] volatility_state_machine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event
    publish_event(
        event_type="volatility.state_machine",
        source="volatility_state_machine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[volatility_state_machine_pro] Event volatility.state_machine publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
