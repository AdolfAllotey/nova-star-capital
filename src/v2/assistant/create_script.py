from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from .config import get_config
# On n'utilise pas le logger pour éviter de polluer la sortie JSON.
# from src.v2.utils.logger import get_logger

# logger = get_logger(__name__)


def _normalize_name(raw: str) -> str:
    """
    Normalise un nom de script en snake_case safe :
    - minuscules
    - espaces et tirets -> underscore
    - caractères non alphanumériques -> supprimés
    - multiples "_" compressés
    """
    name = raw.strip().lower()
    name = re.sub(r"[ \-]+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name)
    return name


def _get_project_root() -> Path:
    cfg = get_config()
    return Path(cfg["root_dir"])


def _get_template(kind: str, name: str) -> str:
    """
    Retourne le code template en fonction du type de script.
    """
    if kind == "analysis_engine":
        return f'''from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def _get_data_dir() -> Path:
    """
    Retourne le DATA_DIR du projet.
    On essaie d'abord get_data_dir() si disponible, sinon on lit la config assistant.
    """
    try:
        # type: ignore[attr-defined]
        from src.v2.utils.file_utils import get_data_dir as _gd  # noqa: F401

        return _gd()  # type: ignore[no-any-return]
    except Exception:
        from src.v2.assistant.config import get_config  # type: ignore

        cfg = get_config()
        return Path(cfg["data_dir"])


def compute_anomalies() -> Dict[str, Any]:
    """
    Exemple de squelette d'engine d'analyse.
    À adapter à ta logique réelle.
    """
    data_dir = _get_data_dir()
    logger.info("[{name}] DATA_DIR=%s", data_dir)

    # TODO: implémenter la vraie logique d'analyse ici.
    # Exemple: lire des fichiers d'analyse intermédiaires et détecter des flags.
    result: Dict[str, Any] = {{
        "engine": "{name}",
        "version": 1,
        "global_flag": "ok",
        "nb_anomalies": 0,
        "nb_critical": 0,
        "nb_warning": 0,
        "details": [],
    }}
    return result


def main() -> None:
    """
    Point d'entrée de l'engine. Sauvegarde le résultat dans data/analysis/{name}_overview.json
    """
    data_dir = _get_data_dir()
    out_dir = data_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "{name}_overview.json"
    overview = compute_anomalies()
    save_json_file(out_path, overview)
    logger.info(
        "[{name}] {name}_overview.json sauvegardé (%s, anomalies=%d, critical=%d, warning=%d).",
        out_path,
        overview.get("nb_anomalies", 0),
        overview.get("nb_critical", 0),
        overview.get("nb_warning", 0),
    )


if __name__ == "__main__":
    main()
'''

    if kind == "trading_task":
        return f'''from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def _get_data_dir() -> Path:
    """
    Retourne le DATA_DIR du projet.
    On essaie d'abord get_data_dir() si disponible, sinon on lit la config assistant.
    """
    try:
        # type: ignore[attr-defined]
        from src.v2.utils.file_utils import get_data_dir as _gd  # noqa: F401

        return _gd()  # type: ignore[no-any-return]
    except Exception:
        from src.v2.assistant.config import get_config  # type: ignore

        cfg = get_config()
        return Path(cfg["data_dir"])


def main() -> None:
    """
    Trading task de base.
    À adapter pour intégrer cette étape dans la boucle quotidienne NSC.
    """
    data_dir = _get_data_dir()
    logger.info("[{name}] DATA_DIR=%s", data_dir)

    # TODO: implémenter la logique réelle de la trading task.
    # Exemple:
    # config_path = data_dir / "config" / "{name}.json"
    # config = load_json_file(config_path, default={{}})
    # logger.info("[{name}] Config chargée: %%s", config)

    logger.info("[{name}] Terminé.")


if __name__ == "__main__":
    main()
'''

    raise ValueError(f"Type de script inconnu: {kind}")


def _get_target_path(root: Path, kind: str, name: str) -> Path:
    """
    Détermine où placer le fichier en fonction du type.
    """
    if kind == "analysis_engine":
        return root / "src" / "v2" / "analysis" / f"{name}.py"
    if kind == "trading_task":
        return root / "src" / "v2" / "trading" / f"{name}.py"

    # fallback générique: module helper
    return root / "src" / "v2" / "helpers" / f"{name}.py"


def create_script(
    raw_name: str,
    kind: str,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Crée un script de type donné dans l'arborescence NSC.
    Retourne un dict résumant l'opération (pour affichage JSON).
    """
    kind = kind.strip()
    name = _normalize_name(raw_name)
    root = _get_project_root()
    target = _get_target_path(root, kind, name)

    existed = target.exists()
    template = _get_template(kind, name)

    if existed and not force:
        # logger.warning("[create_script] Le fichier existe déjà, pas de réécriture: %s", target)
        return {
            "name": name,
            "kind": kind,
            "path": str(target),
            "existed": True,
            "written": False,
            "dry_run": dry_run,
            "notes": "File already exists. Use --force pour réécrire.",
        }

    if dry_run:
        # logger.info("[create_script] DRY-RUN: script %s (%s) serait écrit dans %s", name, kind, target)
        return {
            "name": name,
            "kind": kind,
            "path": str(target),
            "existed": existed,
            "written": False,
            "dry_run": True,
            "notes": "Dry run: aucun fichier écrit.",
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template, encoding="utf-8")
    # logger.info("[create_script] Script %s (%s) écrit dans %s", name, kind, target)

    return {
        "name": name,
        "kind": kind,
        "path": str(target),
        "existed": existed,
        "written": True,
        "dry_run": False,
        "notes": "Script generated.",
    }


def main() -> None:
    # 🔇 On coupe tous les logs pour avoir une sortie 100% JSON
    logging.disable(logging.CRITICAL)

    parser = argparse.ArgumentParser(
        prog="python -m src.v2.assistant.create_script",
        description="Générateur de scripts NSC (analysis_engine, trading_task, etc.)",
    )
    parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Nom du script (ex: market_regime_detector, governor_system_light).",
    )
    parser.add_argument(
        "--kind",
        "-k",
        required=True,
        choices=["analysis_engine", "trading_task"],
        help="Type de script à générer.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Réécrit le fichier s'il existe déjà.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne crée pas le fichier, affiche seulement ce qui serait fait.",
    )

    args = parser.parse_args()

    result = create_script(
        raw_name=args.name,
        kind=args.kind,
        force=bool(args.force),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
