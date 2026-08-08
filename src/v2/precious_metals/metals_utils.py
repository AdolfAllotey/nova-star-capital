import json
from datetime import datetime


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data, path):
    if not isinstance(data, dict):
        data = {"value": data}
    data["timestamp"] = datetime.utcnow().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def clamp(value, min_val=0.0, max_val=1.0):
    return max(min_val, min(max_val, value))


# ---------------------------------------------------------------------------
# RC2 precious-metals strict macro input contract
# ---------------------------------------------------------------------------

import math as _strict_math
from pathlib import Path as _StrictPath


class MacroInputValidationError(ValueError):
    """Raised when the precious-metals macro input contract is invalid."""


def load_json_strict(path):
    """
    Load a non-empty JSON object and fail closed on every read or schema error.

    This function intentionally does not alter the historical load_json
    behavior used by non-certified legacy consumers.
    """
    json_path = _StrictPath(path)

    if not json_path.is_file():
        raise MacroInputValidationError(
            f"required JSON file is missing: {json_path}"
        )

    try:
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise MacroInputValidationError(
            f"unable to load valid JSON from {json_path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise MacroInputValidationError(
            f"JSON root must be an object: {json_path}"
        )

    if not payload:
        raise MacroInputValidationError(
            f"JSON object must not be empty: {json_path}"
        )

    return payload


def require_mapping(payload, key):
    if not isinstance(payload, dict):
        raise MacroInputValidationError(
            f"parent payload for section {key!r} must be an object"
        )

    if key not in payload:
        raise MacroInputValidationError(
            f"required section is missing: {key}"
        )

    section = payload[key]

    if not isinstance(section, dict):
        raise MacroInputValidationError(
            f"section {key!r} must be an object"
        )

    if not section:
        raise MacroInputValidationError(
            f"section {key!r} must not be empty"
        )

    return section


def require_finite_number(
    payload,
    key,
    *,
    minimum=None,
    maximum=None,
):
    if not isinstance(payload, dict):
        raise MacroInputValidationError(
            f"parent payload for field {key!r} must be an object"
        )

    if key not in payload:
        raise MacroInputValidationError(
            f"required numeric field is missing: {key}"
        )

    value = payload[key]

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MacroInputValidationError(
            f"field {key!r} must be a finite number"
        )

    numeric = float(value)

    if not _strict_math.isfinite(numeric):
        raise MacroInputValidationError(
            f"field {key!r} must be finite"
        )

    if minimum is not None and numeric < minimum:
        raise MacroInputValidationError(
            f"field {key!r} must be >= {minimum}"
        )

    if maximum is not None and numeric > maximum:
        raise MacroInputValidationError(
            f"field {key!r} must be <= {maximum}"
        )

    return numeric


def require_non_empty_string(payload, key):
    if not isinstance(payload, dict):
        raise MacroInputValidationError(
            f"parent payload for field {key!r} must be an object"
        )

    if key not in payload:
        raise MacroInputValidationError(
            f"required string field is missing: {key}"
        )

    value = payload[key]

    if not isinstance(value, str) or not value.strip():
        raise MacroInputValidationError(
            f"field {key!r} must be a non-empty string"
        )

    return value.strip()


def validate_macro_input_contract(payload):
    if not isinstance(payload, dict) or not payload:
        raise MacroInputValidationError(
            "macro input payload must be a non-empty object"
        )

    schema_version = payload.get("schema_version")

    if str(schema_version) != "1.0":
        raise MacroInputValidationError(
            "schema_version must be 1.0"
        )

    source = payload.get("source")

    # RC2 certified provider payloads use structured source metadata.
    # Preserve the historical string-source validation path explicitly.
    if isinstance(source, str):
        require_non_empty_string(payload, "source")

    elif isinstance(source, dict):
        try:
            from src.v2.precious_metals.macro_provider_contract import (
                validate_macro_payload,
            )

            validate_macro_payload(payload)

        except Exception as exc:
            raise MacroInputValidationError(
                f"provider macro payload validation failed: {exc}"
            ) from exc

        return payload

    else:
        raise MacroInputValidationError(
            "field 'source' must be either a non-empty string "
            "or certified provider metadata mapping"
        )

    require_non_empty_string(payload, "generated_at")

    status = require_non_empty_string(payload, "status").lower()

    if status != "valid":
        raise MacroInputValidationError(
            "macro input status must be 'valid'"
        )

    inflation = require_mapping(payload, "inflation")
    require_finite_number(inflation, "cpi_yoy")
    require_finite_number(inflation, "inflation_trend_3m")
    require_finite_number(
        inflation,
        "central_bank_credibility_score",
        minimum=0.0,
        maximum=1.0,
    )

    real_rates = require_mapping(payload, "real_rates")
    require_finite_number(real_rates, "us_10y_real")
    require_finite_number(real_rates, "real_rate_trend_1m")

    systemic_stress = require_mapping(
        payload,
        "systemic_stress",
    )
    require_finite_number(
        systemic_stress,
        "stress_score",
        minimum=0.0,
        maximum=1.0,
    )
    require_finite_number(
        systemic_stress,
        "liquidity_stress",
        minimum=0.0,
        maximum=1.0,
    )
    require_finite_number(
        systemic_stress,
        "banking_stress",
        minimum=0.0,
        maximum=1.0,
    )

    usd = require_mapping(payload, "usd")
    require_finite_number(usd, "dxy", minimum=0.0)
    require_finite_number(usd, "dxy_trend_1m")

    return payload


def load_and_validate_macro_inputs(path):
    payload = load_json_strict(path)
    return validate_macro_input_contract(payload)
