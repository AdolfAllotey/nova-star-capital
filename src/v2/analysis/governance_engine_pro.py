# src/v2/analysis/governance_engine_pro.py

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.v2.utils.file_utils import load_json_file, save_json_file, get_data_dir

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # fallback
    from src.v2.logger import get_logger  # type: ignore

logger = get_logger("governance_engine_pro")


@dataclass
class GovernanceScore:
    score: float
    flag: str
    hard_block: bool
    can_trade_recommended: bool
    reasons: List[str]


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_get(d: Any, path: List[str], default: Any = None) -> Any:
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _load_first_json(data_dir: Path, rel_paths: Sequence[str], default: Any = None) -> Tuple[Any, Optional[str]]:
    for rel in rel_paths:
        full = data_dir / rel
        obj = load_json_file(full, default=None)
        if obj is not None:
            return obj, rel
    return default, None


def _normalize_flag(raw: Any, default: str = "ok") -> str:
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() or default
    return default


def _normalize_score(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw)
    except Exception:
        return None


def _extract_flag_and_score(obj: Optional[Dict[str, Any]]) -> Tuple[str, Optional[float]]:
    if not isinstance(obj, dict):
        return "ok", None

    flag = (
        obj.get("flag")
        or obj.get("global_flag")
        or _safe_get(obj, ["stats", "global_flag"], None)
        or _safe_get(obj, ["summary", "global_flag"], None)
    )
    flag_n = _normalize_flag(flag, default="ok")

    score = (
        obj.get("score")
        or obj.get("avg_meta_score")
        or obj.get("risk_score")
        or _safe_get(obj, ["summary", "score"], None)
    )
    score_n = _normalize_score(score)

    return flag_n, score_n


def _extract_backpressure_mode(obj: Optional[Dict[str, Any]]) -> str:
    if not isinstance(obj, dict):
        return "normal"
    return _normalize_flag(obj.get("mode", "normal"), default="normal")


def _extract_production_mode(obj: Optional[Dict[str, Any]]) -> str:
    if not isinstance(obj, dict):
        return "normal"
    return _normalize_flag(obj.get("mode", "normal"), default="normal")


def _extract_logs_errors(obj: Optional[Dict[str, Any]]) -> Tuple[bool, int]:
    if not isinstance(obj, dict):
        return False, 0
    has_errors = bool(obj.get("has_errors", False))
    steps_error = int(obj.get("steps_error", 0) or 0)
    return has_errors, steps_error


def _extract_weak_avoid(obj: Optional[Dict[str, Any]]) -> int:
    if not isinstance(obj, dict):
        return 0
    return int(
        obj.get("weak_avoid", 0)
        or _safe_get(obj, ["stats", "nb_weak_avoid"], 0)
        or _safe_get(obj, ["metrics", "nb_weak_avoid"], 0)
        or 0
    )


def _extract_risk_limits(risk_limits: Optional[Dict[str, Any]], risk_engine: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    if isinstance(risk_limits, dict):
        out.update(risk_limits)

    if isinstance(risk_engine, dict):
        for k in ("mode", "risk_on_off", "size_factor", "max_positions", "risk_mode"):
            if k in risk_engine and out.get(k) is None:
                out[k] = risk_engine.get(k)

    out.setdefault("risk_mode", out.get("risk_mode", "normal"))
    out.setdefault("risk_on_off", out.get("risk_on_off", "on"))

    out["risk_mode"] = _normalize_flag(out.get("risk_mode", "normal"), default="normal")
    out["risk_on_off"] = _normalize_flag(out.get("risk_on_off", "on"), default="on")

    return out


def compute_governance_score(
    risk_engine: Optional[Dict[str, Any]],
    risk_limits: Optional[Dict[str, Any]],
    weak_signals: Optional[Dict[str, Any]],
    meta_score: Optional[Dict[str, Any]],
    stress_test: Optional[Dict[str, Any]],
    logs_overview: Optional[Dict[str, Any]],
    backpressure_state: Optional[Dict[str, Any]],
    production_protocol: Optional[Dict[str, Any]],
    kill_switch: Optional[Dict[str, Any]],
) -> GovernanceScore:
    """
    Score global de gouvernance (0–100) et flag:
      - ok
      - caution
      - block
      - hard_block

    Philosophie NSC:
      - "caution" ne doit PAS bloquer : trade possible (souvent en reduced)
      - hard_block uniquement sur des vetos durs (prod emergency, backpressure emergency, risk_on_off=off, kill switch hard, stress critical, etc.)
    """
    reasons: List[str] = []
    score = 100.0
    hard_block = False

    # --- 1) Protocole de production ---
    prod_mode = _extract_production_mode(production_protocol)
    if prod_mode == "emergency":
        score = min(score, 10.0)
        hard_block = True
        reasons.append("Production Protocol en mode EMERGENCY.")
    elif prod_mode == "degraded":
        score = min(score, 40.0)
        reasons.append("Production Protocol en mode DEGRADED.")

    # --- 2) Stress Test ---
    stress_flag, _ = _extract_flag_and_score(stress_test or {})
    stress_summary = _safe_get(stress_test or {}, ["summary"], {}) if isinstance(stress_test, dict) else {}
    stress_breaches = _safe_get(stress_summary, ["nb_breaches"], 0)
    worst_dd = _safe_get(stress_summary, ["worst_drawdown_pct"], 0.0)

    if stress_flag == "critical":
        score -= 35.0
        hard_block = True
        reasons.append(f"Stress Test Engine CRITICAL (nb_breaches={stress_breaches}, worst_dd={float(worst_dd):.2%}).")
    elif stress_flag != "ok":
        score -= 20.0
        reasons.append(f"Stress Test Engine en mode {stress_flag.upper()} (nb_breaches={stress_breaches}).")

    # --- 3) Backpressure ---
    bp_mode = _extract_backpressure_mode(backpressure_state)
    if bp_mode == "emergency":
        score -= 30.0
        hard_block = True
        reasons.append("Backpressure Engine en mode EMERGENCY (surcharge / erreurs critiques).")
    elif bp_mode == "degraded":
        score -= 20.0
        reasons.append("Backpressure Engine en mode DEGRADED (mode ralenti recommandé).")

    # --- 4) Logs overview ---
    has_errors, steps_error = _extract_logs_errors(logs_overview)
    if has_errors or steps_error:
        score -= 20.0
        reasons.append(f"Logs overview signale des erreurs dans la boucle quotidienne (steps_error={steps_error}).")

    # --- 5) Risk Engine PRO ---
    risk_flag, _ = _extract_flag_and_score(risk_engine)
    if risk_flag == "danger":
        score -= 35.0
        reasons.append("Risk Engine PRO en mode DANGER (contexte défavorable).")
    elif risk_flag == "caution":
        score -= 20.0
        reasons.append("Risk Engine PRO en mode CAUTION (prudence renforcée).")
    elif risk_flag in ("emergency", "hard_block"):
        score -= 40.0
        hard_block = True
        reasons.append(f"Risk Engine PRO en mode {risk_flag.upper()}.")

    # --- 6) Weak Signals ---
    weak_flag, _ = _extract_flag_and_score(weak_signals)
    nb_weak_avoid = _extract_weak_avoid(weak_signals)

    if weak_flag == "caution":
        score -= 10.0
        reasons.append(
            f"Weak Signals Engine PRO en mode CAUTION (weak_avoid={nb_weak_avoid})." if nb_weak_avoid else
            "Weak Signals Engine PRO en mode CAUTION."
        )
    elif weak_flag in ("danger", "block", "hard_block", "emergency"):
        score -= 20.0
        reasons.append(f"Weak Signals Engine PRO en mode {weak_flag.upper()}.")

    # --- 7) Meta-Score ---
    meta_flag, _ = _extract_flag_and_score(meta_score)
    if meta_flag == "danger":
        score -= 30.0
        reasons.append("Meta-Score Engine PRO en mode DANGER (signaux agrégés défavorables).")
    elif meta_flag == "caution":
        score -= 15.0
        reasons.append("Meta-Score Engine PRO en mode CAUTION (signaux agrégés mitigés).")

    # --- 8) Risk limits / Kill switch / risk_on_off ---
    merged_limits = _extract_risk_limits(risk_limits, risk_engine)
    risk_mode = merged_limits.get("risk_mode", "normal")
    risk_on_off = merged_limits.get("risk_on_off", "on")

    kill_data = kill_switch or {}
    ks_enabled = bool(kill_data.get("enabled", False))
    ks_mode = _normalize_flag(kill_data.get("mode", "soft"), default="soft")
    ks_hard = bool(kill_data.get("hard_block", False)) or ks_mode in ("hard", "hard_block")
    ks_soft = bool(kill_data.get("soft_block", False)) or ks_mode in ("soft_block", "soft")

    if risk_on_off == "off":
        score -= 30.0
        hard_block = True
        reasons.append("Risk Engine en mode OFF (risk_on_off=off).")

    if ks_enabled and ks_hard:
        score = min(score, 5.0)
        hard_block = True
        reasons.append("Kill-switch HARD actif (hard_block).")
    elif ks_enabled and ks_soft:
        score -= 15.0
        reasons.append("Kill-switch SOFT BLOCK actif (prudence renforcée).")

    if risk_mode == "reduced":
        score -= 5.0
        reasons.append("Risk mode = REDUCED (taille réduite, contexte tendu).")

    # --- 9) Normalisation score ---
    score = max(0.0, min(100.0, score))

    # --- 10) Flag global ---
    if hard_block:
        flag = "hard_block"
    else:
        if score >= 80.0:
            flag = "ok"
        elif score >= 60.0:
            flag = "caution"
        elif score >= 40.0:
            flag = "block"
        else:
            flag = "hard_block"

    # --- 11) can_trade_recommended (ok + caution => True sauf veto durs) ---
    can_trade_recommended = (
        (not hard_block)
        and (flag in ("ok", "caution"))
        and risk_on_off == "on"
        and prod_mode != "emergency"
        and bp_mode != "emergency"
        and stress_flag != "critical"
    )

    if not reasons:
        reasons.append("Aucun signal de risque majeur détecté (gouvernance OK).")

    return GovernanceScore(
        score=round(score, 2),
        flag=flag,
        hard_block=hard_block,
        can_trade_recommended=can_trade_recommended,
        reasons=reasons,
    )


def main() -> None:
    data_dir = Path(get_data_dir())
    env = os.getenv("NSC_ENV", "PREPROD")
    logger.info("[governance_engine_pro] DATA_DIR=%s, env=%s", str(data_dir), env)

    # Inputs
    risk_engine, _ = _load_first_json(
        data_dir,
        rel_paths=["analysis/risk_engine_pro.json"],
        default=None,
    )

    risk_limits, risk_limits_path = _load_first_json(
        data_dir,
        rel_paths=["trading/risk_limits.json", "analysis/risk_limits.json", "trading/risk_engine_limits.json"],
        default=None,
    )
    if risk_limits_path:
        logger.info("[governance_engine_pro] risk_limits loaded from %s", risk_limits_path)

    weak_signals, _ = _load_first_json(
        data_dir,
        rel_paths=["analysis/weak_signals_engine_pro.json", "analysis/weak_signals_engine.json", "analysis/weak_signals.json"],
        default=None,
    )

    meta_score, meta_path = _load_first_json(
        data_dir,
        rel_paths=["analysis/meta_score_engine_pro.json", "analysis/meta_score_pro.json"],
        default=None,
    )
    if meta_path and meta_path != "analysis/meta_score_engine_pro.json":
        logger.warning("[governance_engine_pro] meta_score loaded from legacy path: %s", meta_path)

    stress_test, _ = _load_first_json(
        data_dir,
        rel_paths=["analysis/stress_test_engine_pro.json", "analysis/stress_test_engine.json", "analysis/stress_test.json"],
        default=None,
    )

    logs_overview, _ = _load_first_json(
        data_dir,
        rel_paths=["analysis/logs_overview_light.json", "telemetry/system_metrics.json"],
        default=None,
    )

    backpressure_state, _ = _load_first_json(
        data_dir,
        rel_paths=["telemetry/backpressure_state.json", "analysis/backpressure_state.json"],
        default=None,
    )

    production_protocol, _ = _load_first_json(
        data_dir,
        rel_paths=["telemetry/production_protocol.json", "telemetry/production_protocol_state.json", "analysis/production_protocol.json"],
        default=None,
    )

    kill_switch, _ = _load_first_json(
        data_dir,
        rel_paths=["trading/kill_switch.json"],
        default=None,
    )

    gov = compute_governance_score(
        risk_engine=risk_engine,
        risk_limits=risk_limits,
        weak_signals=weak_signals,
        meta_score=meta_score,
        stress_test=stress_test,
        logs_overview=logs_overview,
        backpressure_state=backpressure_state,
        production_protocol=production_protocol,
        kill_switch=kill_switch,
    )

    now = _now_utc_str()
    result: Dict[str, Any] = {
        "timestamp": now,
        "env": env,
        "score": gov.score,
        "flag": gov.flag,
        "hard_block": gov.hard_block,
        "can_trade_recommended": gov.can_trade_recommended,
        "reasons": gov.reasons,
        "inputs": {
            "risk_engine": risk_engine,
            "risk_limits": risk_limits,
            "weak_signals": weak_signals,
            "meta_score": meta_score,
            "stress_test": stress_test,
            "logs_overview": logs_overview,
            "backpressure_state": backpressure_state,
            "production_protocol": production_protocol,
            "kill_switch": kill_switch,
        },
    }


    # NSC_PATCH: correlation_gate_hard_block_v3 BEGIN
    try:
        _data_dir = Path(data_dir) if isinstance(data_dir, Path) else Path(str(data_dir))
        _corr = load_json_file(_data_dir / "analysis" / "correlation_regime_engine_pro.json", default={})
        _gate = load_json_file(_data_dir / "state" / "correlation_gate_state.json", default={})
        gate_active = bool(_gate.get("active")) if isinstance(_gate, dict) else False
    
        if isinstance(result, dict):
            cm = _corr.get("metrics") if isinstance(_corr, dict) and isinstance(_corr.get("metrics"), dict) else {}
            result["correlation"] = {
                "regime": (_corr.get("regime") if isinstance(_corr, dict) else None),
                "global_flag": (_corr.get("global_flag") if isinstance(_corr, dict) else None),
                "score": (_corr.get("score") if isinstance(_corr, dict) else None),
                "nb_pairs": (_corr.get("nb_pairs") if isinstance(_corr, dict) else None) or cm.get("nb_pairs"),
                "avg_abs_corr": (_corr.get("avg_abs_corr") if isinstance(_corr, dict) else None) or cm.get("avg_abs_corr"),
                "share_high_corr": cm.get("share_high_corr"),
                "macro_risk_level": (_corr.get("macro_risk_level") if isinstance(_corr, dict) else None),
                "gate": {
                    "active": gate_active,
                    "regime": (_gate.get("regime") if isinstance(_gate, dict) else None),
                    "score": (_gate.get("score") if isinstance(_gate, dict) else None),
                },
            }
    
            if gate_active:
                result["hard_block"] = True
                rs = result.get("reasons")
                if not isinstance(rs, list):
                    rs = []
                if "correlation_gate_state.active=true" not in rs:
                    rs.append("correlation_gate_state.active=true")
                result["reasons"] = rs
    except Exception:
        logger.exception("[governance_engine_pro] correlation gate hard_block failed")
    # NSC_PATCH: correlation_gate_hard_block_v3 END

    out_path = data_dir / "analysis" / "governance_engine_pro.json"

    save_json_file(out_path, result)

    logger.info(
        "[governance_engine_pro] governance_engine_pro.json sauvegardé (%s, score=%.2f, can_trade_recommended=%s)",
        gov.flag,
        gov.score,
        gov.can_trade_recommended,
    )

    # Publish event (best-effort)
    try:
        from src.v2.utils.event_bus import publish_event
        severity = "critical" if gov.hard_block else ("warning" if gov.flag != "ok" else "info")
        ok = publish_event(
            event_type="governance.state",
            source="governance_engine_pro",
            severity=severity,
            payload={
                "timestamp": now,
                "env": env,
                "flag": gov.flag,
                "score": gov.score,
                "hard_block": gov.hard_block,
                "can_trade_recommended": gov.can_trade_recommended,
                "reasons": gov.reasons,
            },
        )
        if ok:
            logger.info("[governance_engine_pro] Event publié – type=governance.state source=governance_engine_pro severity=%s", severity)
        else:
            logger.warning("[governance_engine_pro] Event NON publié (event_bus indisponible).")
    except Exception as exc:
        logger.warning("[governance_engine_pro] publish_event skipped (error=%s)", exc)


if __name__ == "__main__":
    main()
