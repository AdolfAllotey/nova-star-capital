"""
trading_governance.py
-------------------------
Bloc de gouvernance "hedge fund light" pour Nova Star Capital.

Rôle :
  - Lire :
      * kill_switch.json
      * daily_trading_feedback.json  (meta_score_nsc, regime, PnL, etc.)
      * capital_allocation.json      (risk_mode, capital, etc.)
      * ml_signal_filter_config.json (seuils ML)
      * emotional_regime.json        (calm / heated / tilt_risk)
  - Construire une checklist de gouvernance quotidienne :
      * Kill-switch désactivé
      * Régime présent dans le plan
      * Meta_score_nsc au-dessus du seuil
      * Drawdown journalier dans les limites
      * Momentum moyen conforme
      * Règle ML définie dans le plan
      * Risk_mode cohérent avec le régime
      * Régime émotionnel dans les limites
  - Produire :
      * data/reports/trading_checklist.json
      * data/reports/trading_governance_summary.json
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import os

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("trading_governance")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
TRADING_DIR = DATA_DIR / "trading"
REPORTS_DIR = DATA_DIR / "reports"
ANALYSIS_DIR = DATA_DIR / "analysis"
MARKET_DIR = DATA_DIR / "market"

TRADING_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
MARKET_DIR.mkdir(parents=True, exist_ok=True)

KILL_SWITCH_FILE = TRADING_DIR / "kill_switch.json"
DAILY_FEEDBACK_FILE = REPORTS_DIR / "daily_trading_feedback.json"
CAPITAL_ALLOCATION_FILE = TRADING_DIR / "capital_allocation.json"
ML_CONFIG_FILE = ANALYSIS_DIR / "ml_signal_filter_config.json"
EMOTIONAL_REGIME_FILE = ANALYSIS_DIR / "emotional_regime.json"

TRADING_CHECKLIST_FILE = REPORTS_DIR / "trading_checklist.json"
GOVERNANCE_SUMMARY_FILE = REPORTS_DIR / "trading_governance_summary.json"

logger.info("[trading_governance] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)

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
                "[trading_governance] Erreur lors du chargement JSON: %s",
                path,
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
                "[trading_governance] Erreur lors de l'écriture JSON: %s",
                path,
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    name: str
    ok: bool
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradingChecklist:
    timestamp: str
    trading_date: str
    all_ok: bool
    score: float
    items: List[ChecklistItem]
    meta_score_nsc: Optional[float]
    regime: Optional[str]
    risk_mode: Optional[str]
    emotional_regime: Optional[str]
    emotional_action: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # convertir items en liste de dicts
        d["items"] = [it.to_dict() for it in self.items]
        return d


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _load_kill_switch() -> Dict[str, Any]:
    data = _load_json(KILL_SWITCH_FILE, default=None)
    if isinstance(data, dict):
        return data
    return {"enabled": False, "reason": "not_set"}


def _load_daily_feedback() -> Dict[str, Any]:
    data = _load_json(DAILY_FEEDBACK_FILE, default={})
    return data if isinstance(data, dict) else {}


def _load_capital_allocation() -> Dict[str, Any]:
    data = _load_json(CAPITAL_ALLOCATION_FILE, default={})
    return data if isinstance(data, dict) else {}


def _load_ml_config() -> Dict[str, Any]:
    data = _load_json(ML_CONFIG_FILE, default={})
    return data if isinstance(data, dict) else {}


def _load_emotional_regime() -> Dict[str, Any]:
    data = _load_json(EMOTIONAL_REGIME_FILE, default=None)
    if isinstance(data, dict) and "regime" in data:
        return data
    logger.warning(
        "[trading_governance] emotional_regime.json introuvable ou invalide (%s), fallback calm/normal.",
        EMOTIONAL_REGIME_FILE,
    )
    return {
        "regime": "calm",
        "recommended_action": "normal",
        "score_emotional": 80.0,
    }


# ---------------------------------------------------------------------------
# Checklist logic
# ---------------------------------------------------------------------------

def _evaluate_checklist() -> TradingChecklist:
    now = datetime.now(timezone.utc)
    trading_date = date.today().isoformat()

    kill = _load_kill_switch()
    fb = _load_daily_feedback()
    alloc = _load_capital_allocation()
    ml_cfg = _load_ml_config()
    emo = _load_emotional_regime()

    # Inputs principaux
    regime = str(fb.get("regime") or alloc.get("regime") or "neutral")
    risk_mode = str(fb.get("risk_mode") or alloc.get("risk_mode") or "normal")
    meta_score_nsc = _safe_float(fb.get("meta_score_nsc"), None)
    avg_momentum_meta_score = _safe_float(fb.get("avg_momentum_meta_score"), 0.0)
    realized_pnl_today = _safe_float(fb.get("realized_pnl_today"), 0.0)
    max_daily_loss = _safe_float(fb.get("max_daily_loss"), 500.0)

    emotional_regime = str(emo.get("regime", "calm"))
    emotional_action = str(emo.get("recommended_action", "normal"))

    items: List[ChecklistItem] = []

    # 1) Kill-switch
    kill_enabled = bool(kill.get("enabled", False))
    ks_item = ChecklistItem(
        name="Kill-switch désactivé",
        ok=not kill_enabled,
        details=f"kill_switch.enabled={kill_enabled}, reason={kill.get('reason', 'n/a')}",
    )
    items.append(ks_item)

    # 2) Régime dans le plan
    regimes_plan = ["bull", "neutral", "bear"]
    regime_ok = regime in regimes_plan
    regime_item = ChecklistItem(
        name="Régime présent dans le plan",
        ok=regime_ok,
        details=f"regime={regime}, regimes_plan={regimes_plan}",
    )
    items.append(regime_item)

    # 3) Meta-score NSC au-dessus du seuil
    meta_threshold = 40.0
    meta_ok = True
    if meta_score_nsc is not None:
        meta_ok = meta_score_nsc >= meta_threshold
    meta_item = ChecklistItem(
        name="Meta_score_nsc au-dessus du seuil",
        ok=meta_ok,
        details=f"meta_score_nsc={meta_score_nsc}, threshold={meta_threshold:.2f}",
    )
    items.append(meta_item)

    # 4) Drawdown journalier dans les limites
    # logique : OK si la perte n'excède pas -max_daily_loss
    dd_ok = realized_pnl_today >= -max_daily_loss
    dd_item = ChecklistItem(
        name="Drawdown journalier dans les limites",
        ok=dd_ok,
        details=f"realized_pnl_today={realized_pnl_today:.2f}, max_daily_loss={max_daily_loss:.2f}",
    )
    items.append(dd_item)

    # 5) Momentum moyen conforme
    momentum_threshold = 60.0
    momentum_ok = avg_momentum_meta_score >= momentum_threshold
    momentum_item = ChecklistItem(
        name="Momentum moyen conforme",
        ok=momentum_ok,
        details=f"avg_momentum_meta_score={avg_momentum_meta_score:.2f}, threshold={momentum_threshold:.2f}",
    )
    items.append(momentum_item)

    # 6) Règle ML définie dans le plan
    ml_threshold_plan = _safe_float(ml_cfg.get("threshold_accept"), 0.70)
    ml_item = ChecklistItem(
        name="Règle ML définie dans le plan",
        ok=ml_threshold_plan > 0.0,
        details=f"ml_threshold_plan={ml_threshold_plan:.2f}",
    )
    items.append(ml_item)

    # 7) Risk_mode cohérent
    allowed_risk_modes = ["normal", "conservative", "aggressive"]
    risk_ok = risk_mode in allowed_risk_modes
    risk_item = ChecklistItem(
        name="Risk_mode cohérent avec le régime",
        ok=risk_ok,
        details=f"regime={regime}, risk_mode={risk_mode}",
    )
    items.append(risk_item)

    # 8) Régime émotionnel dans les limites
    # OK si pas tilt_risk / pause_trading
    emo_ok = not (
        emotional_regime == "tilt_risk" or emotional_action == "pause_trading"
    )
    emo_item = ChecklistItem(
        name="Régime émotionnel dans les limites",
        ok=emo_ok,
        details=f"emotional_regime={emotional_regime}, emotional_action={emotional_action}",
    )
    items.append(emo_item)

    # Score global
    nb = len(items)
    nb_ok = sum(1 for it in items if it.ok)
    score = (nb_ok / nb * 100.0) if nb > 0 else 0.0
    all_ok = all(it.ok for it in items)

    checklist = TradingChecklist(
        timestamp=now.isoformat(),
        trading_date=trading_date,
        all_ok=all_ok,
        score=score,
        items=items,
        meta_score_nsc=meta_score_nsc,
        regime=regime,
        risk_mode=risk_mode,
        emotional_regime=emotional_regime,
        emotional_action=emotional_action,
    )

    logger.info(
        "[trading_governance] Checklist évaluée: score=%.1f, all_ok=%s, regime=%s, risk_mode=%s, meta_score_nsc=%s",
        score,
        all_ok,
        regime,
        risk_mode,
        meta_score_nsc,
    )

    return checklist


# ---------------------------------------------------------------------------
# LLM (optionnel) + fallback
# ---------------------------------------------------------------------------

def _build_fallback_summary_text(checklist: TradingChecklist) -> str:
    nb_alerts = sum(1 for it in checklist.items if not it.ok)
    realized_pnl_today = 0.0
    meta_score_nsc = checklist.meta_score_nsc

    fb = _load_daily_feedback()
    if isinstance(fb, dict):
        realized_pnl_today = _safe_float(fb.get("realized_pnl_today"), 0.0)

    txt = (
        f"Résumé automatique (fallback, sans LLM) pour la journée du {checklist.trading_date}. "
        f"Régime : {checklist.regime}, risk_mode : {checklist.risk_mode}, "
        f"emotional_regime : {checklist.emotional_regime}, emotional_action : {checklist.emotional_action}, "
        f"meta_score_nsc : {meta_score_nsc}. "
        f"Résultat réalisé de la journée : {realized_pnl_today:.2f} EUR. "
        f"Score checklist : {checklist.score:.1f} %. "
    )

    if checklist.all_ok:
        txt += "Toutes les règles de la checklist sont respectées. Le bot peut continuer à trader selon le plan."
    else:
        txt += (
            "Certaines règles de la checklist ne sont pas respectées. "
            "Une revue manuelle est recommandée. "
            f"Nombre de points en alerte : {nb_alerts}. "
            "Consulter trading_checklist.json pour le détail."
        )

    return txt


def _build_llm_summary_text(checklist: TradingChecklist) -> str:
    """
    # NSC: hard-disable LLM calls in PREPROD when NSC_LLM_ENABLED=0
    import os
    if os.getenv('NSC_LLM_ENABLED','1').strip().lower() in ('0','false','no','n','off'):
        raise RuntimeError('LLM disabled (NSC_LLM_ENABLED=0)')
    Utilise (optionnellement) un LLM via l'API OpenAI (SDK v1) pour générer un résumé.
    Si indisponible, fallback automatique.
    """
    enable_llm = os.getenv("NSC_ENABLE_LLM_GOVERNANCE", "0") == "1"
    if not enable_llm:
        logger.info(
            "[trading_governance] LLM désactivé (NSC_ENABLE_LLM_GOVERNANCE != '1'), utilisation d'un résumé simple."
        )
        return _build_fallback_summary_text(checklist)

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        logger.warning(
            "[trading_governance] openai non disponible, LLM désactivé."
        )
        return _build_fallback_summary_text(checklist)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning(
            "[trading_governance] OPENAI_API_KEY absent, fallback résumé simple."
        )
        return _build_fallback_summary_text(checklist)

    client = OpenAI(api_key=api_key)

    # Préparer un prompt compact avec les infos clés
    items_text = "\n".join(
        f"- [{ 'OK' if it.ok else 'ALERTE' }] {it.name} → {it.details}"
        for it in checklist.items
    )

    prompt = f"""
Tu es le contrôleur de risque d'un petit fonds quantitatif crypto. 
On te donne une checklist de gouvernance pour la journée du {checklist.trading_date}.

Contexte :
- Régime de marché : {checklist.regime}
- Mode de risque : {checklist.risk_mode}
- Régime émotionnel : {checklist.emotional_regime} (action recommandée : {checklist.emotional_action})
- Meta-score NSC : {checklist.meta_score_nsc}
- Score checklist global : {checklist.score:.1f} %
- all_ok : {checklist.all_ok}

Checklist :
{items_text}

Tâche :
- Résumer en français la situation de la journée en 4 à 6 phrases maximum.
- Indiquer clairement si le bot peut continuer à trader normalement, s'il doit réduire la taille, 
  ou s'il doit se mettre en pause.
- Mentionner brièvement les 1 à 2 points principaux en alerte s'il y en a.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un contrôleur de risque prudent, synthétique, qui écrit des résumés clairs "
                        "et actionnables pour un fonds quantitatif."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=350,
        )
        text = resp.choices[0].message.content.strip()  # type: ignore
        return text
    except Exception:
        logger.exception(
            "[trading_governance] Erreur lors de l'appel LLM, fallback sur résumé simple."
        )
        return _build_fallback_summary_text(checklist)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_and_save() -> TradingChecklist:
    checklist = _evaluate_checklist()
    _save_json(TRADING_CHECKLIST_FILE, checklist.to_dict())
    logger.info(
        "[trading_governance] Checklist sauvegardée dans %s.",
        TRADING_CHECKLIST_FILE,
    )

    summary_text = _build_llm_summary_text(checklist)
    summary_payload = {
        "timestamp": checklist.timestamp,
        "trading_date": checklist.trading_date,
        "all_ok": checklist.all_ok,
        "score": checklist.score,
        "meta_score_nsc": checklist.meta_score_nsc,
        "regime": checklist.regime,
        "risk_mode": checklist.risk_mode,
        "emotional_regime": checklist.emotional_regime,
        "emotional_action": checklist.emotional_action,
        "text": summary_text,
    }
    _save_json(GOVERNANCE_SUMMARY_FILE, summary_payload)
    logger.info(
        "[trading_governance] Résumé de gouvernance sauvegardé dans %s.",
        GOVERNANCE_SUMMARY_FILE,
    )

    return checklist


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    evaluate_and_save()


if __name__ == "__main__":
    main()
