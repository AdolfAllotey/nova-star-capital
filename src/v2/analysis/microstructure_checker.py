import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------

ENV = os.getenv("NSC_ENV", os.getenv("ENV", "LOCAL"))
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/opt/nsc/app/data")).resolve()
MARKET_DIR = DATA_ROOT / "market"
REPORTS_DIR = DATA_ROOT / "reports"
OUTPUT_PATH = REPORTS_DIR / "microstructure_score.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("microstructure_checker")


# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------


def safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Lecture JSON sécurisée."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("[microstructure] Erreur lecture JSON %s: %s", path, e)
        return None


def load_price_universe() -> List[Dict[str, Any]]:
    """
    Charge les données de prix à partir de :
    1) ohlcv_combined.json si présent
    2) Sinon tous les fichiers ohlcv_*.json dans DATA_ROOT/market

    Format attendu (minimal) par asset :
    {
      "symbol": "BTCUSDT",
      "source": "...",
      "env": "...",
      "candles": [
        {"ts": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...},
        ...
      ]
    }
    """
    assets: List[Dict[str, Any]] = []

    # 1) Fichier combiné prioritaire
    combined_path = MARKET_DIR / "ohlcv_combined.json"
    if combined_path.exists():
        logger.info(
            "[microstructure] Chargement du fichier combiné: %s", combined_path
        )
        raw = safe_read_json(combined_path)
        if isinstance(raw, dict) and isinstance(raw.get("assets"), list):
            assets = raw["assets"]
            logger.info(
                "[microstructure] Fichier combiné OK – assets=%s", len(assets)
            )
            return assets
        else:
            logger.warning(
                "[microstructure] Format inattendu dans %s (type racine: %s)",
                combined_path,
                type(raw),
            )

    # 2) Fallback: tous les ohlcv_*.json
    if not MARKET_DIR.exists():
        logger.warning(
            "[microstructure] Dossier market inexistant: %s", MARKET_DIR
        )
        return []

    files = list(MARKET_DIR.glob("ohlcv_*.json"))
    if not files:
        logger.warning(
            "[microstructure] Aucun fichier ohlcv_*.json trouvé dans %s", MARKET_DIR
        )
        return []

    logger.info(
        "[microstructure] Chargement des fichiers individuels: %s",
        ", ".join(f.name for f in files),
    )

    for path in files:
        raw = safe_read_json(path)
        if not raw:
            continue

        # 2 formats possibles :
        # - {"assets": [...]}
        # - {"symbol": ..., "candles": [...]}
        if isinstance(raw, dict) and isinstance(raw.get("assets"), list):
            assets.extend(raw["assets"])
        elif isinstance(raw, dict) and "symbol" in raw:
            assets.append(raw)
        else:
            logger.warning(
                "[microstructure] Format inattendu dans %s (clefs: %s)",
                path,
                list(raw.keys()) if isinstance(raw, dict) else type(raw),
            )

    logger.info("[microstructure] Total assets chargés: %s", len(assets))
    return assets


def compute_asset_microstructure(asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calcule quelques métriques simples de microstructure pour un asset.
    On reste volontairement simple : spread, volume, score de liquidité.
    """
    symbol = asset.get("symbol") or asset.get("pair") or "UNKNOWN"
    candles = asset.get("candles") or asset.get("ohlcv") or []

    if not isinstance(candles, list) or len(candles) == 0:
        return None

    # On prend la dernière bougie comme proxy actuel
    last = candles[-1]
    try:
        high = float(last.get("high", last.get("h", 0)))
        low = float(last.get("low", last.get("l", 0)))
        close = float(last.get("close", last.get("c", 0)))
        volume = float(last.get("volume", last.get("v", 0)))
    except Exception as e:
        logger.warning(
            "[microstructure] Impossible d'interpréter les champs OHLCV pour %s: %s",
            symbol,
            e,
        )
        return None

    if close <= 0 or high <= 0 or low <= 0:
        return None

    # Spread relatif simpliste
    spread = (high - low) / close

    # Score de liquidité grossier basé sur volume et spread
    # - volume élevé + spread faible -> score proche de 1
    # - volume faible + spread large -> score proche de 0
    # On clippe pour rester entre 0 et 1
    spread_penalty = min(spread / 0.02, 1.0)  # 2% de spread = pénalité max
    volume_factor = min(volume / 1_000_000.0, 1.0)  # 1M volume = facteur max
    liquidity_score = max(0.0, min(1.0, volume_factor * (1.0 - spread_penalty)))

    flags: List[str] = []
    if spread > 0.02:
        flags.append("spread_large")
    if volume < 10_000:
        flags.append("volume_faible")

    return {
        "symbol": symbol,
        "source": asset.get("source", "unknown"),
        "env": asset.get("env", ENV),
        "n_candles": len(candles),
        "last_close": close,
        "last_volume": volume,
        "spread": spread,
        "liquidity_score": round(liquidity_score, 3),
        "flags": flags,
    }


def main() -> None:
    logger.info(
        "[microstructure] Démarrage – ENV=%s DATA_ROOT=%s", ENV, DATA_ROOT
    )

    assets_raw = load_price_universe()
    if not assets_raw:
        logger.warning(
            "[microstructure] Aucun fichier de prix exploitable trouvé."
        )
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "env": ENV,
            "assets": [],
        }
    else:
        results: List[Dict[str, Any]] = []
        for asset in assets_raw:
            r = compute_asset_microstructure(asset)
            if r is not None:
                results.append(r)

        logger.info("[microstructure] Assets analysés: %s", len(results))
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "env": ENV,
            "assets": results,
        }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(
        "[microstructure] Rapport sauvegardé dans %s (assets=%s)",
        OUTPUT_PATH,
        len(report.get("assets", [])),
    )


if __name__ == "__main__":
    main()
import json
from pathlib import Path

# ...

def load_latest_microstructure(data_root: Path | str | None = None) -> dict:
    """
    Helper utilisé par l'API FastAPI.
    Charge le dernier rapport microstructure_score.json et renvoie un dict.
    """
    try:
        # On réutilise DATA_ROOT/ENV déjà définis dans le script
        root = Path(data_root) if data_root is not None else DATA_ROOT
    except NameError:
        # fallback de sécurité si jamais DATA_ROOT n'existe pas
        root = Path("/opt/nsc/app/data")

    path = root / "reports" / "microstructure_score.json"

    if not path.exists():
        try:
            logger.warning(
                "[microstructure] Aucun rapport microstructure_score.json trouvé à %s",
                path,
            )
        except Exception:
            pass

        return {
            "timestamp": None,
            "env": "LOCAL",
            "assets": [],
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        try:
            logger.exception(
                "[microstructure] Erreur lors du chargement du rapport %s", path
            )
        except Exception:
            pass

        return {
            "timestamp": None,
            "env": "LOCAL",
            "assets": [],
        }
