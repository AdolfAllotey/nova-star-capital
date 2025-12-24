import os
from datetime import datetime, timezone

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = get_logger(__name__)


def _compute_emotional_regime(backpressure_state: dict, production_protocol: dict) -> dict:
    """
    Détermine un régime émotionnel simple (calm/stressed/panic) et un score 0–100.
    """
    mode = (backpressure_state.get("mode") or backpressure_state.get("state") or "").lower()
    reasons = []

    # Base : calm
    regime = "calm"
    score = 70.0

    if mode in {"emergency", "critical"}:
        regime = "panic"
        score = 30.0
        reasons.append(f"Backpressure mode = '{mode}'.")
    elif mode in {"degraded", "warning"}:
        regime = "stressed"
        score = 50.0
        reasons.append(f"Backpressure mode = '{mode}'.")
    else:
        if mode:
            reasons.append(f"Backpressure mode = '{mode}' (considéré safe).")
        else:
            reasons.append("Backpressure mode inconnu, fallback calm.")

    # On regarde aussi le mode global de production
    prod_mode = (production_protocol.get("mode") or production_protocol.get("global_mode") or "").lower()
    if prod_mode in {"emergency", "critical"}:
        score -= 20.0
        reasons.append(f"Production mode = '{prod_mode}' (emergency/critical).")
    elif prod_mode in {"degraded", "warning"}:
        score -= 10.0
        reasons.append(f"Production mode = '{prod_mode}' (degraded/warning).")

    score = max(0.0, min(100.0, score))

    # Flag émotionnel pour lier avec la gouvernance si besoin
    if score >= 65.0:
        flag = "calm"
    elif score >= 40.0:
        flag = "stressed"
    else:
        flag = "panic"

    return {
        "score": round(score, 2),
        "regime": regime,
        "flag": flag,
        "reasons": reasons,
        "backpressure_mode": mode or "unknown",
        "production_mode": prod_mode or "unknown",
    }


def main() -> None:
    data_dir = get_data_dir()
    analysis_dir = os.path.join(data_dir, "analysis")
    telemetry_dir = os.path.join(data_dir, "telemetry")
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(telemetry_dir, exist_ok=True)

    logger.info("[emotional_regime_light] DATA_DIR=%s", data_dir)

    backpressure_path = os.path.join(telemetry_dir, "backpressure_state.json")
    production_protocol_path = os.path.join(telemetry_dir, "production_protocol.json")

    backpressure_state = load_json_file(backpressure_path, default={})
    production_protocol = load_json_file(production_protocol_path, default={})

    metrics = _compute_emotional_regime(backpressure_state, production_protocol)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": "emotional_regime_light",
        "score": metrics["score"],
        "regime": metrics["regime"],
        "flag": metrics["flag"],
        "details": {
            "backpressure_mode": metrics["backpressure_mode"],
            "production_mode": metrics["production_mode"],
            "reasons": metrics["reasons"],
        },
    }

    out_path = os.path.join(analysis_dir, "emotional_regime_light.json")
    save_json_file(out_path, payload)
    logger.info(
        "[emotional_regime_light] emotional_regime_light.json sauvegardé (%s, regime=%s, score=%.2f, flag=%s)",
        out_path,
        metrics["regime"],
        metrics["score"],
        metrics["flag"],
    )


if __name__ == "__main__":
    main()
