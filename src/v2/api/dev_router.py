from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir

logger = get_logger("dev_router")

# IMPORTANT:
# Le prefix /dev est déjà appliqué par api_app d'après tes logs:
# [api_app] Router chargé: src.v2.api.dev_router (prefix=/dev)
# Donc ici ON NE MET PAS prefix="/dev" pour éviter /dev/dev/...
router = APIRouter(tags=["dev"])


def _safe_env(key: str) -> Optional[str]:
    v = os.getenv(key)
    return v if v not in ("", None) else None


def _resolve_root_dir() -> str:
    # On privilégie NSC_PROJECT_ROOT, sinon on remonte depuis ce fichier
    env_root = _safe_env("NSC_PROJECT_ROOT") or _safe_env("NSC_ROOT_DIR")
    if env_root:
        return str(Path(env_root))
    # fallback: /opt/nsc/app (dans ton cas) via le layout src/v2/api
    return str(Path(__file__).resolve().parents[3])


def _resolve_data_dir() -> str:
    # get_data_dir() doit déjà gérer la priorité env vars / fallback
    return str(get_data_dir())


def _selected_tokens_path(data_dir: str) -> str:
    return str(Path(data_dir) / "selected_tokens.json")


def _count_files(base: Path) -> int:
    if not base.exists():
        return 0
    total = 0
    for _, _, files in os.walk(str(base)):
        total += len(files)
    return total


def _missing_expected_files(data_dir: Path) -> List[str]:
    """
    Liste minimale des fichiers attendus en préprod.
    Ajuste si tu veux être plus strict.
    """
    expected = [
        data_dir / "selected_tokens.json",
        data_dir / "reports" / "daily_report.json",
        data_dir / "reports" / "daily_report_summary.json",
        data_dir / "reports" / "trade_simulation.json",
        data_dir / "risk" / "worst_trades.json",
        data_dir / "risk" / "token_blacklist.json",
        data_dir / "analysis" / "sentiment_overview.json",
        data_dir / "market" / "market_overview.json",
    ]
    missing = []
    for p in expected:
        if not p.exists():
            missing.append(str(p))
    return missing


@router.get("/info")
def dev_info() -> Dict[str, Any]:
    """
    Renvoie les infos runtime minimales.
    """
    data_dir = _resolve_data_dir()
    return {
        "env": _safe_env("NSC_ENV") or "UNKNOWN",
        "api_version": "2.0.0",
        "data_dir": data_dir,
        "assistant_model": _safe_env("NSC_ASSISTANT_MODEL"),
        "openai_configured": bool(_safe_env("OPENAI_API_KEY")),
    }


@router.get("/config")
def dev_config() -> Dict[str, Any]:
    """
    Expose la résolution des chemins / variables pour debug systemd.
    """
    resolved_root = _resolve_root_dir()
    resolved_data = _resolve_data_dir()
    return {
        "env": _safe_env("NSC_ENV") or "UNKNOWN",
        "resolution": {
            "NSC_PROJECT_ROOT": _safe_env("NSC_PROJECT_ROOT"),
            "NSC_ROOT_DIR": _safe_env("NSC_ROOT_DIR"),
            "NSC_DATA_DIR": _safe_env("NSC_DATA_DIR"),
            "DATA_ROOT": _safe_env("DATA_ROOT"),
            "DATA_DIR": _safe_env("DATA_DIR"),
            "resolved_root_dir": resolved_root,
            "resolved_data_dir": resolved_data,
            "selected_tokens_path": _selected_tokens_path(resolved_data),
        },
    }


@router.get("/routes")
def dev_routes(request: Request) -> Dict[str, Any]:
    """
    Liste toutes les routes FastAPI (utile pour vérifier qu'une route existe).
    """
    routes_out: List[Dict[str, Any]] = []
    for r in request.app.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", None)
        name = getattr(r, "name", None)
        if path:
            routes_out.append(
                {
                    "path": path,
                    "name": name,
                    "methods": sorted(list(methods)) if methods else None,
                }
            )
    routes_out.sort(key=lambda x: x["path"])
    return {"count": len(routes_out), "routes": routes_out}


@router.get("/files")
def dev_files() -> Dict[str, Any]:
    """
    Donne un état de présence des fichiers attendus + compte des fichiers.
    """
    data_dir = Path(_resolve_data_dir())
    missing = _missing_expected_files(data_dir)
    return {
        "data_dir": str(data_dir),
        "exists": data_dir.exists(),
        "metrics": {
            "total_files": _count_files(data_dir),
        },
        "nb_missing": len(missing),
        "missing": missing,
    }


@router.get("/engines/status")
def dev_engines_status() -> Dict[str, Any]:
    """
    Statut léger: nombre de fichiers dans DATA_DIR.
    (Tu avais déjà un endpoint similaire.)
    """
    data_dir = Path(_resolve_data_dir())
    return {
        "data_dir": str(data_dir),
        "metrics": {
            "total_files": _count_files(data_dir),
        },
    }


@router.get("/knowledge/status")
def dev_knowledge_status() -> Dict[str, Any]:
    """
    Endpoint attendu par tes checks.
    On considère ici que la "knowledge base" quotidienne existe si
    daily_report.json est présent (à adapter si tu utilises un autre artefact).
    """
    data_dir = Path(_resolve_data_dir())
    daily_report = data_dir / "reports" / "daily_report.json"
    return {
        "data_dir": str(data_dir),
        "daily_report": {
            "path": str(daily_report),
            "exists": daily_report.exists(),
        },
    }
