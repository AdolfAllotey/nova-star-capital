# src/v2/strategies/layer1_strategy.py
"""
Stratégie Layer-1 : sélectionne les meilleurs Layer-1 à partir de
/market/top_movers_layer1.json et écrit un fichier
/strategies/layer1_candidates.json exploitable par le bot.

- Input  : NSC_DATA_ROOT/market/top_movers_layer1.json
- Output : NSC_DATA_ROOT/strategies/layer1_candidates.json

Le score utilise :
  - chg_24h (variation 24h)
  - chg_7d  (variation 7j)
  - chg_30d (optionnel ; fallback si absent)

Formule :
  si chg_30d présent :
      score = 0.4 * chg_24h_norm + 0.3 * chg_7d_norm + 0.3 * chg_30d_norm
  sinon :
      score = 0.6 * chg_24h_norm + 0.4 * chg_7d_norm
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# --------------------------------------------------------------------
# Config chemins
# --------------------------------------------------------------------

DATA_ROOT = Path(os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data"))
MARKET_FILE = DATA_ROOT / "market" / "top_movers_layer1.json"
OUT_FILE = DATA_ROOT / "strategies" / "layer1_candidates.json"

# Paramètres ajustables via env
MIN_SCORE = float(os.environ.get("NSC_LAYER1_MIN_SCORE", "0.05"))
MAX_ITEMS = int(os.environ.get("NSC_LAYER1_MAX_ITEMS", "10"))

# --------------------------------------------------------------------
# Logger centralisé (si dispo), sinon fallback print
# --------------------------------------------------------------------

try:
    from v2.utils.logger import get_logger  # type: ignore

    logger = get_logger("layer1_strategy")
except Exception:
    logger = None

    def get_logger(name: str):
        class _Dummy:
            def info(self, msg, *a, **k):
                print(f"[INFO] {msg}")

            def warning(self, msg, *a, **k):
                print(f"[WARN] {msg}")

            def error(self, msg, *a, **k):
                print(f"[ERROR] {msg}")

            def exception(self, msg, *a, **k):
                print(f"[EXC] {msg}")

        return _Dummy()

    logger = get_logger("layer1_strategy")


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        logger.warning(f"[layer1] Fichier introuvable : {path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.error(f"[layer1] JSON invalide : {path}")
        return default


def _normalize_changes(item: Dict[str, Any]) -> Dict[str, float]:
    """
    Normalisation très simple des variations pour générer un score stable.
    On reste volontairement basique pour la préprod.
    """
    chg_24h = float(item.get("chg_24h", 0.0) or 0.0)
    chg_7d = float(item.get("chg_7d", 0.0) or 0.0)
    chg_30d_raw = item.get("chg_30d", None)

    chg_24h_norm = chg_24h / 20.0  # ±20% → ±1
    chg_7d_norm = chg_7d / 40.0    # ±40% → ±1

    has_30d = chg_30d_raw is not None
    if has_30d:
        chg_30d = float(chg_30d_raw or 0.0)
        chg_30d_norm = chg_30d / 60.0  # ±60% → ±1
    else:
        chg_30d = 0.0
        chg_30d_norm = 0.0

    return {
        "chg_24h": chg_24h,
        "chg_7d": chg_7d,
        "chg_30d": chg_30d,
        "chg_24h_norm": chg_24h_norm,
        "chg_7d_norm": chg_7d_norm,
        "chg_30d_norm": chg_30d_norm,
        "has_30d": has_30d,
    }


def _score_item(item: Dict[str, Any]) -> float:
    """
    Calcule le score Layer-1 pour un token.
    Fallback correct si on n'a pas chg_30d.
    """
    feats = _normalize_changes(item)
    if feats["has_30d"]:
        score = (
            0.4 * feats["chg_24h_norm"]
            + 0.3 * feats["chg_7d_norm"]
            + 0.3 * feats["chg_30d_norm"]
        )
    else:
        # Fallback sans données 30 jours
        score = 0.6 * feats["chg_24h_norm"] + 0.4 * feats["chg_7d_norm"]
    return float(score)


def _build_candidate(item: Dict[str, Any]) -> Dict[str, Any]:
    feats = _normalize_changes(item)
    score = _score_item(item)

    return {
        "symbol": item.get("symbol"),
        "name": item.get("name"),
        "id": item.get("id"),
        "price": item.get("price"),
        "source": item.get("source"),
        "pair": item.get("pair"),
        "score": score,
        "features": {
            "chg_24h": feats["chg_24h"],
            "chg_7d": feats["chg_7d"],
            "chg_30d": feats["chg_30d"],
            "chg_24h_norm": feats["chg_24h_norm"],
            "chg_7d_norm": feats["chg_7d_norm"],
            "chg_30d_norm": feats["chg_30d_norm"],
            "has_30d": feats["has_30d"],
        },
    }


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------


def run() -> Dict[str, Any]:
    logger.info(
        f"[layer1] Start – DATA_ROOT={DATA_ROOT}, "
        f"MIN_SCORE={MIN_SCORE}, MAX_ITEMS={MAX_ITEMS}"
    )

    data = _load_json(MARKET_FILE, {"updated_at": None, "items": []})
    items: List[Dict[str, Any]] = data.get("items") or []

    if not items:
        logger.warning(f"[layer1] Aucun item dans {MARKET_FILE}, sortie vide.")
        doc = {"updated_at": datetime.now(timezone.utc).isoformat(), "items": []}
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return doc

    logger.info(f"[layer1] {len(items)} Layer-1 reçus depuis top_movers_layer1.json")

    candidates: List[Dict[str, Any]] = []
    for raw in items:
        try:
            cand = _build_candidate(raw)
            if cand["score"] >= MIN_SCORE:
                candidates.append(cand)
        except Exception:
            logger.exception(
                f"[layer1] Erreur lors du scoring de {raw.get('symbol')}"
            )

    # Tri décroissant par score
    candidates.sort(key=lambda c: c["score"], reverse=True)
    if MAX_ITEMS > 0:
        candidates = candidates[:MAX_ITEMS]

    logger.info(
        f"[layer1] {len(candidates)} candidats retenus (score >= {MIN_SCORE})"
    )

    doc = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": candidates,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"[layer1] Écrit {OUT_FILE}")
    return doc


if __name__ == "__main__":
    run()
