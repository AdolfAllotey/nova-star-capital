from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse


router = APIRouter(tags=["market-memory"])


def _data_root() -> Path:
    configured = os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod")
    return Path(configured)


def _market_memory_path() -> Path:
    return _data_root() / "market_memory" / "market_memory.json"


def _empty_payload(
    *,
    status: str,
    reason: str,
    source_path: Path,
) -> dict[str, Any]:
    return {
        "status": status,
        "available": False,
        "reason": reason,
        "source": str(source_path),
        "assets_count": 0,
        "assets": [],
    }


@router.get(
    "/api/market-memory",
    operation_id="get_market_memory_api",
)
def get_market_memory() -> Any:
    source_path = _market_memory_path()

    if not source_path.exists():
        return JSONResponse(
            status_code=200,
            content=_empty_payload(
                status="unavailable",
                reason="market_memory_artifact_missing",
                source_path=source_path,
            ),
        )

    try:
        payload = json.loads(
            source_path.read_text(
                encoding="utf-8",
                errors="strict",
            )
        )
    except json.JSONDecodeError as exc:
        return JSONResponse(
            status_code=200,
            content={
                **_empty_payload(
                    status="error",
                    reason="market_memory_artifact_invalid_json",
                    source_path=source_path,
                ),
                "error": str(exc),
            },
        )
    except OSError as exc:
        return JSONResponse(
            status_code=200,
            content={
                **_empty_payload(
                    status="error",
                    reason="market_memory_artifact_read_failed",
                    source_path=source_path,
                ),
                "error": str(exc),
            },
        )

    if isinstance(payload, dict):
        response = dict(payload)
        response.setdefault("status", "ok")
        response.setdefault("available", True)
        response.setdefault("source", str(source_path))

        if "assets_count" not in response:
            assets = response.get("assets")

            if isinstance(assets, list):
                response["assets_count"] = len(assets)
            elif isinstance(assets, dict):
                response["assets_count"] = len(assets)

        return response

    if isinstance(payload, list):
        return {
            "status": "ok",
            "available": True,
            "source": str(source_path),
            "assets_count": len(payload),
            "assets": payload,
        }

    return {
        "status": "ok",
        "available": True,
        "source": str(source_path),
        "assets_count": 0,
        "data": payload,
    }
