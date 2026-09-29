# src/v2/analysis/risk_engine_pro.py
from __future__ import annotations
# NSC_FIX_CORR_GATE_REASONS_LITERAL_BRACES_V1
# NSC_FIX_CORR_REGIME_REASON_SOURCE_UNIQUE_V1
# NSC_FIX_CORR_GATE_STATE_REASONS_FSTRINGS_V1
# NSC_FIX_EMPTY_ELSE_BLOCKS_V1
# NSC_DEDUPE_CORR_REGIME_REASON_V1
# NSC_FIX_CORR_GATE_ACTIVE_INACTIVE_FSTRINGS_V2
# NSC_FIX_CORR_GATE_REASON_FSTRINGS_V1

import os
import time

# NSC_FIX_DATADIR_V1
def _resolve_data_dir_cli(args):
    """Return DATA_DIR. CLI --data-dir has priority over env/fallback."""
    from pathlib import Path
    import os
    if getattr(args, "data_dir", None):
        return Path(args.data_dir).expanduser().resolve()
    # fallback: NSC_DATA_DIR env or ./data
    return Path(os.getenv("NSC_DATA_DIR", "data")).expanduser().resolve()

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import ensure_dir, load_json_file, save_json_file

logger = get_logger("risk_engine_pro")


# ---------------------------------------------------------------------------
# Utils / Env
# ---------------------------------------------------------------------------

def _now_ts() -> int:
    return int(time.time())


def _get_env() -> str:
    return os.environ.get("NSC_ENV", "PREPROD")


def _get_data_dir() -> Path:
    root = os.environ.get("NSC_ROOT_DIR") or os.getcwd()
    return Path(os.environ.get("NSC_DATA_DIR", str(Path(root) / "data")))


def _analysis_dir(data_dir: Path) -> Path:
    return data_dir / "analysis"


def _telemetry_dir(data_dir: Path) -> Path:
    return data_dir / "telemetry"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _score_01(x: Any, default: float = 0.5) -> float:
    v = _safe_float(x, default)
    if v > 1.0:
        v = v / 100.0
    return _clamp(v, 0.0, 1.0)


def _score_100(x: Any, default: float = 50.0) -> float:
    v = _safe_float(x, default)
    if v <= 1.0:
        v = v * 100.0
    return _clamp(v, 0.0, 100.0)


from src.v2.utils import file_utils as fu

def _load_json(path: Path, default: Any) -> Any:
    return fu.load_json_file(path, default=default)

def _read_score(payload: Any, keys: Tuple[str, ...]) -> Optional[float]:
    if not isinstance(payload, dict):
        return None
    for k in keys:
        v = payload.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _publish_event(event_type: str, source: str, severity: str, payload: Dict[str, Any]) -> None:
    """
    Best effort publish (MessageBus / MessageBusPro).
    """
    try:
        from src.v2.core.message_bus import MessageBus  # type: ignore
        MessageBus().publish(event_type, source, severity, payload)
        return
    except Exception:
        pass

    try:
        from src.v2.core.message_bus_pro import MessageBusPro  # type: ignore
        MessageBusPro().publish(event_type, source, severity, payload)
        return
    except Exception:
        pass

    logger.debug("[risk_engine_pro] EventBus indisponible (skip publish)")


def _severity(score_100: float) -> str:
    # ici score élevé = risque faible, donc severity inverse
    if score_100 >= 70:
        return "info"
    if score_100 >= 45:
        return "warning"
    return "critical"


# ---------------------------------------------------------------------------
# Risk scoring (light mais robuste)
# ---------------------------------------------------------------------------

# G152_RISK_CORRELATION_SINGLE_AUTHORITY_V1
def _load_correlation_authority(analysis_dir: Path) -> Dict[str, Any]:
    """
    Single correlation authority for Risk Engine.

    Contract:
      - reads correlation_regime_engine_pro.json exactly once per risk computation
      - accepts only a fresh G152 Correlation V1 artifact
      - missing/invalid/stale => neutral score=50 and gate-eligible=False
      - never resurrects stale correlation authority
    """
    neutral = {
        "valid": False,
        "source_fresh": False,
        "score": 50.0,
        "regime": "unknown",
        "global_flag": "neutral",
        "source": None,
        "source_generated_at": None,
        "method": None,
        "window_returns": None,
        "pair_count": 0,
        "macro_risk_level": "neutral",
    }

    try:
        corr = fu.load_json_file(
            str(Path(analysis_dir) / "correlation_regime_engine_pro.json"),
            default={},
        ) or {}
    except Exception:
        return neutral

    if not isinstance(corr, dict) or not corr:
        return neutral

    if corr.get("source_fresh") is not True:
        return neutral

    try:
        score = float(corr.get("score"))
    except Exception:
        return neutral

    if not (0.0 <= score <= 100.0):
        return neutral

    regime = str(corr.get("regime") or "unknown").strip().lower()
    global_flag = str(corr.get("global_flag") or "neutral").strip().lower()

    macro = str(corr.get("macro_risk_level") or "neutral").strip().lower()
    if macro not in ("low", "neutral", "medium", "high"):
        macro = "neutral"

    return {
        "valid": True,
        "source_fresh": True,
        "score": score,
        "regime": regime,
        "global_flag": global_flag,
        "source": corr.get("source"),
        "source_generated_at": corr.get("source_generated_at"),
        "method": corr.get("method"),
        "window_returns": corr.get("window_returns"),
        "pair_count": corr.get("pair_count"),
        "macro_risk_level": macro,
    }



def compute_risk_state(analysis_dir: Path, telemetry_dir: Path) -> Dict[str, Any]:
    reasons: List[str] = []
    components: List[Dict[str, Any]] = []

    # Defaults neutres
    base = 50.0

    # --- Inputs (best effort) ---
    market_regime = _load_json(analysis_dir / "market_regime_detector.json", default={})
    market_conditions = _load_json(analysis_dir / "market_conditions_engine_pro.json", default={})
    volatility_state = _load_json(analysis_dir / "volatility_state_machine_pro.json", default={})
    # NSC_VOL_SHOCK_HARD_VETO_V1
    try:
        _v = volatility_state if isinstance(volatility_state, dict) else {}
        _v_reg = str(_v.get('regime') or _v.get('flag') or '').lower()
        _v_sev = str(_v.get('severity') or '').lower()
        _v_score = float(_v.get('score') or 0.0)
        # If volatility is toxic: FORCE real risk_off (must propagate to trading_kernel hard gate)
        if _v_reg in ('shock','vol_shock','volatility_shock') or _v_sev in ('critical','severe'):
            # hard veto state
            forced_flag = 'risk_off'
            forced_score_cap = 20.0
            # If variables exist later, we will cap them (best-effort).
            os.environ['NSC_FORCED_RISK_FLAG'] = forced_flag
            os.environ['NSC_FORCED_RISK_SCORE_CAP'] = str(forced_score_cap)
    except Exception:
        pass

    coherence = _load_json(analysis_dir / "market_coherence_engine_pro.json", default={})
    system_metrics = _load_json(telemetry_dir / "system_metrics.json", default={})

    # --- Extract signals ---
    # Market conditions score (0..100)
    mc_score = _read_score(market_conditions, ("score",))
    if mc_score is None:
        mc_score = 50.0
        reasons.append("market_conditions_score missing -> 50")
    mc_score = _score_100(mc_score, 50.0)

    # Volatility score (0..100) : si absent -> 50
    vol_score = _read_score(volatility_state, ("score", "value"))
    if vol_score is None:
        vol_score = 50.0
        reasons.append("volatility_score missing -> 50")
    vol_score = _score_100(vol_score, 50.0)
    # --- Volatility state gate (volatility_state_machine_pro) ---
    try:
        _vf = str((volatility_state or {}).get("global_flag") or "").strip().lower()
        _vr = str((volatility_state or {}).get("regime") or "").strip().lower()
        _vs = float(vol_score or 0.0)

        # Hard gate ONLY on explicit risk_off/emergency OR very low score
        if _vf in ("risk_off", "off", "emergency") or _vs <= 35.0:
            global_flag = "risk_off"
            reasons.append(f"volatility_state={_vr or _vf} score={_vs:.2f} => risk_off")
        else:
            reasons.append(f"volatility_state={_vr or _vf} score={_vs:.2f} => {_vf or 'ok'}")
    except Exception:
        logger.exception("[risk_engine_pro] volatility gate failed")


    # G152_COHERENCE_SEMANTIC_CONTRACT_V1
    # Coherence measures agreement between independent authorities.
    # It is NOT a risk-appetite score:
    #   coherent/supportive and coherent/defensive may both score 90.
    # Therefore it must never be injected arithmetically as a favourable
    # Risk Score component.
    coh_score = _read_score(coherence, ("score",))
    if coh_score is None:
        coh_score = 50.0
        reasons.append("coherence_score missing -> observational neutral 50")
    coh_score = _score_100(coh_score, 50.0)

    coh_regime = str(
        (coherence or {}).get("regime") or "unknown"
    ).strip().lower() if isinstance(coherence, dict) else "unknown"

    coh_direction = str(
        (coherence or {}).get("directional_context") or "unknown"
    ).strip().lower() if isinstance(coherence, dict) else "unknown"

    coh_source_fresh = (
        coherence.get("source_fresh") is True
        if isinstance(coherence, dict)
        else False
    )

    reasons.append(
        "coherence observational only: "
        f"regime={coh_regime} direction={coh_direction} "
        f"agreement_score={coh_score:.2f} fresh={coh_source_fresh}"
    )

    # Market regime / risk_mode
    regime = None
    risk_mode = None
    if isinstance(market_regime, dict):
        regime = market_regime.get("regime")
        risk_mode = market_regime.get("risk_mode")

    # Pipeline health (has errors -> malus)
    steps_error = None
    if isinstance(system_metrics, dict):
        steps_error = system_metrics.get("steps_error")

    # --- Risk model ---
    # score_final élevé = risque faible / conditions favorables.
    #
    # G152 Coherence V1 is deliberately excluded from arithmetic weighting:
    # its score measures cross-authority agreement, not risk appetite.
    #
    # Historical non-coherence weights were 35/20/15/10 (sum=80).
    # Normalize them to 100% without changing their relative importance:
    #   market_conditions = 43.75%
    #   volatility        = 25.00%
    #   correlation       = 18.75%
    #   pipeline_health   = 12.50%
    pipeline_score = 100.0
    if isinstance(steps_error, int) and steps_error > 0:
        pipeline_score = 40.0
        reasons.append(f"pipeline errors={steps_error} -> pipeline_score=40")
    elif isinstance(steps_error, int) and steps_error == 0:
        pipeline_score = 100.0

    # Correlation V1 — one canonical read for this entire risk computation.
    corr_authority = _load_correlation_authority(analysis_dir)
    corr_score = float(corr_authority["score"])
    corr_reg = str(corr_authority["regime"])
    corr_flag = str(corr_authority["global_flag"])
    corr_valid = bool(corr_authority["valid"])
    macro_risk_level = str(corr_authority.get("macro_risk_level") or "neutral")

    if not corr_valid:
        reasons.append("correlation unavailable/stale/invalid -> neutral 50")

    score = (
        0.4375 * mc_score +
        0.2500 * vol_score +
        0.1875 * corr_score +
        0.1250 * pipeline_score
    )

    # Risk_mode override léger
    if risk_mode in ("risk_off", "off", "emergency"):
        score = min(score, 35.0)
        reasons.append(f"risk_mode={risk_mode} -> cap score<=35")
    elif risk_mode in ("caution",):
        score = min(score, 55.0)
        reasons.append(f"risk_mode={risk_mode} -> cap score<=55")

    # Regime info (pas un veto ici, juste trace)
    if regime:
        reasons.append(f"market_regime={regime}")

    # Macro compatibility: no second correlation read.
    _macro = str(macro_risk_level or "neutral").lower().strip()
    if _macro == "high":
        score = min(score, 55.0)
        reasons.append("macro_risk_level=high -> cap score<=55")
    elif _macro == "medium":
        score = min(score, 65.0)
        reasons.append("macro_risk_level=medium -> cap score<=65")
    score = _clamp(score, 0.0, 100.0)

    # Flag exploitable par orchestrator / kernel
    flag = "normal"
    if score <= 35:
        flag = "risk_off"
    elif score <= 55:
        flag = "caution"
    else:
        flag = "risk_on"

    # Components debug
    # Weights rééquilibrés (somme=1.00) avec ajout corrélation
    # === NSC_MACRO_TOPLEVEL_AND_MINFLAG_V1 ===
    # Force un minimum de prudence si le macro est défavorable
    try:
        _macro = str(locals().get('macro_risk_level', '') or '').strip().lower()
        if _macro == 'high':
            # au minimum 'caution' (on ne downgrade jamais un risk_off)
            if flag == 'normal' or flag == 'risk_on':
                flag = 'caution'
            # si global_flag existe, on le force aussi au minimum
            try:
                _gf = str(locals().get('global_flag', '') or '').strip().lower()
                if _gf in ('', 'normal', 'risk_on'):
                    global_flag = 'caution'
            except Exception:
                pass
    except Exception:
        logger.exception('[risk_engine_pro] macro min-flag patch failed')
    # === END NSC_MACRO_TOPLEVEL_AND_MINFLAG_V1 ===
    components.append({"name": "market_conditions", "score": round(mc_score, 2), "weight": 0.4375})
    components.append({
        "name": "coherence",
        "score": round(coh_score, 2),
        "weight": 0.0,
        "regime": coh_regime,
        "directional_context": coh_direction,
        "source_fresh": coh_source_fresh,
        "note": "agreement_only_not_risk_appetite",
    })
    components.append({"name": "volatility", "score": round(vol_score, 2), "weight": 0.25})
    components.append({"name": "correlation", "score": round(corr_score, 2), "weight": 0.1875})
    components.append({"name": "macro", "score": 0.0, "weight": 0.0, "note": f"macro_risk_level={macro_risk_level}"})
    components.append({"name": "pipeline_health", "score": round(pipeline_score, 2), "weight": 0.125})

    # --- HF-like Policy (gross exposure & selectivity) ---
    # Objectif: si corrélation intra-crypto élevée => diversification en baisse => réduire gross + limiter nb positions
    policy = {
        "position_size_mult": 1.0,      # multiplicateur de sizing (gross exposure)
        "max_open_positions": None,     # cap positions (None = pas de cap)
        "min_meta_score": None,         # filtre qualité (None = pas de filtre)
        "notes": [],
    }

    # NSC_APPLY_FORCED_RISK_FLAG_V1
    # If volatility_state_machine_pro flagged a toxic regime, force real risk_off here.
    try:
        _forced_flag = str(os.environ.get('NSC_FORCED_RISK_FLAG') or '').strip().lower()
        _cap = float(os.environ.get('NSC_FORCED_RISK_SCORE_CAP') or 0.0)
        if _forced_flag in ('risk_off','off','emergency'):
            # Override global flag + cap score (so trading_kernel HARD gate blocks execution)
            flag = 'risk_off'
            try:
                if _cap > 0:
                    score = min(float(score), float(_cap))
                else:
                    score = min(float(score), 20.0)
            except Exception:
                score = 20.0
            # Ensure volatility component reflects toxicity for observability
            try:
                vol_score = 0.0
            except Exception:
                pass
            # Explainability
            try:
                reasons.append('volatility_state=TOXIC => forced risk_off (NSC_FORCED_RISK_FLAG)')
            except Exception:
                pass
    except Exception:
        pass


    # Base sur le flag global
    if flag == "risk_off":
        policy["position_size_mult"] = 0.0
        policy["max_open_positions"] = 0
        policy["min_meta_score"] = 999
        policy["notes"].append("risk_off -> no new positions")
    elif flag == "caution":
        policy["position_size_mult"] = 0.55
        policy["max_open_positions"] = 2
        policy["min_meta_score"] = 70
        policy["notes"].append("caution -> reduce gross + more selective")

    # Ajustement sur corrélation (si corr_score défini)
    try:
        _cs = float(corr_score)
        _cr = str(corr_reg or corr_flag or "").lower()
        if corr_valid and ("high_corr" in _cr or _cs <= 45):
            # corr élevée => réduire gross + cap positions
            policy["position_size_mult"] = min(policy["position_size_mult"], 0.65)
            policy["max_open_positions"] = 3 if (policy["max_open_positions"] is None or policy["max_open_positions"] > 3) else policy["max_open_positions"]
            policy["min_meta_score"] = 65 if policy["min_meta_score"] is None else max(policy["min_meta_score"], 65)
            policy["notes"].append(f"high_corr -> gross<=0.65 (corr_score={_cs:.2f})")
        if corr_valid and _cs <= 30:
            policy["position_size_mult"] = min(policy["position_size_mult"], 0.45)
            policy["max_open_positions"] = 2 if (policy["max_open_positions"] is None or policy["max_open_positions"] > 2) else policy["max_open_positions"]
            policy["min_meta_score"] = 75 if policy["min_meta_score"] is None else max(policy["min_meta_score"], 75)
            policy["notes"].append(f"very_high_corr -> gross<=0.45 (corr_score={_cs:.2f})")
    except Exception:
        policy["notes"].append("corr_adjust_failed")

    # Safety: policy jamais null
    if not isinstance(policy, dict):
        policy = {"position_size_mult": 1.0, "max_open_positions": None, "min_meta_score": None, "notes": ["policy_defaulted"]}

    # Single correlation hysteresis authority.
    correlation_gate = {
        "active": False,
        "prev_active": False,
        "enter": 35.0,
        "exit": 45.0,
        "source_valid": bool(corr_valid),
    }

    try:
        data_dir = Path(analysis_dir).resolve().parent
        gate_path = data_dir / "state" / "correlation_gate_state.json"
        prev = fu.load_json_file(str(gate_path), default={}) or {}
        prev_active = bool(prev.get("active")) if isinstance(prev, dict) else False

        active = False

        if corr_valid:
            active = prev_active
            if corr_reg == "high_corr":
                if (not prev_active) and corr_score <= 35.0:
                    active = True
                elif prev_active and corr_score >= 45.0:
                    active = False
            else:
                active = False
        else:
            # Temporal sovereignty:
            # stale/missing correlation cannot preserve historical authority.
            active = False

        correlation_gate = {
            "active": bool(active),
            "prev_active": bool(prev_active),
            "enter": 35.0,
            "exit": 45.0,
            "source_valid": bool(corr_valid),
        }

        if active:
            if flag != "risk_off":
                flag = "caution"
                policy["position_size_mult"] = min(policy["position_size_mult"], 0.55)
                policy["max_open_positions"] = (
                    2 if policy["max_open_positions"] is None
                    else min(policy["max_open_positions"], 2)
                )
                policy["min_meta_score"] = (
                    70 if policy["min_meta_score"] is None
                    else max(policy["min_meta_score"], 70)
                )
                policy["notes"].append("correlation_gate ACTIVE -> reduced, no hard block")
                reasons.append("correlation_gate ACTIVE => reduced (no hard block)")

    except Exception:
        logger.exception("[risk_engine_pro] correlation single gate evaluation failed")
        correlation_gate = {
            "active": False,
            "prev_active": False,
            "enter": 35.0,
            "exit": 45.0,
            "source_valid": False,
        }


    return {
        "macro_risk_level": str(locals().get("macro_risk_level", "neutral") or "neutral"),
        "timestamp": _now_ts(),
        "env": _get_env(),
        "score": round(score, 2),        # ✅ c’est ce champ que meta_score attend
        "risk_score": round(score, 2),   # compat
        "flag": flag,
        "correlation_gate": correlation_gate,
        "correlation_regime": {
            "regime": corr_reg,
            "score": corr_score,
            "global_flag": corr_flag,
            "source_fresh": bool(corr_authority.get("source_fresh")),
            "source": corr_authority.get("source"),
            "source_generated_at": corr_authority.get("source_generated_at"),
            "method": corr_authority.get("method"),
            "window_returns": corr_authority.get("window_returns"),
            "pair_count": corr_authority.get("pair_count"),
        },
        "inputs": {
            "market_regime": {"regime": regime, "risk_mode": risk_mode},
            "market_conditions": {"score": round(mc_score, 2)},
            "coherence": {
                "score": round(coh_score, 2),
                "regime": coh_regime,
                "directional_context": coh_direction,
                "source_fresh": coh_source_fresh,
                "score_semantics": "cross_authority_agreement_not_risk_appetite",
                "risk_weight": 0.0,
            },
            "volatility_state": {"score": round(vol_score, 2)},
            "pipeline": {"steps_error": steps_error},
        },
        "components": components,
        "policy": policy,
        "reasons": reasons,
    }


def main() -> None:
    data_dir = _get_data_dir()
    env = _get_env()
    analysis_dir = _analysis_dir(data_dir)
    telemetry_dir = _telemetry_dir(data_dir)

    ensure_dir(str(data_dir))
    ensure_dir(str(analysis_dir))
    ensure_dir(str(telemetry_dir))

    logger.info("[risk_engine_pro] DATA_DIR=%s, env=%s", str(data_dir), env)

    state = compute_risk_state(analysis_dir=analysis_dir, telemetry_dir=telemetry_dir)

    # Persist the already-computed single correlation gate.
    try:
        gate = state.get("correlation_gate") if isinstance(state, dict) else {}
        corr = state.get("correlation_regime") if isinstance(state, dict) else {}
        gate_path = data_dir / "state" / "correlation_gate_state.json"
        ensure_dir(str(gate_path.parent))
        fu.save_json_file(str(gate_path), {
            "active": bool((gate or {}).get("active")),
            "prev_active": bool((gate or {}).get("prev_active")),
            "regime": (corr or {}).get("regime"),
            "score": (corr or {}).get("score"),
            "source_fresh": bool((corr or {}).get("source_fresh")),
            "source_generated_at": (corr or {}).get("source_generated_at"),
            "run_id": str(os.environ.get("NSC_RUN_ID") or ""),
            "writer": "risk_engine_pro",
            "timestamp": _now_ts(),
        })
    except Exception:
        logger.exception("[risk_engine_pro] correlation gate persistence failed")

    out_path = analysis_dir / "risk_engine_pro.json"

    # ───────────────────────────────────────────────────────────
    # Compat sizing: produire un risk index par-asset (assets[])
    # + alias global_flag pour les loaders existants
    # ───────────────────────────────────────────────────────────
    try:
        if isinstance(state, dict):
            # alias compat
            if state.get("global_flag") is None and state.get("flag") is not None:
                state["global_flag"] = state.get("flag")

            if not state.get("assets"):
                symbols = []

                # 1) signal_candidates.json (prioritaire)
                candidates = fu.load_json_file(str(analysis_dir / "signal_candidates.json"), default=[])
                if isinstance(candidates, list):
                    for c in candidates:
                        sym = str((c or {}).get("symbol") or (c or {}).get("asset") or "").strip().lower()
                        if sym:
                            symbols.append(sym)

                # 2) weak_signals_engine_pro.json
                if not symbols:
                    weak = fu.load_json_file(os.path.join(DATA_DIR, "analysis", "weak_signals_engine_pro.json"), default={})
                    wk_assets = weak.get("assets") if isinstance(weak, dict) else None
                    if isinstance(wk_assets, list):
                        for w in wk_assets:
                            sym = str((w or {}).get("symbol") or "").strip().lower()
                            if sym:
                                symbols.append(sym)

                # 3) momentum_scores.json (fallback)
                if not symbols:
                    ms = fu.load_json_file(os.path.join(DATA_DIR, "analysis", "momentum_scores.json"), default={})
                    if isinstance(ms, dict):
                        if isinstance(ms.get("scores"), dict):
                            symbols.extend([str(k).strip().lower() for k in ms["scores"].keys()])
                        elif isinstance(ms.get("assets"), list):
                            for a in ms["assets"]:
                                sym = str((a or {}).get("symbol") or "").strip().lower()
                                # === NSC_RISK_DEDUP_DEBUG_V1 ===
                                try:
                                    logger.info('[risk_engine_pro] risk.state gate: score=%s flag=%s macro=%s env=%s',
                                                (payload.get('score') if isinstance(payload, dict) else None),
                                                (payload.get('global_flag') if isinstance(payload, dict) else None),
                                                (payload.get('macro_risk_level') if isinstance(payload, dict) else None),
                                                (payload.get('env') if isinstance(payload, dict) else None))
                                except Exception:
                                    pass

                                if sym:
                                    symbols.append(sym)

                symbols = sorted(set([s for s in symbols if s]))

                gflag = state.get("global_flag") or "caution"
                assets = []
                for sym in symbols:
                    # conservateur: si global risk_on/ok -> ok, sinon caution
                    risk_flag = "ok" if gflag in ("risk_on", "ok") else "caution"
                    assets.append({
                        "symbol": sym,
                        "risk_flag": risk_flag,
                        "risk_score": state.get("risk_score"),
                        "size_multiplier": 1.0 if risk_flag == "ok" else 0.5,
                        "flags": {"hard_veto": False, "soft_veto": False},
                        "inputs": {"source": "derived_from_global_risk_engine", "global_flag": gflag},
                    })

                state["assets"] = assets
                logger.info("[risk_engine_pro] Derived per-asset risk items: n=%d", len(assets))
    except Exception:
        logger.exception("[risk_engine_pro] Failed to derive per-asset risk items (assets[])")
    fu.save_json_file(str(out_path), state)

    
    # === NSC_RISK_EVENT_PUBLISH_UNIFIED_V5 ===
    # Publication unique vers le Message Bus PRO + déduplication (fail-safe)
    try:
        import time
        from src.v2.core.message_bus import publish_event
        from src.v2.utils import file_utils as _fu_local  # NSC_RENAME_LOCAL_FU_V2
        payload = state if isinstance(state, dict) else {}

        # enrichissement standard
        payload.setdefault("env", os.getenv("NSC_ENV", "UNKNOWN"))
        payload.setdefault("writer", "risk_engine_pro")

        # map global_flag -> severity
        gf = str(payload.get("global_flag", "")).lower()
        sev_map = {"caution": "warning", "danger": "error", "block": "critical"}
        severity = sev_map.get(gf, "info")

        # ---------- DEDUPE ----------
        score_eps = 1.0
        heartbeat_seconds = 1800  # 30 min

        stamp_path = (analysis_dir / "risk_state_last.json")
        last = _fu_local.load_json_file(str(stamp_path), default={}) or {}
        if not isinstance(last, dict):
            last = {}

        now = int(time.time())
        last_ts = int(last.get("ts", 0) or 0)

        last_flag = str(last.get("global_flag", "") or "")
        last_macro = str(last.get("macro_risk_level", "") or "")
        try:
            last_score = float(last.get("score", 0.0) or 0.0)
        except Exception:
            last_score = 0.0

        cur_flag = str(payload.get("global_flag", "") or "")
        cur_macro = str(payload.get("macro_risk_level", "") or "")
        try:
            cur_score = float(payload.get("score", 0.0) or 0.0)
        except Exception:
            cur_score = 0.0

        changed = (cur_flag != last_flag) or (cur_macro != last_macro) or (abs(cur_score - last_score) >= score_eps)
        heartbeat = (now - last_ts) >= heartbeat_seconds
        do_publish = changed or heartbeat

        logger.info(
            "[risk_engine_pro] risk.state publish DECISION=%s changed=%s heartbeat=%s last_ts=%s now=%s "
            "last(flag=%s macro=%s score=%s) cur(flag=%s macro=%s score=%s)",
            ("PUBLISH" if do_publish else "SKIP"),
            changed, heartbeat, last_ts, now,
            last_flag, last_macro, last_score,
            cur_flag, cur_macro, cur_score,
        )

        if do_publish:
            publish_event(
                event_type="risk.state",
                source="risk_engine_pro",
                severity=severity,
                payload=payload,
            )
            _fu_local.save_json_file(str(stamp_path), {
                "ts": now,
                "global_flag": cur_flag,
                "macro_risk_level": cur_macro,
                "score": cur_score,
            })
    except Exception:
        logger.exception("[risk_engine_pro] risk.state publish failed (fail-safe)")



    logger.info("[risk_engine_pro] OK score=%.2f flag=%s -> %s", state["score"], state["flag"], str(out_path))


if __name__ == "__main__":
    main()
