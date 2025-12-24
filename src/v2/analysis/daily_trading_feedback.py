"""
daily_trading_feedback.py

Synthèse quotidienne "humain lisible" de l'état du bot NSC :
- Régime de marché
- Régime émotionnel
- Discipline
- Console de risque
- Governor / Kill switch
- Logs / erreurs
- Weak signals & liquidité
- Stress test & anomalies

Sortie : data/analysis/daily_feedback.json
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
    get_logger,
)

logger = get_logger("daily_trading_feedback")


def _as_dict(obj: Any) -> Dict[str, Any]:
    """Retourne un dict, ou {} si ce n'en est pas un."""
    return obj if isinstance(obj, dict) else {}


def _load_safe(path: str, default: Any) -> Any:
    """Wrapper autour load_json_file avec default."""
    return load_json_file(path, default=default)


def _get_root_and_data_dirs() -> tuple[str, str]:
    """
    Déduit ROOT_DIR et DATA_DIR sans dépendre de fonctions spécifiques de file_utils.
    daily_trading_feedback.py est dans src/v2/analysis/ → on remonte 3 niveaux.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(here, "..", "..", ".."))
    data_dir = os.path.join(root_dir, "data")
    return root_dir, data_dir


def compute_daily_feedback(data_dir: str | None = None) -> Dict[str, Any]:
    """
    Compile un feedback quotidien synthétique pour le trader / opérateur NSC.
    """
    root_dir, inferred_data_dir = _get_root_and_data_dirs()
    if data_dir is None:
        data_dir = inferred_data_dir

    logger.info(
        "[daily_trading_feedback] ROOT_DIR=%s, DATA_DIR=%s",
        root_dir,
        data_dir,
    )

    analysis_dir = os.path.join(data_dir, "analysis")
    market_dir = os.path.join(data_dir, "market")
    trading_dir = os.path.join(data_dir, "trading")
    reports_dir = os.path.join(data_dir, "reports")

    # --- Chargement des différentes briques ---

    market_regime = _as_dict(
        _load_safe(os.path.join(market_dir, "market_regime.json"), default={})
    )
    emotional = _as_dict(
        _load_safe(os.path.join(analysis_dir, "emotional_regime.json"), default={})
    )
    discipline = _as_dict(
        _load_safe(os.path.join(analysis_dir, "discipline_overview.json"), default={})
    )
    risk_console = _as_dict(
        _load_safe(os.path.join(analysis_dir, "risk_console_overview.json"), default={})
    )
    governor = _as_dict(
        _load_safe(os.path.join(analysis_dir, "governor_overview.json"), default={})
    )
    logs_overview = _as_dict(
        _load_safe(os.path.join(analysis_dir, "logs_overview.json"), default={})
    )
    weak_signals = _as_dict(
        _load_safe(os.path.join(analysis_dir, "weak_signals_overview.json"), default={})
    )
    liquidity_risk = _as_dict(
        _load_safe(os.path.join(analysis_dir, "liquidity_risk_overview.json"), default={})
    )
    stress_test = _as_dict(
        _load_safe(os.path.join(analysis_dir, "stress_test_overview.json"), default={})
    )
    anomalies = _as_dict(
        _load_safe(os.path.join(analysis_dir, "anomaly_overview.json"), default={})
    )
    trading_checklist = _as_dict(
        _load_safe(os.path.join(reports_dir, "trading_checklist.json"), default={})
    )

    # --- Extraction des infos clés ---

    regime = market_regime.get("regime", "unknown")
    market_risk_mode = market_regime.get("risk_mode", "normal")

    emotional_regime = emotional.get("regime", "unknown")
    emotional_score = emotional.get("score_emotional", emotional.get("score", None))
    emotional_action = emotional.get("recommended_action", "normal")

    discipline_score = discipline.get(
        "score_discipline",
        discipline.get("score", None),
    )
    discipline_flag = discipline.get("flag", "unknown")

    risk_flag = risk_console.get("global_flag", "unknown")

    governor_flag = governor.get("global_flag", "unknown")
    kill_enabled = bool(governor.get("kill_switch_enabled", False))
    kill_mode = governor.get("kill_switch_mode", governor.get("mode", "soft"))
    governor_reason = governor.get("reason", "")

    logs_flag = logs_overview.get("flag", "unknown")
    logs_reason = logs_overview.get("reason", "")
    total_counts = logs_overview.get("total_counts", {})

    ws_nb_assets = weak_signals.get("nb_assets", 0)
    ws_nb_watch = weak_signals.get("nb_weak_watch", 0)
    ws_nb_avoid = weak_signals.get("nb_weak_avoid", 0)

    liq_flag = liquidity_risk.get("global_flag", "unknown")
    liq_nb_risk = liquidity_risk.get("nb_risk", 0)
    liq_nb_watch = liquidity_risk.get("nb_watch", 0)

    stress_score = stress_test.get("stress_score", None)
    stress_flag = stress_test.get("risk_flag", "unknown")

    nb_anomalies = anomalies.get("nb_anomalies", 0)
    nb_crit = anomalies.get("nb_critical", 0)
    nb_warn = anomalies.get("nb_warning", 0)

    checklist_score = trading_checklist.get("score", None)
    checklist_all_ok = trading_checklist.get("all_ok", None)

    # --- Headline ---

    headline_parts: List[str] = []

    if kill_enabled:
        headline_parts.append("⚠️ Kill switch ACTIVÉ")
    elif governor_flag in ("hard_block", "soft_block"):
        headline_parts.append("🟠 Gouvernance en mode blocage léger")
    else:
        headline_parts.append("🟢 Gouvernance OK")

    if regime == "bull":
        headline_parts.append("marché BULL (risk_on)")
    elif regime == "bear":
        headline_parts.append("marché BEAR (risk_off)")
    elif regime == "neutral":
        headline_parts.append("marché neutre")
    else:
        headline_parts.append("régime marché inconnu")

    if discipline_score is not None:
        headline_parts.append(f"discipline ≈ {discipline_score:.1f}/100")
    if emotional_regime != "unknown":
        headline_parts.append(f"émotionnel: {emotional_regime}")

    headline = " | ".join(headline_parts)

    # --- Actions recommandées ---

    actions: List[str] = []

    if kill_enabled:
        actions.append(
            f"✅ Kill switch activé ({kill_mode}) – aucune nouvelle prise de position recommandée. Motif: {governor_reason or 'non précisé'}."
        )
    elif governor_flag in ("hard_block", "soft_block"):
        actions.append(
            f"⚠️ Gouvernance en mode {governor_flag} – réduire la voilure, éviter de nouvelles expositions agressives. Motif: {governor_reason or 'voir risk console'}."
        )
    else:
        actions.append(
            "🟢 Gouvernance OK – le bot peut trader normalement sous réserve des autres signaux de risque."
        )

    if discipline_score is not None:
        if discipline_score < 60:
            actions.append(
                f"🔴 Discipline faible ({discipline_score:.1f}/100) – revoir les règles d'exécution, tailles de position, et respecter strictement les plans."
            )
        elif discipline_score < 80:
            actions.append(
                f"🟠 Discipline moyenne ({discipline_score:.1f}/100) – être vigilant sur les écarts au plan."
            )
        else:
            actions.append(
                f"🟢 Discipline solide ({discipline_score:.1f}/100) – conserver les routines actuelles."
            )

    if emotional_regime == "tilted":
        actions.append(
            "⚠️ Régime émotionnel TILTED – réduire les tailles, éviter de 'chasser' le marché, privilégier les setups A+ seulement."
        )
    elif emotional_regime == "stressed":
        actions.append(
            "🟠 Régime émotionnel stressé – prendre du recul, limiter le nombre de trades, faire une revue à froid avant la prochaine session."
        )
    elif emotional_regime == "calm":
        actions.append(
            "🟢 Régime émotionnel calme – conditions psychologiques favorables si la discipline reste élevée."
        )

    if logs_flag != "ok":
        actions.append(
            f"⚠️ Anomalies techniques dans les logs ({logs_flag}) – {logs_reason or 'vérifier les fichiers de logs détaillés.'}"
        )
    else:
        actions.append(
            f"ℹ️ Logs techniques OK – erreurs={total_counts.get('errors', 0)}, warnings={total_counts.get('warnings', 0)}."
        )

    if ws_nb_avoid > 0:
        actions.append(
            f"⚠️ {ws_nb_avoid} actifs en zone 'à éviter' selon le moteur de weak signals – ne pas forcer l'entrée sur ces tickers."
        )
    if ws_nb_watch > 0:
        actions.append(
            f"👀 {ws_nb_watch} actifs en zone 'à surveiller' – privilégier l'attente d'un signal plus propre avant d'engager du capital."
        )

    if liq_flag in ("watch", "risk"):
        actions.append(
            f"⚠️ Risque de liquidité ({liq_flag}) – {liq_nb_risk} actifs en zone rouge, {liq_nb_watch} en surveillance. Réduire la taille sur ces lignes."
        )

    if stress_flag != "ok":
        actions.append(
            f"⚠️ Stress test défavorable (score={stress_score}) – limiter les nouvelles expositions et considérer des prises de profit / allègements."
        )
    elif stress_score is not None:
        actions.append(
            f"🧪 Stress test satisfaisant (score={stress_score}) – portefeuille résilient aux scénarios testés."
        )

    if nb_crit > 0:
        actions.append(
            f"🔴 {nb_crit} anomalies critiques détectées – vérifier immédiatement les modules concernés."
        )
    elif nb_anomalies > 0:
        actions.append(
            f"🟠 {nb_anomalies} anomalies détectées (dont {nb_warn} warnings) – à investiguer dans la journée."
        )

    if checklist_all_ok is False:
        actions.append(
            f"🟠 Checklist trading incomplète (score={checklist_score}) – revoir au moins un point avant de lancer une nouvelle session."
        )
    elif checklist_all_ok:
        actions.append("✅ Checklist trading complétée – conditions minimales remplies.")

    now = datetime.now(timezone.utc).isoformat()

    feedback: Dict[str, Any] = {
        "timestamp": now,
        "headline": headline,
        "summary": {
            "market_regime": regime,
            "market_risk_mode": market_risk_mode,
            "emotional_regime": emotional_regime,
            "emotional_score": emotional_score,
            "emotional_action": emotional_action,
            "discipline_score": discipline_score,
            "discipline_flag": discipline_flag,
            "risk_console_flag": risk_flag,
            "governor_flag": governor_flag,
            "kill_switch_enabled": kill_enabled,
            "kill_switch_mode": kill_mode,
            "logs_flag": logs_flag,
            "weak_signals_watch": ws_nb_watch,
            "weak_signals_avoid": ws_nb_avoid,
            "liquidity_flag": liq_flag,
            "liquidity_nb_risk": liq_nb_risk,
            "stress_score": stress_score,
            "stress_flag": stress_flag,
            "nb_anomalies": nb_anomalies,
            "nb_critical": nb_crit,
            "nb_warning": nb_warn,
        },
        "actions": actions,
        "details": {
            "market_regime": market_regime,
            "emotional_regime": emotional,
            "discipline_overview": discipline,
            "risk_console_overview": risk_console,
            "governor_overview": governor,
            "logs_overview": logs_overview,
            "weak_signals_overview": weak_signals,
            "liquidity_risk_overview": liquidity_risk,
            "stress_test_overview": stress_test,
            "anomaly_overview": anomalies,
            "trading_checklist": trading_checklist,
        },
    }

    return feedback


def main() -> None:
    _, data_dir = _get_root_and_data_dirs()
    feedback = compute_daily_feedback(data_dir=data_dir)

    analysis_dir = os.path.join(data_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    output_path = os.path.join(analysis_dir, "daily_feedback.json")

    save_json_file(output_path, feedback)
    logger.info(
        "[daily_trading_feedback] daily_feedback.json sauvegardé (%s).",
        output_path,
    )


if __name__ == "__main__":
    main()
