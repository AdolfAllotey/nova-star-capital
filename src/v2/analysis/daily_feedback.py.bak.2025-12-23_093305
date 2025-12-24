"""
daily_feedback.py
---------------------------------
Feedback quotidien "hedge fund light" pour Nova Star Capital.

Objectif :
  - Consolider les infos clés de la journée :
      * régime de marché (bull/bear/neutral + risk_mode)
      * capital total & poche trading
      * stats signaux (nb assets momentum, nb signaux par type)
      * positions (nb positions, PnL latent & réalisé)
      * momentum moyen (avg_momentum_meta_score)
      * meta_score_nsc (0–100) = synthèse simple de l'état du système

  - Sauvegarder dans :
      data/reports/daily_trading_feedback.json

Ce fichier sert :
  - à l'API (/trading/feedback, /metrics)
  - aux gardes de risque (risk_limits.json) dans trading_kernel.py
  - à la supervision LLM / UI
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("daily_feedback")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"

MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"
TRADING_DIR = DATA_DIR / "trading"
REPORTS_DIR = DATA_DIR / "reports"

MARKET_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
TRADING_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MARKET_REGIME_FILE = MARKET_DIR / "market_regime.json"
CAP_ALLOC_FILE = TRADING_DIR / "capital_allocation.json"
MOMENTUM_SCORES_FILE = ANALYSIS_DIR / "momentum_scores.json"
SIGNAL_CANDIDATES_FILTERED_FILE = ANALYSIS_DIR / "signal_candidates_filtered.json"
SIGNAL_CANDIDATES_FILE = ANALYSIS_DIR / "signal_candidates.json"
SIGNAL_VOTES_FILE = ANALYSIS_DIR / "signal_votes.json"
OPEN_POSITIONS_FILE = TRADING_DIR / "open_positions.json"
EXIT_EVENTS_FILE = TRADING_DIR / "exit_events.json"

DAILY_FEEDBACK_FILE = REPORTS_DIR / "daily_trading_feedback.json"

logger.info(
    "[daily_feedback] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR
)

# ---------------------------------------------------------------------------
# file_utils fallback
# ---------------------------------------------------------------------------

try:
    from src.v2.utils.file_utils import load_json_file, save_json_file  # type: ignore
except Exception:  # pragma: no cover
    load_json_file = None
    save_json_file = None

    import json

    def _load_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception(
                "[daily_feedback] Erreur lors du chargement JSON: %s", path
            )
            return default

    def _save_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                import json as _json

                _json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.exception(
                "[daily_feedback] Erreur lors de l'écriture JSON: %s", path
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class DailyTradingFeedback:
    timestamp: str
    trading_date: str

    regime: str
    risk_mode: str

    total_capital: float
    trading_capital: float

    nb_assets_momentum: int
    nb_signals: int
    nb_signals_enter_long: int
    nb_signals_watch: int
    nb_signals_avoid: int

    nb_open_positions: int
    unrealized_pnl: float
    realized_pnl_today: float

    avg_momentum_meta_score: float
    meta_score_nsc: float
    meta_components: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers: chargement des inputs
# ---------------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _load_market_regime() -> Tuple[str, str]:
    data = _load_json(MARKET_REGIME_FILE, default={})
    if not isinstance(data, dict):
        return "neutral", "normal"
    regime = str(data.get("regime", "neutral")).lower()
    risk_mode = str(data.get("risk_mode", "normal")).lower()
    return regime, risk_mode


def _load_capital_allocation() -> Tuple[float, float]:
    data = _load_json(CAP_ALLOC_FILE, default={})
    if not isinstance(data, dict):
        return 0.0, 0.0
    total = _safe_float(data.get("total_capital", 0.0), 0.0)
    pockets = data.get("pockets", {})
    if not isinstance(pockets, dict):
        pockets = {}
    trading = _safe_float(pockets.get("trading", 0.0), 0.0)
    return total, trading


def _load_momentum_scores() -> List[Dict[str, Any]]:
    data = _load_json(MOMENTUM_SCORES_FILE, default=[])
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def _load_signals() -> List[Dict[str, Any]]:
    """
    Charge les signaux dans l'ordre de priorité :
      1) signal_candidates_filtered.json (sortie du ML)
      2) signal_candidates.json
      3) signal_votes.json
    """
    for path in (
        SIGNAL_CANDIDATES_FILTERED_FILE,
        SIGNAL_CANDIDATES_FILE,
        SIGNAL_VOTES_FILE,
    ):
        data = _load_json(path, default=None)
        if isinstance(data, list):
            signals = [d for d in data if isinstance(d, dict)]
            if signals:
                logger.info(
                    "[daily_feedback] Signaux chargés depuis %s (n=%d).",
                    path,
                    len(signals),
                )
                return signals
    logger.warning(
        "[daily_feedback] Aucun fichier de signaux trouvé (signal_candidates_filtered / signal_candidates / signal_votes)."
    )
    return []


def _load_open_positions() -> List[Dict[str, Any]]:
    data = _load_json(OPEN_POSITIONS_FILE, default=[])
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


def _load_exit_events() -> List[Dict[str, Any]]:
    data = _load_json(EXIT_EVENTS_FILE, default=[])
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


# ---------------------------------------------------------------------------
# Calcul PnL et métriques
# ---------------------------------------------------------------------------

def _compute_unrealized_pnl(open_positions: List[Dict[str, Any]]) -> float:
    """
    Tente de sommer un champ 'unrealized_pnl' par position si présent.
    Sinon retourne 0.0 (préprod).
    """
    pnl = 0.0
    for pos in open_positions:
        pnl += _safe_float(pos.get("unrealized_pnl", 0.0), 0.0)
    return pnl


def _compute_realized_pnl_today(exit_events: List[Dict[str, Any]]) -> float:
    """
    Somme les 'realized_pnl' des exit_events du jour courant (UTC),
    si ces champs existent.
    """
    if not exit_events:
        return 0.0

    today_str = date.today().isoformat()
    total = 0.0

    for ev in exit_events:
        ev_date = str(ev.get("exit_date", "") or ev.get("date", "")).split("T")[0]
        if ev_date != today_str:
            continue
        pnl = _safe_float(ev.get("realized_pnl", 0.0), 0.0)
        total += pnl

    return total


def _compute_signals_stats(signals: List[Dict[str, Any]]) -> Dict[str, int]:
    n = len(signals)
    enter_long = 0
    watch = 0
    avoid = 0

    for s in signals:
        action = str(s.get("action", "")).lower()
        if action == "enter_long":
            enter_long += 1
        elif action == "watch":
            watch += 1
        elif action == "avoid":
            avoid += 1

    return {
        "nb_signals": n,
        "nb_signals_enter_long": enter_long,
        "nb_signals_watch": watch,
        "nb_signals_avoid": avoid,
    }


def _compute_avg_momentum_meta_score(momentum_scores: List[Dict[str, Any]]) -> float:
    if not momentum_scores:
        return 0.0
    vals: List[float] = []
    for row in momentum_scores:
        vals.append(_safe_float(row.get("meta_score", 0.0), 0.0))
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _compute_meta_score_nsc(
    regime: str,
    risk_mode: str,
    avg_momentum_meta_score: float,
    total_capital: float,
    trading_capital: float,
) -> Dict[str, float]:
    """
    Meta-score NSC (0-100) version simple "hedge fund light".

    On décompose en 3 composantes :
      - regime_component   (0–20) : bull / neutral / bear
      - momentum_component (0–60) : 0.6 * avg_momentum_meta_score (cappé 60)
      - cap_component      (0–20) : qualité de la poche trading vs total

    Exemple (cas neutre dans tes logs) :
      regime_component   = 10
      momentum_component = 0.6 * 60.05 ≈ 36.03
      cap_component      = 20
      => meta_score_nsc ≈ 66.03
    """

    # 1) regime_component
    regime_component = 10.0
    r = regime.lower()
    rm = risk_mode.lower()

    if r.startswith("bull") and rm != "risk_off":
        regime_component = 20.0
    elif r.startswith("bear") or rm == "risk_off":
        regime_component = 0.0
    else:
        regime_component = 10.0  # neutral / other

    # 2) momentum_component (0–60)
    momentum_component = max(0.0, min(60.0, 0.6 * avg_momentum_meta_score))

    # 3) cap_component (0–20)
    cap_component = 0.0
    if total_capital > 0:
        ratio_trading = trading_capital / total_capital
        # Idéalement, autour de 45% pour la poche trading (V2)
        # On donne 20 si ratio ~ 0.45, 10 si ~0.25 ou 0.65, 0 si ~0
        if ratio_trading <= 0.0:
            cap_component = 0.0
        elif ratio_trading < 0.2 or ratio_trading > 0.8:
            cap_component = 5.0
        elif 0.3 <= ratio_trading <= 0.6:
            cap_component = 20.0
        else:
            cap_component = 10.0

    meta_score_nsc = regime_component + momentum_component + cap_component

    return {
        "regime_component": regime_component,
        "momentum_component": momentum_component,
        "cap_component": cap_component,
        "meta_score_nsc": meta_score_nsc,
    }


# ---------------------------------------------------------------------------
# Core: compute + save
# ---------------------------------------------------------------------------

def compute_daily_feedback() -> DailyTradingFeedback:
    """
    Calcule le feedback quotidien à partir des JSON générés par les autres modules.
    """

    now = datetime.now(timezone.utc)
    trading_date = date.today().isoformat()

    regime, risk_mode = _load_market_regime()
    total_capital, trading_capital = _load_capital_allocation()
    momentum_scores = _load_momentum_scores()
    signals = _load_signals()
    open_positions = _load_open_positions()
    exit_events = _load_exit_events()

    nb_assets_momentum = len(momentum_scores)
    signals_stats = _compute_signals_stats(signals)
    nb_open_positions = len(open_positions)

    unrealized_pnl = _compute_unrealized_pnl(open_positions)
    realized_pnl_today = _compute_realized_pnl_today(exit_events)
    avg_momentum_meta_score = _compute_avg_momentum_meta_score(momentum_scores)

    meta = _compute_meta_score_nsc(
        regime=regime,
        risk_mode=risk_mode,
        avg_momentum_meta_score=avg_momentum_meta_score,
        total_capital=total_capital,
        trading_capital=trading_capital,
    )

    feedback = DailyTradingFeedback(
        timestamp=now.isoformat(),
        trading_date=trading_date,
        regime=regime,
        risk_mode=risk_mode,
        total_capital=total_capital,
        trading_capital=trading_capital,
        nb_assets_momentum=nb_assets_momentum,
        nb_signals=signals_stats["nb_signals"],
        nb_signals_enter_long=signals_stats["nb_signals_enter_long"],
        nb_signals_watch=signals_stats["nb_signals_watch"],
        nb_signals_avoid=signals_stats["nb_signals_avoid"],
        nb_open_positions=nb_open_positions,
        unrealized_pnl=unrealized_pnl,
        realized_pnl_today=realized_pnl_today,
        avg_momentum_meta_score=avg_momentum_meta_score,
        meta_score_nsc=meta["meta_score_nsc"],
        meta_components={
            "regime_component": meta["regime_component"],
            "momentum_component": meta["momentum_component"],
            "cap_component": meta["cap_component"],
        },
    )

    logger.info(
        "[daily_feedback] Feedback calculé: regime=%s, risk_mode=%s, meta_score_nsc=%.2f",
        feedback.regime,
        feedback.risk_mode,
        feedback.meta_score_nsc,
    )

    return feedback


def save_daily_feedback(feedback: DailyTradingFeedback) -> None:
    _save_json(DAILY_FEEDBACK_FILE, feedback.to_dict())
    logger.info(
        "[daily_feedback] Feedback quotidien sauvegardé dans %s.",
        DAILY_FEEDBACK_FILE,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    fb = compute_daily_feedback()
    save_daily_feedback(fb)


if __name__ == "__main__":
    main()
