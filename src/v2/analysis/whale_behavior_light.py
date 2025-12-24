"""
whale_behavior_light.py
-------------------------------
Bloc D – Whale Behavior "light" pour Nova Star Capital.

Objectifs :
  - Lire les données brutes de comportement des whales si disponibles :
      * data/intelligence/whale_behavior.json
      * ou data/risk/whale_behavior.json
      * ou data/analysis/whale_behavior_raw.json
  - Fallback (si aucune donnée) :
      * charger les symboles depuis data/market/ohlcv_combined.json
      * créer un profil "neutre" par asset (whale_score=0.5)
  - Calculer par asset :
      * whale_score (0–1)
      * net_inflow_usd (optionnel)
      * whale_tx_count (optionnel)
      * tags : whale_inflow / whale_outflow / whale_neutral
  - Sauvegarder dans :
      * data/analysis/whale_overview.json
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("whale_behavior_light")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
INTEL_DIR = DATA_DIR / "intelligence"
RISK_DIR = DATA_DIR / "risk"
MARKET_DIR = DATA_DIR / "market"
ANALYSIS_DIR = DATA_DIR / "analysis"

INTEL_DIR.mkdir(parents=True, exist_ok=True)
RISK_DIR.mkdir(parents=True, exist_ok=True)
MARKET_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

WHALE_INTEL_FILE = INTEL_DIR / "whale_behavior.json"
WHALE_RISK_FILE = RISK_DIR / "whale_behavior.json"
WHALE_RAW_FILE = ANALYSIS_DIR / "whale_behavior_raw.json"
OHLCV_FILE = MARKET_DIR / "ohlcv_combined.json"
WHALE_OVERVIEW_FILE = ANALYSIS_DIR / "whale_overview.json"

logger.info(
    "[whale_behavior_light] ROOT_DIR=%s, DATA_DIR=%s",
    ROOT_DIR,
    DATA_DIR,
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
                "[whale_behavior_light] Erreur lors du chargement JSON: %s",
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
                "[whale_behavior_light] Erreur lors de l'écriture JSON: %s",
                path,
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Dataclass & helpers
# ---------------------------------------------------------------------------

@dataclass
class WhaleEntry:
    symbol: str
    whale_score: float        # 0–1
    net_inflow_usd: float     # peut être 0 si inconnu
    whale_tx_count: int       # nombre de tx whales (approx.)
    tags: List[str]
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Loading raw whale & ohlcv data
# ---------------------------------------------------------------------------

def _load_raw_whale() -> List[Dict[str, Any]]:
    """
    Charge la donnée brute de comportement des whales depuis
    les différents emplacements possibles.
    """
    for path in (WHALE_INTEL_FILE, WHALE_RISK_FILE, WHALE_RAW_FILE):
        data = _load_json(path, default=None)
        if data is None:
            continue
        if isinstance(data, list) and data:
            logger.info(
                "[whale_behavior_light] Données whales chargées (list) depuis %s (%d lignes).",
                path,
                len(data),
            )
            return data
        if isinstance(data, dict) and data:
            # dict -> on le convertit en liste de valeurs
            out = []
            for key, val in data.items():
                if isinstance(val, dict):
                    if "symbol" not in val:
                        val = dict(val)
                        val["symbol"] = key
                    out.append(val)
            logger.info(
                "[whale_behavior_light] Données whales chargées (dict→list) depuis %s (%d lignes).",
                path,
                len(out),
            )
            return out
    logger.warning(
        "[whale_behavior_light] Aucune donnée brute whales trouvée (%s, %s, %s).",
        WHALE_INTEL_FILE,
        WHALE_RISK_FILE,
        WHALE_RAW_FILE,
    )
    return []


def _load_symbols_from_ohlcv() -> List[str]:
    """
    Fallback : si aucune donnée whales, on lit les symboles depuis ohlcv_combined.json
    pour générer des profils neutres.
    """
    data = _load_json(OHLCV_FILE, default=None)
    if not isinstance(data, dict):
        logger.warning(
            "[whale_behavior_light] Impossible de charger les symboles depuis %s.",
            OHLCV_FILE,
        )
        return []
    symbols = sorted(list(data.keys()))
    logger.info(
        "[whale_behavior_light] Symboles chargés depuis ohlcv_combined.json (n=%d).",
        len(symbols),
    )
    return symbols


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def _aggregate_whale_entries(raw: List[Dict[str, Any]]) -> Dict[str, WhaleEntry]:
    """
    Agrège les entrées whales par symbol.
    Si aucun champ de score n'est disponible, on approxime :
      - net_inflow_usd > 0 => whale_score ≈ 0.7
      - net_inflow_usd < 0 => whale_score ≈ 0.3
      - sinon => 0.5
    """
    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").strip()
        if not sym:
            continue
        by_symbol.setdefault(sym, []).append(row)

    out: Dict[str, WhaleEntry] = {}
    now = datetime.now(timezone.utc).isoformat()

    for symbol, rows in by_symbol.items():
        # moyennes simples
        net_inflows: List[float] = []
        whale_scores: List[float] = []
        tx_counts: List[int] = []

        for r in rows:
            nf = None
            for k in ("net_inflow_usd", "netflow_usd", "netflow", "net_inflow"):
                if k in r:
                    nf = _safe_float(r.get(k), 0.0)
                    break
            if nf is not None:
                net_inflows.append(nf)

            ws = None
            for k in ("whale_score", "score", "netflow_score"):
                if k in r:
                    ws = _safe_float(r.get(k), 0.0)
                    break
            if ws is not None:
                whale_scores.append(ws)

            for k in ("whale_tx_count", "tx_count", "transactions"):
                if k in r:
                    tx_counts.append(_safe_int(r.get(k), 0))
                    break

        avg_net_inflow = sum(net_inflows) / len(net_inflows) if net_inflows else 0.0
        avg_ws_raw = sum(whale_scores) / len(whale_scores) if whale_scores else None
        avg_tx = int(sum(tx_counts) / len(tx_counts)) if tx_counts else 0

        if avg_ws_raw is not None:
            whale_score = max(0.0, min(1.0, avg_ws_raw))
        else:
            # Heuristique simple si pas de score déjà fourni
            if avg_net_inflow > 0:
                whale_score = 0.7
            elif avg_net_inflow < 0:
                whale_score = 0.3
            else:
                whale_score = 0.5

        tags: List[str] = []
        if whale_score >= 0.7:
            tags.append("whale_inflow")
        elif whale_score <= 0.3:
            tags.append("whale_outflow")
        else:
            tags.append("whale_neutral")

        entry = WhaleEntry(
            symbol=symbol,
            whale_score=whale_score,
            net_inflow_usd=avg_net_inflow,
            whale_tx_count=avg_tx,
            tags=tags,
            updated_at=now,
        )
        out[symbol] = entry

    logger.info(
        "[whale_behavior_light] Aggregation whales pour %d assets.",
        len(out),
    )
    return out


def _build_neutral_whales(symbols: List[str]) -> Dict[str, WhaleEntry]:
    """
    Fallback complet : aucun fichier whales.
    On crée un profil neutre pour chaque symbol (whale_score=0.5).
    """
    now = datetime.now(timezone.utc).isoformat()
    out: Dict[str, WhaleEntry] = {}
    for sym in symbols:
        out[sym] = WhaleEntry(
            symbol=sym,
            whale_score=0.5,
            net_inflow_usd=0.0,
            whale_tx_count=0,
            tags=["whale_neutral"],
            updated_at=now,
        )
    logger.info(
        "[whale_behavior_light] Profils whales neutres créés pour %d assets.",
        len(out),
    )
    return out


def compute_whale_overview() -> Dict[str, WhaleEntry]:
    raw = _load_raw_whale()
    if raw:
        overview = _aggregate_whale_entries(raw)
        if overview:
            return overview

    # Fallback : pas de données whales, on se base sur les symboles d'ohlcv
    symbols = _load_symbols_from_ohlcv()
    if not symbols:
        logger.warning(
            "[whale_behavior_light] Aucun symbole trouvé pour générer des profils whales."
        )
        return {}
    return _build_neutral_whales(symbols)


def save_whale_overview(data: Dict[str, WhaleEntry]) -> None:
    serialised = {sym: entry.to_dict() for sym, entry in data.items()}
    _save_json(WHALE_OVERVIEW_FILE, serialised)
    logger.info(
        "[whale_behavior_light] whale_overview.json mis à jour (%s, assets=%d).",
        WHALE_OVERVIEW_FILE,
        len(serialised),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    data = compute_whale_overview()
    if not data:
        logger.warning(
            "[whale_behavior_light] Aucun profil whales généré."
        )
        return
    save_whale_overview(data)


if __name__ == "__main__":
    main()
