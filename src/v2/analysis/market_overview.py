import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.v2.utils.logger import get_logger

logger = get_logger("market_overview")

ENV = os.getenv("NSC_ENV") or os.getenv("ENV", "LOCAL")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/opt/nsc/app/data"))
REPORTS_DIR = DATA_ROOT / "reports"


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        if not path.exists():
            logger.warning(f"[market_overview] Fichier manquant: {path}")
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"[market_overview] Erreur lecture {path}: {e}")
        return default


def compute_risk_and_regimes(
    market_regime: dict,
    micro: dict,
    orderflow: dict,
) -> dict:
    """Construit risk_score, kill_switch, governor_mode, allocation."""
    # --- 1) Base sur market_regime.json ---
    regime = (market_regime.get("regime") or "neutral").lower()
    inputs = market_regime.get("inputs") or {}

    if regime == "bull":
        base_risk = 35
    elif regime == "bear":
        base_risk = 70
    else:
        base_risk = 50

    risk_score = float(base_risk)

    # --- 2) Microstructure ---
    micro_info = inputs.get("microstructure") or {}
    micro_regime = (micro_info.get("microstructure_regime") or "unknown").lower()
    n_assets = int(micro_info.get("n_assets") or 0)
    frac_low_liq = float(micro_info.get("frac_low_liquidity") or 0.0)

    if micro_regime == "bad":
        risk_score += 15
    elif micro_regime == "ok":
        risk_score += 5
    elif micro_regime == "good":
        risk_score -= 10

    # surcharge si beaucoup d’assets illiquides
    if n_assets > 0 and frac_low_liq > 0.5:
        risk_score += 5
    if n_assets > 0 and frac_low_liq > 0.75:
        risk_score += 5

    # --- 3) Orderflow ---
    of_summary = orderflow.get("summary") or {}
    orderflow_regime = (of_summary.get("orderflow_regime") or "unknown").lower()
    nb_high_spoof = int(of_summary.get("nb_high_spoof") or 0)
    nb_med_spoof = int(of_summary.get("nb_medium_spoof") or 0)

    if orderflow_regime == "stressed":
        risk_score += 15
    elif orderflow_regime == "hot":
        risk_score += 10
    elif orderflow_regime == "calm":
        risk_score -= 5

    if nb_high_spoof > 0:
        risk_score += 10
    elif nb_med_spoof > 0:
        risk_score += 5

    # --- 4) Macro score (si présent dans market_regime.json) ---
    macro_score = float(inputs.get("macro_score") or 0.0)
    # convention : macro_score > 0 = macro plus risquée
    risk_score += macro_score * 0.5

    # clamp 0–100
    risk_score = max(0.0, min(100.0, risk_score))

    # --- 5) Kill Switch ---
    # 0 = normal, 1 = soft, 2 = medium, 3 = hard
    if risk_score >= 90:
        kill_level = 3
        kill_reason = "Risque extrême (risk_score>=90)"
    elif risk_score >= 75 and (micro_regime == "bad" or orderflow_regime in {"stressed", "hot"}):
        kill_level = 2
        kill_reason = "Risque élevé avec microstructure/flux dégradés"
    elif risk_score >= 60:
        kill_level = 1
        kill_reason = "Risque modéré à élevé (risk_score>=60)"
    else:
        kill_level = 0
        kill_reason = "Risque maîtrisé"

    # --- 6) Governor Mode (global trading stance) ---
    if risk_score <= 40:
        governor_mode = "aggressive"
    elif risk_score <= 60:
        governor_mode = "neutral"
    elif risk_score <= 75:
        governor_mode = "defensive"
    else:
        governor_mode = "hedge"

    # --- 7) Allocation capital ---
    # Règles figées NSC (Bull/Bear/Neutral)
    if kill_level >= 2:
        # Mode ultra défensif forcé
        allocation_regime = "crisis"
        allocation = {
            "trading_pct": 0.10,
            "long_term_pct": 0.40,
            "security_pct": 0.45,
            "bfr_pct": 0.05,
        }
    else:
        if regime == "bull" and governor_mode in {"aggressive", "neutral"}:
            allocation_regime = "bull"
            allocation = {
                "trading_pct": 0.65,
                "long_term_pct": 0.25,
                "security_pct": 0.03,
                "bfr_pct": 0.07,
            }
        elif regime == "bear" or governor_mode in {"defensive", "hedge"}:
            allocation_regime = "bear"
            allocation = {
                "trading_pct": 0.25,
                "long_term_pct": 0.50,
                "security_pct": 0.20,
                "bfr_pct": 0.05,
            }
        else:
            # neutral
            allocation_regime = "neutral"
            allocation = {
                "trading_pct": 0.45,
                "long_term_pct": 0.35,
                "security_pct": 0.15,
                "bfr_pct": 0.05,
            }

    # sécurité : normalisation à 1.0
    total = sum(allocation.values())
    if total > 0:
        allocation = {k: v / total for k, v in allocation.items()}

    return {
        "risk_score": round(risk_score, 2),
        "kill_switch": {
            "level": kill_level,
            "reason": kill_reason,
        },
        "governor": {
            "mode": governor_mode,
        },
        "allocation": {
            "regime": allocation_regime,
            **allocation,
        },
        "source": {
            "market_regime_file": "market_regime.json",
            "microstructure_file": "microstructure_score.json",
            "orderflow_file": "orderflow_report.json",
        },
        "raw": {
            "market_regime": market_regime,
            "microstructure": micro,
            "orderflow": orderflow,
        },
    }


def main():
    logger.info(f"[market_overview] Démarrage – ENV={ENV} DATA_ROOT={DATA_ROOT}")

    market_regime_path = REPORTS_DIR / "market_regime.json"
    micro_path = REPORTS_DIR / "microstructure_score.json"
    orderflow_path = REPORTS_DIR / "orderflow_report.json"

    market_regime = load_json(market_regime_path, default={})
    micro = load_json(micro_path, default={})
    orderflow = load_json(orderflow_path, default={})

    overview = compute_risk_and_regimes(market_regime, micro, orderflow)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": ENV,
        **overview,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "market_overview.json"
    try:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        logger.info(f"[market_overview] Rapport sauvegardé dans {out_path}")
    except Exception as e:
        logger.exception(f"[market_overview] Erreur écriture {out_path}: {e}")


if __name__ == "__main__":
    main()
