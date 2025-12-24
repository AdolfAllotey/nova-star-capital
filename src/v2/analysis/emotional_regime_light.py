from __future__ import annotations

import math
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("emotional_regime_light")

# =====================================================================
#  Chemins
# =====================================================================

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"

TRADING_DIR = DATA_DIR / "trading"
ANALYSIS_DIR = DATA_DIR / "analysis"
REPORTS_DIR = DATA_DIR / "reports"

LOOKBACK_DAYS = 7


# =====================================================================
#  Helpers génériques
# =====================================================================

def _safe_load(path: Path, default: Any) -> Any:
    data = load_json_file(path, default=default)
    # robustesse : si le type ne correspond pas, on renvoie le default
    if default is None:
        return data
    if not isinstance(data, type(default)):
        return default
    return data


def _today_iso() -> str:
    return date.today().isoformat()


def _parse_ts_to_date_str(ts: str) -> str | None:
    """
    Essaie de convertir un timestamp en 'YYYY-MM-DD'.
    Accepte :
    - 'YYYY-MM-DD'
    - ISO complet 'YYYY-MM-DDTHH:MM:SS...'
    """
    if not ts:
        return None
    ts = str(ts)
    if len(ts) >= 10:
        return ts[:10]
    return None


# =====================================================================
#  Lecture des exit_events et calcul des stats 7j
# =====================================================================

def _load_exit_events() -> List[Dict[str, Any]]:
    events = _safe_load(TRADING_DIR / "exit_events.json", default=[])
    if not isinstance(events, list):
        return []
    return events


def _filter_last_7_days(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtre les événements sur les 7 derniers jours (approche simple sur la date).
    On regarde 'closed_at' ou 'timestamp'.
    """
    if not events:
        return []

    now = datetime.now(timezone.utc).date()
    min_date = now - timedelta(days=LOOKBACK_DAYS)

    filtered: List[Dict[str, Any]] = []
    for ev in events:
        ts = ev.get("closed_at") or ev.get("timestamp")
        if not ts:
            continue
        d_str = _parse_ts_to_date_str(str(ts))
        if not d_str:
            continue
        try:
            year, month, day = [int(x) for x in d_str.split("-")]
            d = date(year, month, day)
        except Exception:
            continue
        if d >= min_date:
            filtered.append(ev)

    return filtered


def _compute_stats_7d(events_7d: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcule :
    - realized_pnl_7d (EUR)
    - realized_pnl_7d_pct (si info de capital dispo, sinon 0)
    - nb_trades_7d
    - winrate_7d
    - losing_streak_current
    - overtrading (nb_trades_7d > seuil)
    """

    if not events_7d:
        stats = {
            "realized_pnl_7d": 0.0,
            "realized_pnl_7d_pct": 0.0,
            "nb_trades_7d": 0,
            "winrate_7d": 0.0,
            "losing_streak_current": 0,
            "overtrading": False,
        }
        logger.info(
            "[emotional_regime_light] Stats 7d: pnl_7d=%.2f (%.2f%%), nb_trades=%d, winrate=%.1f%%, losing_streak=%d, overtrading=%s",
            stats["realized_pnl_7d"],
            stats["realized_pnl_7d_pct"],
            stats["nb_trades_7d"],
            stats["winrate_7d"],
            stats["losing_streak_current"],
            stats["overtrading"],
        )
        return stats

    realized_pnl_7d = 0.0
    nb_trades_7d = 0
    nb_wins = 0

    # On va aussi calculer la losing streak "courante"
    # en parcourant les trades dans l'ordre chronologique inverse
    # (du plus récent au plus ancien).
    def _event_date(ev: Dict[str, Any]) -> str:
        ts = ev.get("closed_at") or ev.get("timestamp") or ""
        d = _parse_ts_to_date_str(str(ts)) or "0000-00-00"
        return d

    sorted_events = sorted(events_7d, key=_event_date, reverse=True)

    losing_streak_current = 0
    for ev in sorted_events:
        pnl = float(ev.get("realized_pnl", 0.0) or 0.0)
        realized_pnl_7d += pnl
        nb_trades_7d += 1
        if pnl > 0:
            nb_wins += 1

    # losing streak : on recompte depuis le plus récent jusqu'à tomber
    # sur un trade >= 0
    losing_streak_current = 0
    for ev in sorted_events:
        pnl = float(ev.get("realized_pnl", 0.0) or 0.0)
        if pnl < 0:
            losing_streak_current += 1
        else:
            break

    winrate_7d = (nb_wins / nb_trades_7d * 100.0) if nb_trades_7d > 0 else 0.0

    # Overtrading : règle simple
    overtrading = nb_trades_7d > 20

    # PnL % très light : faute de capital, on laisse 0
    realized_pnl_7d_pct = 0.0

    stats = {
        "realized_pnl_7d": realized_pnl_7d,
        "realized_pnl_7d_pct": realized_pnl_7d_pct,
        "nb_trades_7d": nb_trades_7d,
        "winrate_7d": winrate_7d,
        "losing_streak_current": losing_streak_current,
        "overtrading": overtrading,
    }

    logger.info(
        "[emotional_regime_light] Stats 7d: pnl_7d=%.2f (%.2f%%), nb_trades=%d, winrate=%.1f%%, losing_streak=%d, overtrading=%s",
        realized_pnl_7d,
        realized_pnl_7d_pct,
        nb_trades_7d,
        winrate_7d,
        losing_streak_current,
        overtrading,
    )

    return stats


# =====================================================================
#  Dérivation du régime émotionnel
# =====================================================================

def _derive_emotional_regime(
    realized_pnl_7d: float,
    realized_pnl_7d_pct: float,
    nb_trades_7d: int,
    winrate_7d: float,
    losing_streak_current: int,
    overtrading: bool,
    meta_score_nsc: float,
) -> Dict[str, Any]:
    """
    Règles simples pour déterminer l'état émotionnel.
    - calm : par défaut
    - stressed : pertes récentes / losing streak / drawdown
    - euphoric : gros gains & bon winrate
    - overtrading : volume de trades trop élevé
    """

    # Valeurs par défaut
    regime = "calm"
    score_emotional = 80.0
    notes = "aucun signal psychologique majeur (calm)"
    action = "normal"

    # Règles de base
    # 1) Stressed : pertes significatives ou losing streak
    if realized_pnl_7d < -500 or losing_streak_current >= 3:
        regime = "stressed"
        score_emotional = 55.0
        notes = (
            "pertes récentes ou série de trades perdants — risque de tilt "
            "(stressed)"
        )
        action = "reduce_size"

    # 2) Euphoric : gros gains + bon winrate
    if realized_pnl_7d > 500 and winrate_7d >= 60.0:
        regime = "euphoric"
        score_emotional = 60.0
        notes = (
            "gains importants avec bon winrate — risque de surconfiance "
            "(euphoric)"
        )
        action = "lock_gains"

    # 3) Overtrading : beaucoup de trades en peu de temps
    if overtrading:
        regime = "overtrading"
        score_emotional = 50.0
        notes = (
            "nombre de trades élevé — risque de perte de discipline "
            "(overtrading)"
        )
        action = "pause_or_reduce"

    logger.info(
        "[emotional_regime_light] Emotional regime : %s (score=%.1f, action=%s)",
        regime,
        score_emotional,
        action,
    )

    return {
        "regime": regime,
        "score_emotional": score_emotional,
        "notes": notes,
        "recommended_action": action,
    }


# =====================================================================
#  API principale
# =====================================================================

def compute_emotional_regime() -> Dict[str, Any]:
    """
    Calcule le régime émotionnel global sur la base :
    - des exit_events des 7 derniers jours
    - du meta_score_nsc (daily_trading_feedback)
    """

    now = datetime.now(timezone.utc)

    # 1) Charger les exit events
    exit_events_all = _load_exit_events()
    events_7d = _filter_last_7_days(exit_events_all)
    stats = _compute_stats_7d(events_7d)

    # 2) Charger le meta_score_nsc depuis daily_trading_feedback
    feedback = _safe_load(REPORTS_DIR / "daily_trading_feedback.json", default={})
    try:
        meta_score_nsc = float(feedback.get("meta_score_nsc", 0.0) or 0.0)
    except Exception:
        meta_score_nsc = 0.0

    # 3) Dériver le régime émotionnel
    regime_info = _derive_emotional_regime(
        realized_pnl_7d=stats["realized_pnl_7d"],
        realized_pnl_7d_pct=stats["realized_pnl_7d_pct"],
        nb_trades_7d=stats["nb_trades_7d"],
        winrate_7d=stats["winrate_7d"],
        losing_streak_current=stats["losing_streak_current"],
        overtrading=stats["overtrading"],
        meta_score_nsc=meta_score_nsc,
    )

    result: Dict[str, Any] = {
        "timestamp": now.isoformat(),
        "regime": regime_info["regime"],
        "score_emotional": regime_info["score_emotional"],
        "realized_pnl_7d": stats["realized_pnl_7d"],
        "realized_pnl_7d_pct": stats["realized_pnl_7d_pct"],
        "nb_trades_7d": stats["nb_trades_7d"],
        "winrate_7d": stats["winrate_7d"],
        "losing_streak_current": stats["losing_streak_current"],
        "overtrading": stats["overtrading"],
        "meta_score_nsc": meta_score_nsc,
        "notes": regime_info["notes"],
        "recommended_action": regime_info["recommended_action"],
    }

    return result


def save_emotional_regime(regime: Dict[str, Any]) -> Path:
    """
    Sauvegarde du fichier emotional_regime.json dans data/analysis.
    """
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS_DIR / "emotional_regime.json"
    save_json_file(path, regime)
    logger.info(
        "[emotional_regime_light] emotional_regime.json mis à jour (%s).",
        path,
    )
    return path


def main() -> None:
    logger.info("[emotional_regime_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)
    regime = compute_emotional_regime()
    save_emotional_regime(regime)


if __name__ == "__main__":
    main()
