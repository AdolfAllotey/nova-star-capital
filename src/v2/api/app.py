# src/v2/api/app.py
from __future__ import annotations

import importlib
import os
import pkgutil
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from src.v2.api.routes.family_office import router as family_office_router
import json
from pathlib import Path
from src.v2.api.routes.governance import router as governance_router
from src.v2.api.routes.risk import router as risk_router
from src.v2.api.routes.monitoring import router as monitoring_router

from fastapi.middleware.cors import CORSMiddleware

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir
from src.v2.api.routes.long_term import router as long_term_router
from src.v2.api.routes.long_term_valuation import router as long_term_valuation_router
from src.v2.api.routes.execution_plan import router as execution_plan_router
from src.v2.api.routes.execution_orders import router as execution_orders_router
from src.v2.api.routes.equity_curve import router as equity_curve_router
from src.v2.api.routes.lt_curve import router as lt_curve_router
from src.v2.api.routes.brick_curve import router as brick_curve_router
from src.v2.api.routes.total_curve import router as total_curve_router

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
from src.v2.api.routes.crypto_overview import router as crypto_overview_router
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
DEV_ROUTER_ENVIRONMENTS = {
    "DEV",
    "DEVELOPMENT",
    "LOCAL",
    "TEST",
}

if ENV.strip().upper() in DEV_ROUTER_ENVIRONMENTS:
    _try_include_router(app, "src.v2.api.dev_router", prefix="/dev")
else:
    logger.info(
        "[api_app] Routeur dev désactivé pour NSC_ENV=%s",
        ENV,
    )

# Assistant router (si présent)
_try_include_router(app, "src.v2.api.assistant_router", prefix="")
_try_include_router(app, "src.v2.api.ico_router", prefix="")
app.include_router(long_term_router)
app.include_router(long_term_valuation_router, prefix="/api")
app.include_router(equity_curve_router, prefix="/api")
app.include_router(lt_curve_router, prefix="/api")
app.include_router(brick_curve_router, prefix="/api")
app.include_router(total_curve_router, prefix="/api")
from src.v2.api.routes.long_term_valuation import router as long_term_valuation_router
app.include_router(execution_plan_router)
app.include_router(execution_orders_router)
_try_include_router(app, "src.v2.api.routes.activity_dashboard", prefix="/api")
_try_include_router(app, "src.v2.api.routes.long_term", prefix="/api")
_try_include_router(app, "src.v2.api.routes.bonds", prefix="")
_try_include_router(app, "src.v2.api.routes.precious_metals", prefix="")
_try_include_router(app, "src.v2.api.routes.explainability", prefix="")
_try_include_router(app, "src.v2.api.routes.dashboard_v3", prefix="")
_try_include_router(app, "src.v2.api.routes.market_intelligence", prefix="")
_try_include_router(app, "src.v2.api.routes.market_memory", prefix="")
_try_include_router(app, "src.v2.api.routes.system_status", prefix="")
_try_include_router(app, "src.v2.api.routes.executive_decision", prefix="")
_try_include_router(app, "src.v2.api.routes.documentation_center", prefix="")
_try_include_router(app, "src.v2.api.routes.go_no_go", prefix="")
app.include_router(crypto_overview_router)

# ─────────────────────────────────────────────────────────────
# Auto-discovery des routes métiers
# ─────────────────────────────────────────────────────────────
_autodiscover_and_include_routes(app, base_pkg="src.v2.api.routes")


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> Dict[str, Any]:
    import os, time
    return {
        "status": "ok",
        "ts": int(time.time()),
        "env": os.getenv("ENV") or os.getenv("NSC_ENV") or "unknown",
        "nsc_env": os.getenv("NSC_ENV"),
        "dry_run": os.getenv("DRY_RUN"),
        "execution_mode": os.getenv("EXECUTION_MODE"),
        "action_policy": os.getenv("ACTION_POLICY"),
        "twitter_enabled": os.getenv("TWITTER_ENABLED"),
    }

@app.get("/options/v2/dashboard")
def get_options_v2_dashboard():
    path = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json")
    if not path.exists():
        return {
            "status": "missing",
            "message": "options_v2_dashboard.json absent"
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Family Office API
app.include_router(family_office_router, prefix="/api")


def _deduplicate_exact_routes(application: FastAPI) -> int:
    """
    Supprime uniquement les enregistrements de routes strictement identiques.

    Une route est considérée comme identique lorsque son chemin et son ensemble
    de méthodes HTTP sont identiques. La première déclaration est conservée afin
    de préserver l'ordre et le comportement historiques de résolution FastAPI.
    """
    unique_routes = []
    seen = set()
    removed = 0

    for route in application.router.routes:
        path_value = getattr(route, "path", None)
        methods_value = getattr(route, "methods", None)

        if path_value is None or methods_value is None:
            unique_routes.append(route)
            continue

        key = (
            tuple(sorted(methods_value)),
            path_value,
        )

        if key in seen:
            removed += 1
            continue

        seen.add(key)
        unique_routes.append(route)

    application.router.routes[:] = unique_routes
    return removed


EXACT_DUPLICATE_ROUTES_REMOVED = _deduplicate_exact_routes(app)

if EXACT_DUPLICATE_ROUTES_REMOVED:
    logger.warning(
        "[api_app] Routes exactes dupliquées supprimées: %s",
        EXACT_DUPLICATE_ROUTES_REMOVED,
    )
