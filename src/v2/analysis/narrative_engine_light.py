# src/v2/analysis/narrative_engine_light.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
MARKET_DIR = DATA_DIR / "market"
REPORTS_DIR = DATA_DIR / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_sentiment_overview() -> Dict[str, Any]:
    """
    Essaie d'abord data/reports/sentiment_overview.json,
    puis data/market/sentiment_overview.json.
    """
    path_report = REPORTS_DIR / "sentiment_overview.json"
    path_market = MARKET_DIR / "sentiment_overview.json"

    data = load_json_file(path_report, default=None)
    if data:
        logger.info(
            "[narrative_engine_light] Sentiment chargé depuis %s",
            path_report,
        )
        return data

    data = load_json_file(path_market, default=None)
    if data:
        logger.info(
            "[narrative_engine_light] Sentiment chargé depuis %s (fallback)",
            path_market,
        )
        return data

    logger.warning(
        "[narrative_engine_light] Aucun sentiment_overview trouvé (%s ni %s).",
        path_report,
        path_market,
    )
    return {}


def _load_momentum_scores() -> Dict[str, Dict[str, Any]]:
    """
    Normalise momentum_scores.json en dict symbol -> infos.
    Compatible avec différents formats (liste ou dict).
    """
    path = ANALYSIS_DIR / "momentum_scores.json"
    raw = load_json_file(path, default={})
    assets: Dict[str, Dict[str, Any]] = {}

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            symbol = (
                item.get("symbol")
                or item.get("asset")
                or item.get("ticker")
            )
            if symbol:
                assets[str(symbol).lower()] = item
    elif isinstance(raw, dict):
        # Soit déjà symbol -> dict, soit { "assets": [...] }
        if "assets" in raw and isinstance(raw["assets"], list):
            for item in raw["assets"]:
                if not isinstance(item, dict):
                    continue
                symbol = (
                    item.get("symbol")
                    or item.get("asset")
                    or item.get("ticker")
                )
                if symbol:
                    assets[str(symbol).lower()] = item
        else:
            for k, v in raw.items():
                if isinstance(v, dict):
                    assets[str(k).lower()] = v

    logger.info(
        "[narrative_engine_light] momentum_scores normalisé pour %d assets.",
        len(assets),
    )
    return assets


def _load_simple(path: Path) -> Dict[str, Any]:
    return load_json_file(path, default={}) or {}


def _load_weak_signals() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "weak_signals_overview.json")


def _load_hype_cycle() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "hype_cycle_overview.json")


def _load_mm_withdrawal() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "mm_withdrawal_overview.json")


def _load_liquidity_risk() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "liquidity_risk_overview.json")


def _load_risk_console() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "risk_console_overview.json")


def _load_anomaly_overview() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "anomaly_overview.json")


def _load_market_regime() -> Dict[str, Any]:
    return _load_simple(MARKET_DIR / "market_regime.json")


def _load_trading_checklist() -> Dict[str, Any]:
    return _load_simple(REPORTS_DIR / "trading_checklist.json")


def _load_logs_overview() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "logs_overview.json")


def _load_discipline_overview() -> Dict[str, Any]:
    return _load_simple(ANALYSIS_DIR / "discipline_overview.json")


def _get_asset_sentiment(
    sentiment_overview: Dict[str, Any], symbol: str
) -> Optional[Dict[str, Any]]:
    symbol_l = symbol.lower()
    assets = sentiment_overview.get("assets") or {}
    if isinstance(assets, dict):
        for k, v in assets.items():
            if str(k).lower() == symbol_l and isinstance(v, dict):
                return v
    return None


def _is_hype_asset(hype_overview: Dict[str, Any], symbol: str) -> bool:
    symbol_l = symbol.lower()
    items = hype_overview.get("items") or hype_overview.get("assets") or []
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = (
                it.get("symbol")
                or it.get("asset")
                or it.get("ticker")
            )
            if sym and str(sym).lower() == symbol_l:
                phase = str(it.get("phase") or it.get("stage") or "").lower()
                if phase in {"hype", "euphoric", "distribution"}:
                    return True
    return False


def _is_mm_withdrawal_flag(mm_overview: Dict[str, Any], symbol: str) -> bool:
    symbol_l = symbol.lower()
    items = mm_overview.get("items") or mm_overview.get("assets") or []
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = (
                it.get("symbol")
                or it.get("asset")
                or it.get("ticker")
            )
            if sym and str(sym).lower() == symbol_l:
                flag = str(it.get("flag") or "").lower()
                if flag in {"withdrawal", "warning", "critical"}:
                    return True
    return False


def _get_liquidity_flag(liq_overview: Dict[str, Any], symbol: str) -> Optional[str]:
    symbol_l = symbol.lower()
    items = liq_overview.get("items") or liq_overview.get("assets") or []
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = (
                it.get("symbol")
                or it.get("asset")
                or it.get("ticker")
            )
            if sym and str(sym).lower() == symbol_l:
                return str(it.get("liquidity_flag") or it.get("flag") or "").lower()
    return None


def _get_weak_signal_flag(weak_overview: Dict[str, Any], symbol: str) -> Optional[str]:
    symbol_l = symbol.lower()
    items = weak_overview.get("items") or []
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = (
                it.get("symbol")
                or it.get("asset")
                or it.get("ticker")
            )
            if sym and str(sym).lower() == symbol_l:
                return str(it.get("weak_flag") or it.get("flag") or "").lower()
    return None


# ---------------------------------------------------------------------------
# Construction du narratif par asset
# ---------------------------------------------------------------------------

def _build_asset_narrative(
    symbol: str,
    momentum_info: Dict[str, Any],
    sentiment_overview: Dict[str, Any],
    weak_overview: Dict[str, Any],
    hype_overview: Dict[str, Any],
    mm_overview: Dict[str, Any],
    liq_overview: Dict[str, Any],
) -> Dict[str, Any]:
    symbol_l = symbol.lower()
    sent = _get_asset_sentiment(sentiment_overview, symbol_l) or {}
    sentiment_score = _safe_float(sent.get("sentiment_score"), default=0.5)
    sentiment_label = sent.get("sentiment_label") or (
        "bullish" if sentiment_score >= 0.6 else "bearish" if sentiment_score <= 0.4 else "neutral"
    )

    meta_score = _safe_float(
        momentum_info.get("meta_score")
        or momentum_info.get("meta")
        or momentum_info.get("meta_score_nsc"),
        default=0.0,
    )
    momentum_score = _safe_float(
        momentum_info.get("momentum_score")
        or momentum_info.get("score")
        or momentum_info.get("momentum"),
        default=0.0,
    )

    weak_flag = _get_weak_signal_flag(weak_overview, symbol_l)
    hype_flag = _is_hype_asset(hype_overview, symbol_l)
    mm_flag = _is_mm_withdrawal_flag(mm_overview, symbol_l)
    liq_flag = _get_liquidity_flag(liq_overview, symbol_l)

    risk_flags: List[str] = []
    if weak_flag in {"watch", "avoid"}:
        risk_flags.append(f"weak_signals_{weak_flag}")
    if hype_flag:
        risk_flags.append("hype_cycle_risk")
    if mm_flag:
        risk_flags.append("mm_withdrawal_risk")
    if liq_flag:
        risk_flags.append(f"liquidity_{liq_flag}")

    # Vue synthétique entrée/surveillance/à éviter
    if meta_score >= 70 and sentiment_score >= 0.55 and "liquidity_high" not in risk_flags:
        trade_bias = "enter_long"
    elif weak_flag == "avoid" or liq_flag in {"low", "critical"} or mm_flag:
        trade_bias = "avoid"
    else:
        trade_bias = "watch"

    summary_parts: List[str] = []

    summary_parts.append(
        f"Momentum {momentum_score:.0f}/100 (meta {meta_score:.0f}/100), sentiment {sentiment_label} ({sentiment_score:.2f})."
    )

    if hype_flag:
        summary_parts.append("Attention : actif en phase de hype/distribution.")
    if mm_flag:
        summary_parts.append("Risque : retrait de liquidité par les market makers.")
    if liq_flag:
        summary_parts.append(f"Liquidité : {liq_flag}.")
    if weak_flag:
        summary_parts.append(f"Signal faible : {weak_flag}.")

    if trade_bias == "enter_long":
        summary_parts.append("Biais : candidat potentiel à l'entrée (sous réserve des règles du plan).")
    elif trade_bias == "avoid":
        summary_parts.append("Biais : à éviter pour le moment.")
    else:
        summary_parts.append("Biais : à surveiller, pas de déclencheur majeur isolé.")

    return {
        "symbol": symbol_l,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "momentum_score": momentum_score,
        "meta_score": meta_score,
        "trade_bias": trade_bias,
        "risk_flags": risk_flags,
        "summary": " ".join(summary_parts),
    }


# ---------------------------------------------------------------------------
# Narratif global
# ---------------------------------------------------------------------------

def _build_global_narrative(
    market_regime: Dict[str, Any],
    checklist: Dict[str, Any],
    sentiment_overview: Dict[str, Any],
    anomaly_overview: Dict[str, Any],
    risk_console: Dict[str, Any],
    discipline: Dict[str, Any],
) -> Dict[str, Any]:
    regime = str(market_regime.get("regime") or "neutral")
    risk_mode = str(market_regime.get("risk_mode") or "normal")
    meta_score = _safe_float(
        checklist.get("meta_score_nsc")
        or market_regime.get("meta_score_nsc"),
        default=0.0,
    )

    global_sentiment = _safe_float(
        sentiment_overview.get("global_sentiment_score"),
        default=0.5,
    )
    nb_anomalies = int(anomaly_overview.get("nb_anomalies") or 0)
    nb_critical = int(anomaly_overview.get("nb_critical") or 0)
    risk_flag = str(risk_console.get("global_flag") or "ok")
    discipline_score = _safe_float(discipline.get("score_discipline"), default=100.0)

    bullets: List[str] = []

    # 1) Contexte de marché
    bullets.append(
        f"Régime de marché : {regime} (risk_mode={risk_mode}, meta_score_nsc={meta_score:.1f})."
    )

    # 2) Sentiment
    if global_sentiment >= 0.65:
        bullets.append("Sentiment global plutôt optimiste, risque de complaisance à surveiller.")
    elif global_sentiment <= 0.35:
        bullets.append("Sentiment global plutôt négatif, environnement défensif.")
    else:
        bullets.append("Sentiment global neutre à équilibré.")

    # 3) Anomalies & risque console
    if nb_critical > 0:
        bullets.append(
            f"Plusieurs anomalies critiques détectées ({nb_critical}), prudence maximale recommandée."
        )
    elif nb_anomalies > 0:
        bullets.append(
            f"Quelques anomalies détectées ({nb_anomalies}), à intégrer dans le sizing et les entrées."
        )
    else:
        bullets.append("Aucune anomalie majeure détectée dans les checks automatiques.")

    bullets.append(f"Risk console : flag={risk_flag}.")
    bullets.append(f"Discipline : score={discipline_score:.1f}/100.")

    # 4) Message synthèse
    if risk_flag in {"caution", "soft_block"} or meta_score < 40 or discipline_score < 70:
        headline = (
            "Contexte prudent : privilégier la discipline et le contrôle du risque, "
            "même si certaines opportunités restent présentes."
        )
    elif regime == "bull" and meta_score >= 60 and global_sentiment >= 0.55:
        headline = (
            "Contexte porteur : environnement favorable aux prises de position, "
            "tout en respectant strictement les garde-fous."
        )
    elif regime == "bear":
        headline = (
            "Contexte défensif : priorité à la préservation du capital et aux signaux de qualité."
        )
    else:
        headline = (
            "Contexte intermédiaire : exploiter sélectivement les signaux solides, sans sur-exposition."
        )

    return {
        "headline": headline,
        "bullets": bullets,
        "regime": regime,
        "risk_mode": risk_mode,
        "meta_score_nsc": meta_score,
        "global_sentiment_score": global_sentiment,
        "risk_console_flag": risk_flag,
        "discipline_score": discipline_score,
        "nb_anomalies": nb_anomalies,
        "nb_critical": nb_critical,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def compute_narrative() -> Optional[Dict[str, Any]]:
    logger.info("[narrative_engine_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)

    sentiment_overview = _load_sentiment_overview()
    momentum_scores = _load_momentum_scores()
    weak_overview = _load_weak_signals()
    hype_overview = _load_hype_cycle()
    mm_overview = _load_mm_withdrawal()
    liq_overview = _load_liquidity_risk()
    risk_console = _load_risk_console()
    anomaly_overview = _load_anomaly_overview()
    market_regime = _load_market_regime()
    checklist = _load_trading_checklist()
    logs_overview = _load_logs_overview()
    discipline_overview = _load_discipline_overview()

    if not momentum_scores and not sentiment_overview and not market_regime:
        logger.warning(
            "[narrative_engine_light] Inputs insuffisants (pas de momentum_scores, "
            "pas de sentiment_overview et pas de market_regime). Aucun narratif généré."
        )
        return None

    # Construction narratif global
    global_view = _build_global_narrative(
        market_regime=market_regime,
        checklist=checklist,
        sentiment_overview=sentiment_overview,
        anomaly_overview=anomaly_overview,
        risk_console=risk_console,
        discipline=discipline_overview,
    )

    # Construction par asset
    assets_block: Dict[str, Any] = {}
    for symbol, info in momentum_scores.items():
        assets_block[symbol] = _build_asset_narrative(
            symbol=symbol,
            momentum_info=info,
            sentiment_overview=sentiment_overview,
            weak_overview=weak_overview,
            hype_overview=hype_overview,
            mm_overview=mm_overview,
            liq_overview=liq_overview,
        )

    overview: Dict[str, Any] = {
        "timestamp": _now_iso(),
        "source": "narrative_engine_light",
        "global_view": global_view,
        "assets": assets_block,
        "logs_flag": logs_overview.get("flag", "unknown"),
        "logs_reason": logs_overview.get("reason", ""),
    }

    logger.info(
        "[narrative_engine_light] Narratives calculées pour %d assets.",
        len(assets_block),
    )
    return overview


def main() -> None:
    overview = compute_narrative()
    if overview is None:
        logger.warning("[narrative_engine_light] Aucun narrative généré.")
        return

    out_path = ANALYSIS_DIR / "narrative_overview.json"
    save_json_file(out_path, overview)
    logger.info(
        "[narrative_engine_light] narrative_overview.json mis à jour (%s, assets=%d).",
        out_path,
        len(overview.get("assets", {})),
    )


if __name__ == "__main__":
    main()
