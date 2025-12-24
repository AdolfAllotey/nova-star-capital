"""
logs_overview_light.py

Vue "institutionnelle" des logs NSC :
- Scan de src/v2/logs/*.log
- Comptage des niveaux (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- Drapeau global : ok / caution / critical
- Résumé sauvegardé dans data/analysis/logs_overview.json

Utilisé par la gouvernance / Risk Console (Saison 1).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import save_json_file

logger = get_logger("logs_overview_light")

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _get_root_and_data_dirs() -> Tuple[Path, Path]:
    """
    Calcule ROOT_DIR et DATA_DIR sans dépendre de file_utils.
    - ROOT_DIR = racine du projet (…/app)
    - DATA_DIR = NSC_DATA_DIR si défini, sinon ROOT_DIR / "data"
    """
    # /opt/nsc/app/src/v2/analysis/logs_overview_light.py
    root_dir = Path(__file__).resolve().parents[3]

    data_dir_env = os.environ.get("NSC_DATA_DIR")
    if data_dir_env:
        data_dir = Path(data_dir_env)
    else:
        data_dir = root_dir / "data"

    return root_dir, data_dir


@dataclass
class FileLogStats:
    path: str
    total_lines: int
    level_counts: Dict[str, int]


@dataclass
class LogsOverview:
    timestamp: str
    root_dir: str
    logs_dir: str
    files_scanned: int
    file_stats: List[FileLogStats]
    total_counts: Dict[str, int]
    flag: str  # "ok" | "caution" | "critical"
    reason: str


def _detect_level(line: str) -> str | None:
    """
    Détecte le niveau de log dans une ligne.

    On reste volontairement simple :
    - on cherche ' LEVEL ' dans la ligne (ex: ' INFO ', ' WARNING ', ' ERROR ')
    - sinon on renvoie None.
    """
    for level in LOG_LEVELS:
        token = f" {level} "
        if token in line:
            return level
    return None


def _compute_flag(total_counts: Dict[str, int]) -> Tuple[str, str]:
    """
    Détermine un flag global simple :
    - critical si >= 1 CRITICAL
    - critical si >= 10 ERROR
    - caution si 1–9 ERROR ou >= 20 WARNING
    - ok sinon
    """
    errors = total_counts.get("ERROR", 0)
    critical = total_counts.get("CRITICAL", 0)
    warnings = total_counts.get("WARNING", 0)

    if critical >= 1 or errors >= 10:
        return "critical", f"critical={critical}, errors={errors} (seuils dépassés)"
    if errors > 0 or warnings >= 20:
        return "caution", f"errors={errors}, warnings={warnings} (zone de vigilance)"
    return "ok", f"errors={errors}, warnings={warnings} (rien de notable)"


def compute_logs_overview() -> LogsOverview:
    """
    Scan des fichiers de logs et construction d'un overview institutionnel.
    """
    root_dir, data_dir = _get_root_and_data_dirs()
    logs_dir = root_dir / "src" / "v2" / "logs"

    logger.info(
        "[logs_overview_light] ROOT_DIR=%s, DATA_DIR=%s, LOGS_DIR=%s",
        root_dir,
        data_dir,
        logs_dir,
    )

    file_stats: List[FileLogStats] = []
    total_counts: Dict[str, int] = {lvl: 0 for lvl in LOG_LEVELS}

    if not logs_dir.exists() or not logs_dir.is_dir():
        logger.warning("[logs_overview_light] Dossier logs inexistant: %s", logs_dir)
    else:
        for log_file in sorted(logs_dir.glob("*.log")):
            try:
                level_counts = {lvl: 0 for lvl in LOG_LEVELS}
                total_lines = 0

                with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        total_lines += 1
                        lvl = _detect_level(line)
                        if lvl:
                            level_counts[lvl] += 1
                            total_counts[lvl] += 1

                file_stats.append(
                    FileLogStats(
                        path=str(log_file.relative_to(root_dir)),
                        total_lines=total_lines,
                        level_counts=level_counts,
                    )
                )
            except Exception as exc:  # pragma: no cover – robustesse
                logger.exception(
                    "[logs_overview_light] Erreur lors de la lecture du fichier de log %s: %s",
                    log_file,
                    exc,
                )

    flag, reason = _compute_flag(total_counts)

    overview = LogsOverview(
        timestamp=datetime.now(timezone.utc).isoformat(),
        root_dir=str(root_dir),
        logs_dir=str(logs_dir),
        files_scanned=len(file_stats),
        file_stats=file_stats,
        total_counts=total_counts,
        flag=flag,
        reason=reason,
    )

    return overview


def save_logs_overview(overview: LogsOverview) -> Path:
    """
    Sauvegarde l'overview dans data/analysis/logs_overview.json.
    """
    root_dir, data_dir = _get_root_and_data_dirs()
    output_path = data_dir / "analysis" / "logs_overview.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = asdict(overview)
    save_json_file(output_path, payload)
    logger.info(
        "[logs_overview_light] logs_overview.json sauvegardé (%s, flag=%s).",
        output_path,
        overview.flag,
    )
    return output_path


def main() -> None:
    overview = compute_logs_overview()
    save_logs_overview(overview)


if __name__ == "__main__":
    main()
