from __future__ import annotations

from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import data_path, load_json_file, save_json_file, now_ts

logger = get_logger("market_snapshot_exporter")


def export_market_snapshot() -> Dict[str, Any]:
    """
    Exporte un snapshot marché minimal (à enrichir ensuite).
    L'objectif ici est surtout de garantir que les chemins data/ sont canoniques.
    """
    snapshot: Dict[str, Any] = {
        "timestamp": now_ts(),
        "env": "unknown",
        "sources": {},
    }

    # Exemple : lecture de fichiers déjà générés, via data_path()
    snapshot["sources"]["market_conditions"] = load_json_file(
        data_path("analysis", "market_conditions_engine_pro.json"),
        default={},
    )
    snapshot["sources"]["market_coherence"] = load_json_file(
        data_path("analysis", "market_coherence_engine_pro.json"),
        default={},
    )
    snapshot["sources"]["signal_quality"] = load_json_file(
        data_path("analysis", "signal_quality_engine_pro.json"),
        default={},
    )

    return snapshot


def main() -> None:
    snapshot = export_market_snapshot()
    out_path = data_path("analysis", "market_snapshot.json")
    save_json_file(out_path, snapshot)
    logger.info(f"[market_snapshot_exporter] saved: {out_path}")


if __name__ == "__main__":
    main()
