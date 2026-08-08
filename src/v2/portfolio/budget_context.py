from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.v2.core.fx import FXService, FXServiceError
from src.v2.utils.file_utils import load_json_file


def load_budget_context(
    root: Path,
    scope: str = "equities_offensive",
) -> Dict[str, Any]:
    """
    Load the canonical Portfolio pocket and convert it into USD.

    Source of truth:
        portfolio/pockets.json

    The Portfolio budget is denominated in EUR and converted through
    the canonical Core FX service. No legacy monetary source is used.
    """
    pockets_path = root / "portfolio/pockets.json"
    pockets_doc = (
        load_json_file(str(pockets_path), default={}) or {}
    )

    context: Dict[str, Any] = {
        "status": "blocked",
        "scope": scope,
        "budget_source": str(pockets_path),
        "budget_source_engine": (
            pockets_doc.get("engine")
            if isinstance(pockets_doc, dict)
            else None
        ),
        "budget_source_timestamp": (
            pockets_doc.get("ts")
            if isinstance(pockets_doc, dict)
            else None
        ),
        "source_currency": None,
        "target_currency": "USD",
        "budget_eur": 0.0,
        "budget_usd": 0.0,
        "fx": None,
        "error": None,
    }

    if not isinstance(pockets_doc, dict):
        context["error"] = "invalid_pockets_document"
        return context

    source_currency = str(
        pockets_doc.get("currency") or "EUR"
    ).strip().upper()

    context["source_currency"] = source_currency

    pockets = pockets_doc.get("pockets")

    if not isinstance(pockets, dict):
        context["error"] = "pockets_missing_or_invalid"
        return context

    pocket = pockets.get(scope)

    if not isinstance(pocket, dict):
        context["error"] = f"pocket_missing:{scope}"
        return context

    raw_budget = pocket.get("budget_eur")

    if raw_budget is None:
        context["error"] = (
            f"canonical_budget_eur_missing:{scope}"
        )
        return context

    try:
        budget_eur = float(raw_budget)
    except Exception:
        context["error"] = (
            f"canonical_budget_eur_invalid:{raw_budget!r}"
        )
        return context

    context["budget_eur"] = budget_eur

    if source_currency != "EUR":
        context["error"] = (
            "unsupported_portfolio_currency:"
            f"{source_currency}"
        )
        return context

    if budget_eur <= 0:
        context["error"] = "canonical_budget_not_positive"
        return context

    try:
        conversion = FXService().convert(
            budget_eur,
            "EUR",
            "USD",
        )
    except FXServiceError as exc:
        context["error"] = (
            f"fx_service_error:{type(exc).__name__}:{exc}"
        )
        return context
    except Exception as exc:
        context["error"] = (
            "fx_unexpected_error:"
            f"{type(exc).__name__}:{exc}"
        )
        return context

    rate = conversion.rate_metadata

    context.update(
        {
            "status": "ok",
            "budget_usd": round(
                float(conversion.converted_amount),
                8,
            ),
            "fx": {
                "pair": rate.pair,
                "rate": rate.rate,
                "provider": rate.provider,
                "market_timestamp": rate.market_timestamp,
                "retrieved_at": rate.retrieved_at,
                "is_cached": rate.is_cached,
                "cache_age_seconds": (
                    rate.cache_age_seconds
                ),
                "inverted": rate.inverted,
            },
            "error": None,
        }
    )

    return context
