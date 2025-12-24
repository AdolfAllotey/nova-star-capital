from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import data_path, load_json_file, save_json_file, now_ts

logger = get_logger("daily_report")

# Répertoire canonique reports (FINI le hardcode src/v2/data/reports)
REPORT_DIR: Path = data_path("reports")


def generate_daily_report() -> Dict[str, Any]:
    """
    Génère un rapport quotidien simple (placeholder / base).
    Tu pourras enrichir ensuite avec tes sections réelles.
    """
    report: Dict[str, Any] = {
        "timestamp": now_ts(),
        "sections": {},
        "meta": {},
    }

    # Exemple : si tu as des fichiers à agréger, fais-le ici en canonique
    # market_overview = load_json_file(data_path("market", "overview.json"), default={})
    # report["sections"]["market_overview"] = market_overview

    return report


def save_daily_report(report: Dict[str, Any], filename: str = "daily_report.json") -> Path:
    """
    Sauvegarde le rapport dans data/reports/.
    """
    out_path = REPORT_DIR / filename
    save_json_file(out_path, report)
    logger.info(f"[daily_report] saved: {out_path}")
    return out_path


def main() -> None:
    report = generate_daily_report()
    save_daily_report(report)


if __name__ == "__main__":
    main()
