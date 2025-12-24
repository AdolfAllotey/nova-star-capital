# src/v2/api/app.py
from __future__ import annotations

import importlib
import os
import pkgutil
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir

logger = get_logger("api_app")


def _parse_cors_origins(raw: Optional[str]) -> List[str]:
    if not raw:
        return ["*"]
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["*"]


def _try_include_router(app: FastAPI, module_path: str, prefix: str = "") -> None:
    """
    Tente d'importer module_path, récupère `router`, et l'inclut dans l'app.
    Loggue proprement en cas d'échec.
    """
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, "router", None)
        if router is None:
            logger.warning(f"[api_app] Router introuvable dans {module_path} (attribut 'router' absent)")
            return
        app.include_router(router, prefix=prefix)
        logger.info(f"[api_app] Router chargé: {module_path} (prefix={prefix or ''})")
    except Exception as e:
        logger.warning(f"[api_app] Router non chargé: {module_path} ({type(e).__name__}: {e})")


def _autodiscover_and_include_routes(app: FastAPI, base_pkg: str = "src.v2.api.routes") -> None:
    """
    Auto-discovery: importe tous les modules dans src.v2.api.routes.*
    Chaque module doit exposer `router` (FastAPI APIRouter).
    Si le module expose `PREFIX`, on l'utilise; sinon prefix="".
    """
    try:
        pkg = importlib.import_module(base_pkg)
    except Exception as e:
        logger.warning(f"[api_app] Impossible d'importer {base_pkg} ({type(e).__name__}: {e})")
        return

    pkg_path = getattr(pkg, "__path__", None)
    if not pkg_path:
        logger.warning(f"[api_app] {base_pkg} n'a pas de __path__ → auto-discovery impossible")
        return

    for _, name, ispkg in pkgutil.iter_modules(pkg_path):
        if ispkg:
            continue

        module_path = f"{base_pkg}.{name}"
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, "router", None)
            if router is None:
                logger.warning(f"[api_app] Skipped {module_path}: pas de 'router'")
                continue

            prefix = getattr(mod, "PREFIX", "")
            app.include_router(router, prefix=prefix)
            logger.info(f"[api_app] Router chargé: {module_path} (prefix={prefix or ''})")
        except Exception as e:
            logger.warning(f"[api_app] Router non chargé: {module_path} ({type(e).__name__}: {e})")


# ─────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Nova Star Capital API",
    version="2.0.0",
)

# ENV + DATA_DIR
ENV = os.getenv("NSC_ENV", "UNKNOWN")
DATA_DIR = get_data_dir()
logger.info(f"[api_app] DATA_DIR={DATA_DIR}, ENV={ENV}")

# CORS
cors_origins = _parse_cors_origins(os.getenv("NSC_CORS_ORIGINS"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Routers "core" (dev + assistant)
# ─────────────────────────────────────────────────────────────
# IMPORTANT : dev_router doit être monté en /dev, sinon /dev/routes etc. renverront 404
_try_include_router(app, "src.v2.api.dev_router", prefix="/dev")

# Assistant router (si présent)
_try_include_router(app, "src.v2.api.assistant_router", prefix="")

# ─────────────────────────────────────────────────────────────
# Auto-discovery des routes métiers
# ─────────────────────────────────────────────────────────────
_autodiscover_and_include_routes(app, base_pkg="src.v2.api.routes")


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "env": ENV}
