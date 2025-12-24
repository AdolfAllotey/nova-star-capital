# src/v2/utils/file_utils.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.v2.utils.logger import get_logger

logger = get_logger("file_utils")

PathLike = Union[str, Path]

# ---------------------------------------------------------
# ROOT + DATA resolution (PREPROD compatible)
# ---------------------------------------------------------

def get_root_dir() -> Path:
    """
    Détecte le ROOT_DIR du projet NSC.

    Priorité :
    1) NSC_PROJECT_ROOT (systemd)
    2) NSC_ROOT_DIR (legacy)
    3) Remonte depuis ce fichier (best-effort)
    """
    env = os.getenv("NSC_PROJECT_ROOT") or os.getenv("NSC_ROOT_DIR")
    if env and env.strip():
        return Path(env).expanduser().resolve()

    # file_utils.py : src/v2/utils/file_utils.py
    # -> parents: utils -> v2 -> src -> app
    return Path(__file__).resolve().parents[3]


def get_data_dir() -> Path:
    """
    Source of truth pour la racine DATA.

    Priorité :
    1) NSC_DATA_DIR (systemd)
    2) NSC_DATA_ROOT (legacy)
    3) DATA_ROOT (systemd)
    4) DATA_DIR (legacy)
    5) fallback stable: <project_root>/data   (ex: /opt/nsc/app/data)
    """
    for key in ("NSC_DATA_DIR", "NSC_DATA_ROOT", "DATA_ROOT", "DATA_DIR"):
        v = os.getenv(key)
        if v and v.strip():
            return Path(v).expanduser().resolve()

    return (get_root_dir() / "data").resolve()


DATA_DIR: Path = get_data_dir()


def data_path(*parts: str) -> Path:
    """
    Construit un chemin dans DATA_DIR.
    Exemple: data_path("analysis", "market_regime_detector.json")
    """
    return (DATA_DIR / Path(*parts)).resolve()


def _resolve_path(path: PathLike) -> Path:
    """
    Résout un chemin en garantissant que tout chemin relatif est rebased sous DATA_DIR.

    - Si `path` est absolu -> retourné tel quel
    - Si `path` commence par `src/v2/data/...` -> on rebased le suffixe sous DATA_DIR
    - Si `path` commence par `data/...` -> idem
    - Sinon -> DATA_DIR / path
    """
    pp = Path(path)

    if pp.is_absolute():
        return pp

    parts = pp.parts

    # drop leading "src/v2/data"
    if len(parts) >= 3 and parts[0] == "src" and parts[1] == "v2" and parts[2] == "data":
        suffix = Path(*parts[3:]) if len(parts) > 3 else Path()
        return (DATA_DIR / suffix).resolve()

    # drop leading "data"
    if len(parts) >= 1 and parts[0] == "data":
        suffix = Path(*parts[1:]) if len(parts) > 1 else Path()
        return (DATA_DIR / suffix).resolve()

    return (DATA_DIR / pp).resolve()


# ---------------------------------------------------------
# UTILITAIRE : CRÉER LE DOSSIER SI MANQUANT
# ---------------------------------------------------------
def ensure_directory_exists(path: PathLike) -> None:
    """
    Creates the directory for the file if it does not exist.
    Safe for systemd services writing JSON files.
    """
    try:
        p = Path(path)
        directory = p.parent
        if directory and not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", directory)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to ensure directory exists for %s : %s", path, e)


# Backward-compatible alias (legacy name)
def ensure_dir(path: PathLike) -> None:
    return ensure_directory_exists(path)


# ---------------------------------------------------------
# JSON helpers (robustes + unifiés)
# ---------------------------------------------------------
def load_json_file(path: PathLike, default: Any = None) -> Any:
    """
    Loads a JSON file and returns its data.
    If file missing or invalid -> returns default.

    IMPORTANT:
    - path relatif est rebased sous DATA_DIR via _resolve_path()
    """
    p = _resolve_path(path)

    if not p.exists():
        try:
            logger.warning("JSON file not found: %s → returning default", p)
        except Exception:
            pass
        return default

    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in %s: %s", p, e)
        return default
    except Exception as e:  # noqa: BLE001
        logger.error("Error loading JSON file %s: %s", p, e)
        return default


def save_json_file(path: PathLike, data: Any, indent: int = 2) -> str:
    """
    Saves data to a JSON file with UTF-8 encoding.
    Ensures directory exists before writing.
    Returns the resolved path as string.

    IMPORTANT:
    - path relatif est rebased sous DATA_DIR via _resolve_path()
    """
    p = _resolve_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        try:
            logger.info("Saved JSON file: %s", p)
        except Exception:
            pass
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to save JSON file %s: %s", p, e)

    return str(p)


# ---------------------------------------------------------
# UTILITAIRE : TIMESTAMP ISO
# ---------------------------------------------------------
def now_ts() -> str:
    # timezone-aware (évite le warning utcnow)
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# TOKENS SÉLECTIONNÉS
# ---------------------------------------------------------
def selected_tokens_path() -> Path:
    # Toujours dans DATA_DIR
    return data_path("selected_tokens.json")


def load_selected_tokens() -> List[str]:
    """
    Loads selected tokens from selected_tokens.json.
    If the file is missing or invalid → returns empty list.

    Accepts:
      - {"tokens": [...]}
      - [...]
    """
    tokens = load_json_file(selected_tokens_path(), default=[])

    if isinstance(tokens, dict) and isinstance(tokens.get("tokens"), list):
        return [str(x) for x in tokens["tokens"]]

    if isinstance(tokens, list):
        return [str(x) for x in tokens]

    logger.warning("selected_tokens.json format unexpected, returning empty list")
    return []


# ---------------------------------------------------------
# CAPITAL ALLOCATION (compat ancien + nouveau schéma)
# ---------------------------------------------------------
def load_capital_allocation(trading_dir: Optional[PathLike] = None, default: Optional[dict] = None) -> Dict[str, Any]:
    """
    Charge capital_allocation.json et renvoie un dict NORMALISÉ,
    compatible avec:
    - schéma legacy: total_capital, pockets, max_concurrent_positions
    - schéma new: total_budget, trading_budget, trading_ratio, max_positions

    Retourne toujours:
      total_budget, trading_budget, trading_ratio, capital_per_trade, max_positions
    Et conserve aussi des alias legacy:
      total_capital, pockets, max_concurrent_positions
    """
    if default is None:
        default = {}

    if trading_dir is None:
        trading_dir_path = data_path("trading")
    else:
        trading_dir_path = _resolve_path(trading_dir)

    path = trading_dir_path / "capital_allocation.json"
    data = load_json_file(path, default=default) or {}
    if not isinstance(data, dict):
        data = {}

    # --- Nouvel schéma
    total_budget = float(data.get("total_budget") or 0.0)
    trading_budget = float(data.get("trading_budget") or 0.0)
    max_positions = data.get("max_positions")

    # --- Legacy
    total_capital = float(data.get("total_capital") or 0.0)
    pockets = data.get("pockets") if isinstance(data.get("pockets"), dict) else {}
    max_concurrent_positions = data.get("max_concurrent_positions")

    # fallback: si nouveau schéma absent, on dérive depuis legacy
    if total_budget <= 0 and total_capital > 0:
        total_budget = total_capital

    if trading_budget <= 0 and pockets:
        trading_budget = float(pockets.get("trading") or 0.0)

    if max_positions in (None, "", 0):
        max_positions = max_concurrent_positions if max_concurrent_positions not in (None, "", 0) else None

    try:
        max_positions_i = int(max_positions) if max_positions is not None else 0
    except Exception:
        max_positions_i = 0

    # trading_ratio
    trading_ratio = data.get("trading_ratio")
    try:
        trading_ratio_f = float(trading_ratio) if trading_ratio is not None else 0.0
    except Exception:
        trading_ratio_f = 0.0
    if trading_ratio_f <= 0 and total_budget > 0 and trading_budget > 0:
        trading_ratio_f = trading_budget / total_budget

    # capital_per_trade
    cpt = data.get("capital_per_trade")
    try:
        capital_per_trade = float(cpt) if cpt is not None else 0.0
    except Exception:
        capital_per_trade = 0.0
    if capital_per_trade <= 0 and max_positions_i > 0 and trading_budget > 0:
        capital_per_trade = trading_budget / max_positions_i

    # alias legacy garantis
    if not pockets:
        pockets = {"trading": float(trading_budget)} if trading_budget > 0 else {}

    if total_capital <= 0 and total_budget > 0:
        total_capital = total_budget

    if not max_concurrent_positions and max_positions_i > 0:
        max_concurrent_positions = max_positions_i

    normalized = dict(data)
    normalized.update(
        {
            # normalized
            "total_budget": float(total_budget),
            "trading_budget": float(trading_budget),
            "trading_ratio": float(trading_ratio_f),
            "capital_per_trade": float(capital_per_trade),
            "max_positions": int(max_positions_i) if max_positions_i else 0,
            # legacy aliases
            "total_capital": float(total_capital),
            "pockets": pockets,
            "max_concurrent_positions": int(max_concurrent_positions) if max_concurrent_positions else 0,
        }
    )
    return normalized


# ---------------------------------------------------------
# DEBUG helper
# ---------------------------------------------------------
def debug_data_resolution() -> Dict[str, Any]:
    return {
        "NSC_PROJECT_ROOT": os.getenv("NSC_PROJECT_ROOT"),
        "NSC_ROOT_DIR": os.getenv("NSC_ROOT_DIR"),
        "NSC_DATA_DIR": os.getenv("NSC_DATA_DIR"),
        "NSC_DATA_ROOT": os.getenv("NSC_DATA_ROOT"),
        "DATA_ROOT": os.getenv("DATA_ROOT"),
        "DATA_DIR": os.getenv("DATA_DIR"),
        "resolved_root_dir": str(get_root_dir()),
        "resolved_data_dir": str(get_data_dir()),
        "DATA_DIR_const": str(DATA_DIR),
        "selected_tokens_path": str(selected_tokens_path()),
    }
