import json
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------

# ENV local pour les scripts d'analyse (comme microstructure_checker)
ENV = os.getenv("ENV", "LOCAL")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/opt/nsc/app/data")).resolve()
MARKET_DIR = DATA_ROOT / "market"
REPORTS_DIR = DATA_ROOT / "reports"
COMBINED_FILE = MARKET_DIR / "ohlcv_combined.json"
REPORT_FILE = REPORTS_DIR / "orderflow_report.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orderflow_checker")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AssetOrderflowReport:
    symbol: str
    source: str
    env: str
    n_candles: int
    avg_imbalance: float
    max_imbalance: float
    spoofing_risk: str
    has_fvg_flags: bool
    flags: List[str]


@dataclass
class OrderflowSummary:
    n_assets: int
    avg_imbalance: float
    nb_high_spoof: int
    nb_medium_spoof: int
    orderflow_regime: str


# ---------------------------------------------------------------------------
# Utilitaires de chargement
# ---------------------------------------------------------------------------

def ensure_reports_dir() -> None:
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.exception(
            "[orderflow] Erreur création du dossier reports %s: %s",
            REPORTS_DIR,
            e,
        )


def load_combined_ohlcv() -> Dict[str, Dict[str, Any]]:
    """
    Charge le fichier combiné ohlcv_combined.json.

    On supporte plusieurs formats possibles (pour coller à microstructure_checker) :

    1) {
         "assets": [
            {
              "symbol": "...",
              "source": "...",
              "ohlcv" | "candles" | "data" | "series": [ {...}, ... ]
            },
            ...
         ]
       }

    2) {
         "BTCUSDT": [...],
         "ETHUSDT": [...]
       }

    On retourne un dict:
        { symbol: { "source": str, "series": List[Dict[str, Any]] }, ... }
    """
    if not COMBINED_FILE.exists():
        logger.warning(
            "[orderflow] Fichier combiné introuvable: %s",
            COMBINED_FILE,
        )
        return {}

    try:
        with COMBINED_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        logger.exception(
            "[orderflow] Erreur de lecture %s: %s",
            COMBINED_FILE,
            e,
        )
        return {}

    assets: Dict[str, Dict[str, Any]] = {}

    # Format 1 : dict avec clé "assets"
    if isinstance(raw, dict) and isinstance(raw.get("assets"), list):
        for item in raw["assets"]:
            if not isinstance(item, dict):
                continue

            symbol = item.get("symbol") or item.get("pair") or item.get("ticker")
            if not symbol:
                continue

            source = item.get("source") or "unknown"

            series = (
                item.get("ohlcv")
                or item.get("candles")
                or item.get("data")
                or item.get("series")
            )
            if not isinstance(series, list) or not series:
                continue

            assets[str(symbol)] = {
                "source": str(source),
                "series": series,
            }

    # Format 2 : mapping symbol -> liste de candles
    elif isinstance(raw, dict):
        for symbol, series in raw.items():
            if isinstance(series, list) and series:
                assets[str(symbol)] = {
                    "source": "unknown",
                    "series": series,
                }

    else:
        logger.warning(
            "[orderflow] Format inattendu pour %s (type: %s)",
            COMBINED_FILE,
            type(raw),
        )

    logger.info("[orderflow] Fichier combiné OK – assets=%s", len(assets))
    return assets


# ---------------------------------------------------------------------------
# Logique d'analyse orderflow
# ---------------------------------------------------------------------------

def compute_imbalance_for_candle(c: Dict[str, Any]) -> Optional[float]:
    """
    Essaie de calculer un score d'order imbalance pour une bougie.

    On tente plusieurs schémas possibles :
      - champs explicites buy_volume / sell_volume
      - éventuellement un champ 'order_imbalance' déjà calculé
    """
    # Si un champ d'imbalance est déjà présent
    if isinstance(c.get("order_imbalance"), (int, float)):
        return float(c["order_imbalance"])

    buy_v = c.get("buy_volume")
    sell_v = c.get("sell_volume")

    if isinstance(buy_v, (int, float)) and isinstance(sell_v, (int, float)):
        total = buy_v + sell_v
        if total > 0:
            return (buy_v - sell_v) / total

    # Si rien d'exploitable
    return None


def detect_spoofing_flags(c: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """
    Détection très simple du risque de spoofing.

    On supporte plusieurs formats :
      - champ 'spoof_score' (0 → 1)
      - champ 'spoofing_risk' déjà catégorisé
    """
    spoof_score = c.get("spoof_score")
    risk = c.get("spoofing_risk")

    if isinstance(spoof_score, (int, float)):
        if spoof_score >= 0.7:
            return float(spoof_score), "high"
        if spoof_score >= 0.4:
            return float(spoof_score), "medium"
        return float(spoof_score), "low"

    if isinstance(risk, str):
        risk_lower = risk.lower()
        if risk_lower in {"high", "medium", "low"}:
            return None, risk_lower

    return None, None


def analyse_asset(symbol: str, asset: Dict[str, Any]) -> AssetOrderflowReport:
    """
    Analyse l'ordre flow pour un asset : imbalance moyen, max, spoofing, flags.
    """
    source = asset.get("source", "unknown")
    series = asset.get("series") or []
    n = len(series)

    imbalances: List[float] = []
    spoof_scores: List[float] = []
    spoof_risks: List[str] = []
    flags: List[str] = []

    for c in series:
        if not isinstance(c, dict):
            continue

        # Order imbalance
        imb = compute_imbalance_for_candle(c)
        if imb is not None:
            imbalances.append(imb)

        # Spoofing
        spoof_score, spoof_risk = detect_spoofing_flags(c)
        if spoof_score is not None:
            spoof_scores.append(spoof_score)
        if spoof_risk is not None:
            spoof_risks.append(spoof_risk)

        # Flags divers (si déjà présents)
        if isinstance(c.get("flags"), list):
            for f in c["flags"]:
                if isinstance(f, str) and f not in flags:
                    flags.append(f)

    if imbalances:
        avg_imb = float(mean(imbalances))
        max_imb = float(max(abs(x) for x in imbalances))
    else:
        avg_imb = 0.0
        max_imb = 0.0

    # Détermination du spoofing_risk global pour l'asset
    spoofing_risk = "none"
    if spoof_risks:
        # priorité high > medium > low
        if any(r == "high" for r in spoof_risks):
            spoofing_risk = "high"
        elif any(r == "medium" for r in spoof_risks):
            spoofing_risk = "medium"
        elif any(r == "low" for r in spoof_risks):
            spoofing_risk = "low"

    has_fvg = any("fvg" in f.lower() for f in flags)

    return AssetOrderflowReport(
        symbol=symbol,
        source=source,
        env=ENV,
        n_candles=n,
        avg_imbalance=avg_imb,
        max_imbalance=max_imb,
        spoofing_risk=spoofing_risk,
        has_fvg_flags=has_fvg,
        flags=flags,
    )


def summarise_orderflow(reports: List[AssetOrderflowReport]) -> OrderflowSummary:
    """
    Construit un résumé global de l'orderflow pour tous les assets.
    """
    n_assets = len(reports)

    if n_assets == 0:
        return OrderflowSummary(
            n_assets=0,
            avg_imbalance=0.0,
            nb_high_spoof=0,
            nb_medium_spoof=0,
            orderflow_regime="unknown",
        )

    avg_imb = float(mean(abs(r.avg_imbalance) for r in reports))

    nb_high_spoof = sum(1 for r in reports if r.spoofing_risk == "high")
    nb_medium_spoof = sum(1 for r in reports if r.spoofing_risk == "medium")

    # Petit heuristique pour le régime global :
    # - si bcp de spoofing "high" ou déséquilibre moyen très élevé → "bad"
    # - sinon si un peu de spoofing ou imbalance notable → "caution"
    # - sinon → "normal"
    if nb_high_spoof >= max(1, n_assets // 3) or avg_imb >= 0.6:
        regime = "bad"
    elif nb_medium_spoof > 0 or avg_imb >= 0.3:
        regime = "caution"
    else:
        regime = "normal"

    return OrderflowSummary(
        n_assets=n_assets,
        avg_imbalance=avg_imb,
        nb_high_spoof=nb_high_spoof,
        nb_medium_spoof=nb_medium_spoof,
        orderflow_regime=regime,
    )


# ---------------------------------------------------------------------------
# Sauvegarde
# ---------------------------------------------------------------------------

def save_report(summary: OrderflowSummary, reports: List[AssetOrderflowReport]) -> None:
    ensure_reports_dir()
    payload: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": ENV,
        "summary": asdict(summary),
        "assets": [asdict(r) for r in reports],
    }

    try:
        with REPORT_FILE.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(
            "[orderflow] Rapport sauvegardé dans %s (assets=%s)",
            REPORT_FILE,
            len(reports),
        )
    except Exception as e:
        logger.exception(
            "[orderflow] Erreur lors de l'écriture du rapport %s: %s",
            REPORT_FILE,
            e,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info(
        "[orderflow] Démarrage – ENV=%s DATA_ROOT=%s",
        ENV,
        DATA_ROOT,
    )

    assets = load_combined_ohlcv()
    if not assets:
        logger.warning(
            "[orderflow] Aucun asset chargé depuis %s, rapport vide.",
            COMBINED_FILE,
        )
        summary = OrderflowSummary(
            n_assets=0,
            avg_imbalance=0.0,
            nb_high_spoof=0,
            nb_medium_spoof=0,
            orderflow_regime="unknown",
        )
        save_report(summary, [])
        return

    reports: List[AssetOrderflowReport] = []
    for symbol, info in assets.items():
        try:
            report = analyse_asset(symbol, info)
            reports.append(report)
        except Exception as e:
            logger.exception(
                "[orderflow] Erreur d'analyse pour %s: %s",
                symbol,
                e,
            )

    logger.info("[orderflow] Assets analysés: %s", len(reports))
    summary = summarise_orderflow(reports)
    save_report(summary, reports)


if __name__ == "__main__":
    main()

def load_latest_orderflow(data_root: Path | str | None = None) -> dict | None:
    """
    Charge le dernier rapport d'orderflow depuis data_root/reports/orderflow_report.json.
    Utilisé par l'API FastAPI (/analysis/orderflow, /market/overview).
    """
    if data_root is None:
        base = detect_data_root()
    else:
        base = Path(data_root)

    report_path = base / "reports" / "orderflow_report.json"

    if not report_path.exists():
        logger.warning("[orderflow] Aucun fichier de rapport trouvé: %s", report_path)
        return None

    try:
        with report_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(
            "[orderflow] Rapport chargé depuis %s (assets=%s)",
            report_path,
            len(data.get("assets", [])),
        )
        return data
    except Exception:
        logger.exception(
            "[orderflow] Erreur lors du chargement du rapport: %s", report_path
        )
        return None
