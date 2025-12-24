# src/v2/monitoring/daily_loop_engine_pro.py

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
    get_data_dir,
)
from src.v2.utils.logger import get_logger
from src.v2.core.message_bus import publish_event

logger = get_logger("daily_loop_engine_pro")


@dataclass
class DailyLoopInputs:
    env: str
    phase: str
    orchestrator: Dict[str, Any]
    governance: Dict[str, Any]
    risk_limits: Dict[str, Any]
    backpressure: Dict[str, Any]
    production_protocol: Dict[str, Any]
    stress_summary: Dict[str, Any]
    kill_switch: Dict[str, Any]


@dataclass
class DailyLoopState:
    timestamp: str
    env: str
    phase: str
    flag: str
    can_trade: bool
    reasons: List[str]
    # Snapshots des sous-moteurs
    orchestrator_mode: Optional[str] = None
    orchestrator_can_trade: Optional[bool] = None
    governance_flag: Optional[str] = None
    governance_score: Optional[float] = None
    risk_mode: Optional[str] = None
    risk_on_off: Optional[str] = None
    backpressure_mode: Optional[str] = None
    production_mode: Optional[str] = None
    stress_global_flag: Optional[str] = None
    stress_nb_breaches: Optional[int] = None
    stress_worst_drawdown_pct: Optional[float] = None
    kill_switch_enabled: Optional[bool] = None
    kill_switch_mode: Optional[str] = None


def utc_now_iso() -> str:
    """Retourne un timestamp ISO8601 en UTC, sans offset (+00:00)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def detect_phase(now: Optional[datetime] = None) -> str:
    """
    Détecte la phase du cycle journalier en fonction de l'heure (UTC).

    - 00h–06h : pre_flight
    - 06h–16h : core_session
    - 16h–20h : closing
    - 20h–24h : post_close
    """
    if now is None:
        now = datetime.now(timezone.utc)

    hour = now.hour

    if 0 <= hour < 6:
        return "pre_flight"
    if 6 <= hour < 16:
        return "core_session"
    if 16 <= hour < 20:
        return "closing"
    return "post_close"


def load_inputs(data_dir: Path) -> DailyLoopInputs:
    env = os.environ.get("NSC_ENV", "PREPROD")

    telemetry_dir = data_dir / "telemetry"
    analysis_dir = data_dir / "analysis"
    trading_dir = data_dir / "trading"

    orchestrator = load_json_file(telemetry_dir / "orchestrator_pro.json", default={})
    governance = load_json_file(analysis_dir / "governance_engine_pro.json", default={})
    risk_limits = load_json_file(trading_dir / "risk_limits.json", default={})
    backpressure = load_json_file(telemetry_dir / "backpressure_state.json", default={})
    production_protocol = load_json_file(telemetry_dir / "production_protocol.json", default={})
    stress = load_json_file(analysis_dir / "stress_test_engine.json", default={})
    kill_switch = load_json_file(trading_dir / "kill_switch.json", default={})

    stress_summary = stress.get("summary", stress)

    phase = detect_phase()

    return DailyLoopInputs(
        env=env,
        phase=phase,
        orchestrator=orchestrator or {},
        governance=governance or {},
        risk_limits=risk_limits or {},
        backpressure=backpressure or {},
        production_protocol=production_protocol or {},
        stress_summary=stress_summary or {},
        kill_switch=kill_switch or {},
    )


def compute_state(inputs: DailyLoopInputs) -> DailyLoopState:
    reasons: List[str] = []

    orch_mode = inputs.orchestrator.get("mode")
    orch_can_trade = inputs.orchestrator.get("can_trade")
    gov_flag = inputs.governance.get("flag") or inputs.governance.get("governance_flag")
    gov_score = inputs.governance.get("score") or inputs.governance.get("governance_score")
    risk_mode = inputs.risk_limits.get("risk_mode")
    risk_on_off = inputs.risk_limits.get("risk_on_off")
    backpressure_mode = inputs.backpressure.get("mode")
    production_mode = inputs.production_protocol.get("mode")
    stress_flag = inputs.stress_summary.get("global_flag")
    stress_nb_breaches = inputs.stress_summary.get("nb_breaches")
    stress_worst_dd = inputs.stress_summary.get("worst_drawdown_pct")
    kill_switch_enabled = inputs.kill_switch.get("enabled")
    kill_switch_mode = inputs.kill_switch.get("mode")

    # 1) Base : état de l’orchestrateur
    if orch_mode in ("emergency", "degraded"):
        reasons.append(f"orchestrator.mode={orch_mode}")
    if orch_can_trade is False:
        reasons.append("orchestrator.can_trade=False")

    # 2) Gouvernance
    if gov_flag == "hard_block":
        reasons.append("governance.flag=hard_block")
    can_trade_recommended = inputs.governance.get("can_trade_recommended")
    if can_trade_recommended is False:
        reasons.append("governance.can_trade_recommended=False")

    # 3) Risk Engine / risk_limits
    if risk_on_off == "off":
        reasons.append("risk_on_off=off")
    if risk_mode in ("reduced", "emergency"):
        reasons.append(f"risk_mode={risk_mode}")

    # 4) Backpressure
    if backpressure_mode and backpressure_mode != "normal":
        reasons.append(f"backpressure.mode={backpressure_mode}")

    # 5) Stress Test
    if stress_flag == "critical":
        reasons.append("stress_test.global_flag=critical")

    # 6) Kill switch global
    if kill_switch_enabled:
        reasons.append(f"kill_switch.enabled=True ({kill_switch_mode})")

    # 7) Phase journalière
    phase = inputs.phase
    if phase != "core_session":
        # on marque cette info mais on ne force pas un hard block par défaut
        reasons.append(f"phase={phase} (hors core_session)")

    # Détermination du flag global et can_trade
    # ----------------------------------------
    # Priorité absolue : hard blocks et risk_on_off=off
    hard_block_conditions = [
        orch_mode == "emergency",
        gov_flag == "hard_block",
        can_trade_recommended is False,
        risk_on_off == "off",
        stress_flag == "critical",
    ]

    if any(hard_block_conditions):
        flag = "hard_block"
        can_trade = False
    else:
        # Si tout est normal côté orchestrateur / stress / risk, on regarde la phase
        if orch_mode == "normal" and stress_flag in (None, "ok"):
            if phase == "core_session":
                flag = "ok"
                can_trade = True
            else:
                flag = "caution"
                # on conserve la possibilité de rester strict : pas de trade hors core
                can_trade = False
        else:
            flag = "caution"
            can_trade = False

    # Construction de l’état
    state = DailyLoopState(
        timestamp=utc_now_iso(),
        env=inputs.env,
        phase=phase,
        flag=flag,
        can_trade=can_trade,
        reasons=reasons,
        orchestrator_mode=orch_mode,
        orchestrator_can_trade=orch_can_trade,
        governance_flag=gov_flag,
        governance_score=gov_score,
        risk_mode=risk_mode,
        risk_on_off=risk_on_off,
        backpressure_mode=backpressure_mode,
        production_mode=production_mode,
        stress_global_flag=stress_flag,
        stress_nb_breaches=stress_nb_breaches,
        stress_worst_drawdown_pct=stress_worst_dd,
        kill_switch_enabled=kill_switch_enabled,
        kill_switch_mode=kill_switch_mode,
    )

    return state


def main() -> None:
    try:
        data_dir = get_data_dir()
        logger.info("[daily_loop_engine_pro] DATA_DIR=%s", data_dir)

        inputs = load_inputs(data_dir)
        state = compute_state(inputs)

        telemetry_dir = Path(data_dir) / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        output_path = telemetry_dir / "daily_loop_engine_pro.json"
        save_json_file(output_path, asdict(state))

        logger.info(
            "[daily_loop_engine_pro] daily_loop_engine_pro.json sauvegardé "
            "(phase=%s, flag=%s, can_trade=%s)",
            state.phase,
            state.flag,
            state.can_trade,
        )

        # Publication sur le message bus
        publish_event(
            "daily_loop.state",
            "daily_loop_engine_pro",
            payload=asdict(state),
            severity="info" if state.flag == "ok" else "warning" if state.flag == "caution" else "critical",
        )

    except Exception:
        logger.exception("[daily_loop_engine_pro] Erreur inattendue dans Daily Loop Engine PRO")
        raise


if __name__ == "__main__":
    main()
