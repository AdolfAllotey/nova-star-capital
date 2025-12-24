"""
sector_rotation_engine_light.py

Version "light" du moteur de rotation sectorielle pour Nova Star Capital.

Objectif :
- Regrouper les actifs par "secteur" (majors, smart_contracts, high_beta, etc.)
- Calculer un score par secteur à partir :
  - du meta-score momentum
  - des whales
  - de la narrative
  - du hype cycle (si dispo)
- Identifier les secteurs leaders / laggards
- Proposer un signal de rotation : overweight leaders, underweight laggards, ou neutre.

Entrées (toutes optionnelles, le module est robuste aux absences) :
- data/analysis/momentum_scores.json      (liste)
- data/analysis/whale_overview.json       (dict par symbol)
- data/analysis/narrative_overview.json   (dict par symbol)
- data/analysis/hype_cycle_overview.json  (dict par symbol)
- data/market/sector_map.json             (mapping facultatif {symbol: sector})

Sortie :
- data/analysis/sector_rotation_overview.json
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger(__name__)

# Détection ROOT_DIR / DATA_DIR sans dépendre de file_utils
# /opt/nsc/app/src/v2/analysis/sector_rotation_engine_light.py
# parents[0] = .../src/v2/analysis
# parents[1] = .../src/v2
# parents[2] = .../src
# parents[3] = .../app   <-- ROOT_DIR
# parents[4] = .../nsc
ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"

MOMENTUM_FILE = DATA_DIR / "analysis" / "momentum_scores.json"
WHALE_FILE = DATA_DIR / "analysis" / "whale_overview.json"
NARRATIVE_FILE = DATA_DIR / "analysis" / "narrative_overview.json"
HYPE_FILE = DATA_DIR / "analysis" / "hype_cycle_overview.json"
SECTOR_MAP_FILE = DATA_DIR / "market" / "sector_map.json"
OUTPUT_FILE = DATA_DIR / "analysis" / "sector_rotation_overview.json"


@dataclass
class AssetMetrics:
    symbol: str
    sector: str
    momentum_meta: float | None = None
    whale_score: float | None = None
    narrative_score: float | None = None
    hype_score: float | None = None


@dataclass
class SectorMetrics:
    sector: str
    assets: List[str]
    avg_momentum_meta: float
    avg_whale_score: float
    avg_narrative_score: float
    avg_hype_score: float
    sector_score: float
    flag: str  # leader / laggard / neutral


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_sector_map() -> Dict[str, str]:
    """
    Charge un mapping symbol -> secteur depuis sector_map.json,
    avec un fallback par défaut pour BTC / ETH / SOL.
    """
    default_map = {
        "bitcoin": "majors_store_of_value",
        "btc": "majors_store_of_value",
        "ethereum": "smart_contracts",
        "eth": "smart_contracts",
        "solana": "high_beta_l1",
        "sol": "high_beta_l1",
    }

    data = load_json_file(SECTOR_MAP_FILE, default=None)
    if not data or not isinstance(data, dict):
        logger.warning(
            "[sector_rotation] Aucun sector_map.json valide trouvé (%s), "
            "utilisation du mapping par défaut.",
            SECTOR_MAP_FILE,
        )
        return default_map

    merged = {**default_map, **data}
    logger.info(
        "[sector_rotation] sector_map chargé depuis %s (n=%d, default fusionné).",
        SECTOR_MAP_FILE,
        len(merged),
    )
    return merged


def _load_momentum_assets() -> Dict[str, AssetMetrics]:
    """
    Charge les scores momentum et initialise la structure AssetMetrics.
    """
    raw = load_json_file(MOMENTUM_FILE, default=[])
    assets: Dict[str, AssetMetrics] = {}

    if not isinstance(raw, list):
        logger.warning(
            "[sector_rotation] momentum_scores.json n'est pas une liste (%s).",
            type(raw),
        )
        return assets

    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        if not symbol:
            continue

        sym = str(symbol).lower()

        meta = item.get("meta_score")
        if meta is None:
            components = item.get("components") or {}
            meta = components.get("meta_score")

        try:
            meta_f = float(meta) if meta is not None else None
        except (TypeError, ValueError):
            meta_f = None

        assets[sym] = AssetMetrics(
            symbol=sym,
            sector="other",  # sera remplacé plus tard par le sector_map
            momentum_meta=meta_f,
        )

    logger.info(
        "[sector_rotation] momentum_scores: %d assets chargés depuis %s.",
        len(assets),
        MOMENTUM_FILE,
    )
    return assets


def _enrich_with_whales(assets: Dict[str, AssetMetrics]) -> None:
    data = load_json_file(WHALE_FILE, default={})
    if not isinstance(data, dict) or not data:
        logger.warning(
            "[sector_rotation] Aucun whale_overview.json exploitable (%s).",
            WHALE_FILE,
        )
        return

    for sym, metrics in assets.items():
        src = data.get(sym) or data.get(sym.upper()) or data.get(sym.capitalize())
        if not isinstance(src, dict):
            continue
        score = src.get("whale_score") or src.get("score") or src.get("meta_score")
        try:
            metrics.whale_score = float(score) if score is not None else None
        except (TypeError, ValueError):
            metrics.whale_score = None

    logger.info("[sector_rotation] Enrichissement whales terminé.")


def _enrich_with_narrative(assets: Dict[str, AssetMetrics]) -> None:
    data = load_json_file(NARRATIVE_FILE, default={})
    if not isinstance(data, dict) or not data:
        logger.warning(
            "[sector_rotation] Aucun narrative_overview.json exploitable (%s).",
            NARRATIVE_FILE,
        )
        return

    for sym, metrics in assets.items():
        src = data.get(sym) or data.get(sym.upper()) or data.get(sym.capitalize())
        if not isinstance(src, dict):
            continue
        score = src.get("narrative_score") or src.get("score") or src.get(
            "meta_score"
        )
        try:
            metrics.narrative_score = float(score) if score is not None else None
        except (TypeError, ValueError):
            metrics.narrative_score = None

    logger.info("[sector_rotation] Enrichissement narrative terminé.")


def _enrich_with_hype(assets: Dict[str, AssetMetrics]) -> None:
    data = load_json_file(HYPE_FILE, default={})
    if not isinstance(data, dict) or not data:
        logger.warning(
            "[sector_rotation] Aucun hype_cycle_overview.json exploitable (%s).",
            HYPE_FILE,
        )
        return

    for sym, metrics in assets.items():
        src = data.get(sym) or data.get(sym.upper()) or data.get(sym.capitalize())
        if not isinstance(src, dict):
            continue
        score = src.get("hype_score") or src.get("score") or src.get("meta_score")
        try:
            metrics.hype_score = float(score) if score is not None else None
        except (TypeError, ValueError):
            metrics.hype_score = None

    logger.info("[sector_rotation] Enrichissement hype terminé.")


def _apply_sector_map(
    assets: Dict[str, AssetMetrics], sector_map: Dict[str, str]
) -> None:
    for sym, metrics in assets.items():
        sector = sector_map.get(sym) or sector_map.get(sym.upper()) or sector_map.get(
            sym.capitalize()
        )
        if not sector:
            sector = "other"
        metrics.sector = str(sector)


def _compute_sector_scores(
    assets: Dict[str, AssetMetrics],
) -> Tuple[Dict[str, SectorMetrics], Dict[str, Any]]:
    """
    Agrège les métriques par secteur et calcule un score sectoriel.
    """
    sector_buckets: Dict[str, Dict[str, Any]] = {}

    for m in assets.values():
        sec = m.sector or "other"
        bucket = sector_buckets.setdefault(
            sec,
            {
                "assets": [],
                "momentum": [],
                "whale": [],
                "narrative": [],
                "hype": [],
            },
        )
        bucket["assets"].append(m.symbol)
        if m.momentum_meta is not None:
            bucket["momentum"].append(m.momentum_meta)
        if m.whale_score is not None:
            bucket["whale"].append(m.whale_score)
        if m.narrative_score is not None:
            bucket["narrative"].append(m.narrative_score)
        if m.hype_score is not None:
            bucket["hype"].append(m.hype_score)

    if not sector_buckets:
        return {}, {
            "nb_assets": 0,
            "nb_sectors": 0,
            "global_avg_momentum": None,
        }

    def _avg(values: List[float]) -> float:
        return sum(values) / len(values) if values else 50.0

    all_momentum_values = [
        m.momentum_meta for m in assets.values() if m.momentum_meta is not None
    ]
    global_avg_momentum = (
        sum(all_momentum_values) / len(all_momentum_values)
        if all_momentum_values
        else 50.0
    )

    sectors: Dict[str, SectorMetrics] = {}
    best_sec = None
    best_score = None
    worst_sec = None
    worst_score = None

    for sec, bucket in sector_buckets.items():
        avg_mom = _avg(bucket["momentum"])
        avg_whale = _avg(bucket["whale"])
        avg_narr = _avg(bucket["narrative"])
        avg_hype = _avg(bucket["hype"])

        sector_score = (
            0.45 * avg_mom
            + 0.20 * avg_whale
            + 0.20 * avg_narr
            + 0.15 * avg_hype
        )

        sectors[sec] = SectorMetrics(
            sector=sec,
            assets=sorted(bucket["assets"]),
            avg_momentum_meta=avg_mom,
            avg_whale_score=avg_whale,
            avg_narrative_score=avg_narr,
            avg_hype_score=avg_hype,
            sector_score=sector_score,
            flag="neutral",
        )

        if best_score is None or sector_score > best_score:
            best_score = sector_score
            best_sec = sec
        if worst_score is None or sector_score < worst_score:
            worst_score = sector_score
            worst_sec = sec

    if best_sec is not None:
        sectors[best_sec].flag = "leader"
    if worst_sec is not None and worst_sec != best_sec:
        sectors[worst_sec].flag = "laggard"

    meta = {
        "nb_assets": len(assets),
        "nb_sectors": len(sectors),
        "global_avg_momentum": global_avg_momentum,
        "best_sector": best_sec,
        "best_score": best_score,
        "worst_sector": worst_sec,
        "worst_score": worst_score,
    }

    return sectors, meta


def compute_sector_rotation() -> Dict[str, Any]:
    """
    Fonction principale : calcule l'overview de rotation sectorielle.
    """
    logger.info(
        "[sector_rotation] ROOT_DIR=%s, DATA_DIR=%s",
        ROOT_DIR,
        DATA_DIR,
    )

    assets = _load_momentum_assets()
    if not assets:
        logger.warning(
            "[sector_rotation] Aucun asset momentum disponible, rotation sectorielle triviale."
        )
        result = {
            "timestamp": _utc_now_iso(),
            "nb_assets": 0,
            "nb_sectors": 0,
            "rotation_flag": "no_data",
            "rotation_signal": "none",
            "rotation_comment": "Aucun asset momentum disponible.",
            "sectors": {},
            "meta": {},
        }
        save_json_file(OUTPUT_FILE, result)
        logger.info(
            "[sector_rotation] sector_rotation_overview.json sauvegardé (no_data) dans %s.",
            OUTPUT_FILE,
        )
        return result

    sector_map = _load_sector_map()
    _apply_sector_map(assets, sector_map)

    _enrich_with_whales(assets)
    _enrich_with_narrative(assets)
    _enrich_with_hype(assets)

    sectors_dict, meta = _compute_sector_scores(assets)
    sectors_payload = {sec: asdict(metrics) for sec, metrics in sectors_dict.items()}

    best_score = meta.get("best_score")
    worst_score = meta.get("worst_score")
    best_sec = meta.get("best_sector")
    worst_sec = meta.get("worst_sector")

    rotation_flag = "flat"
    rotation_signal = "none"
    rotation_comment = "Différences sectorielles faibles, pas de rotation forte recommandée."

    if best_score is not None and worst_score is not None:
        spread = best_score - worst_score
        meta["score_spread"] = spread

        if spread >= 15:
            rotation_flag = "rotation_on"
            rotation_signal = "overweight_leaders_underweight_laggards"
            rotation_comment = (
                f"Secteur leader '{best_sec}' nettement au-dessus de '{worst_sec}' "
                f"(écart ~{spread:.1f} pts) : surpondérer le leader, sous-pondérer le laggard."
            )
        elif spread >= 8:
            rotation_flag = "rotation_moderate"
            rotation_signal = "light_rotation"
            rotation_comment = (
                f"Secteur leader '{best_sec}' au-dessus de '{worst_sec}' "
                f"(écart ~{spread:.1f} pts) : rotation modérée possible vers le leader."
            )

    result = {
        "timestamp": _utc_now_iso(),
        "nb_assets": meta.get("nb_assets", 0),
        "nb_sectors": meta.get("nb_sectors", 0),
        "rotation_flag": rotation_flag,
        "rotation_signal": rotation_signal,
        "rotation_comment": rotation_comment,
        "leader_sector": meta.get("best_sector"),
        "laggard_sector": meta.get("worst_sector"),
        "sectors": sectors_payload,
        "meta": meta,
    }

    save_json_file(OUTPUT_FILE, result)
    logger.info(
        "[sector_rotation] sector_rotation_overview.json sauvegardé dans %s "
        "(nb_assets=%s, nb_sectors=%s, rotation_flag=%s).",
        OUTPUT_FILE,
        result["nb_assets"],
        result["nb_sectors"],
        rotation_flag,
    )
    return result


def main() -> None:
    compute_sector_rotation()


if __name__ == "__main__":
    main()
