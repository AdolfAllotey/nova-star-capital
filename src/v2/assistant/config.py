"""
src/v2/assistant/config.py

Détection centralisée de la configuration du projet NSC pour l'assistant autonome.

- Détecte ROOT_DIR à partir de la position de ce fichier (ou de NSC_ROOT_DIR)
- Construit les chemins :
    - root_dir
    - data_dir
    - react_dir
    - api_dir
- Vérifie l'existence des chemins (paths_exist)
- Expose get_config() pour les autres modules (executor, project_map, tasks, etc.)
- CLI :
    python -m src.v2.assistant.config
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _detect_root_dir() -> str:
    """
    Détecte le ROOT_DIR du projet NSC.

    Stratégie :
    1) Si NSC_ROOT_DIR est défini dans l'env, on l'utilise.
    2) Sinon, on remonte à partir de ce fichier jusqu'à la racine du projet.
       Ici : src/v2/assistant/config.py -> .../src/v2/assistant -> .../src/v2 -> .../src -> .../
    """
    env_root = os.environ.get("NSC_ROOT_DIR")
    if env_root:
        return os.path.abspath(env_root)

    # On part du dossier courant de ce fichier
    here = os.path.dirname(os.path.abspath(__file__))
    # remonte 3 niveaux : assistant -> v2 -> src -> root
    root_dir = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return root_dir


def get_config() -> Dict[str, Any]:
    """
    Retourne la configuration détectée pour l'assistant NSC.

    Exemple :
    {
      "root_dir": "/opt/nsc/app",
      "data_dir": "/opt/nsc/app/data",
      "react_dir": "/opt/nsc/app/src/v2/interface/react",
      "api_dir": "/opt/nsc/app/src/v2/api",
      "paths_exist": {
        "root_dir": true,
        "data_dir": true,
        "react_dir": true,
        "api_dir": true
      }
    }
    """
    root_dir = _detect_root_dir()

    data_dir = os.path.join(root_dir, "data")
    react_dir = os.path.join(root_dir, "src", "v2", "interface", "react")
    api_dir = os.path.join(root_dir, "src", "v2", "api")

    cfg: Dict[str, Any] = {
        "root_dir": root_dir,
        "data_dir": data_dir,
        "react_dir": react_dir,
        "api_dir": api_dir,
        "paths_exist": {
            "root_dir": os.path.isdir(root_dir),
            "data_dir": os.path.isdir(data_dir),
            "react_dir": os.path.isdir(react_dir),
            "api_dir": os.path.isdir(api_dir),
        },
    }

    return cfg


def main() -> None:
    """
    Entrée CLI : python -m src.v2.assistant.config

    Affiche la configuration détectée en JSON.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:%(name)s:%(message)s",
        )

    cfg = get_config()
    logger.info("[assistant.config] Configuration détectée : %s", cfg)
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
