#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app

PYTHON="/opt/nsc/.venv/bin/python3"
VALUATION="/opt/nsc/app/data/portfolio/long_term_valuation.json"
HISTORY="/opt/nsc/src/v2/data/reports/long_term_nav_history.json"

TMP_VAL="$(mktemp)"
TMP_NAV="$(mktemp)"

cleanup() {
    rm -f "$TMP_VAL" "$TMP_NAV"
}
trap cleanup EXIT

"$PYTHON" \
    src/v2/portfolio/long_term_consolidator.py \
    >"$TMP_VAL" 2>&1

"$PYTHON" \
    src/v2/analysis/long_term_nav_history.py \
    >"$TMP_NAV" 2>&1

"$PYTHON" - <<'PY'
from pathlib import Path
import json

valuation_path = Path(
    "/opt/nsc/app/data/portfolio/long_term_valuation.json"
)
history_path = Path(
    "/opt/nsc/src/v2/data/reports/long_term_nav_history.json"
)

valuation = json.loads(
    valuation_path.read_text(encoding="utf-8")
)
history = json.loads(
    history_path.read_text(encoding="utf-8")
)

totals = valuation.get("totals", {}) or {}
quality = valuation.get("data_quality", {}) or {}
positions = valuation.get("positions", []) or []
history_rows = history.get("history", []) or []

print("LONG_TERM_REFRESH_STATUS=PASS")
print(f"ENGINE={valuation.get('engine')}")
print(f"POSITIONS_COUNT={len(positions)}")
print(
    "MARKET_VALUE_EUR="
    f"{totals.get('market_value_eur')}"
)
print(f"PNL_EUR={totals.get('pnl_eur')}")
print(
    "DATA_QUALITY_COMPLETE="
    f"{quality.get('complete')}"
)
print(
    "FALLBACK_COUNT="
    f"{quality.get('fallback_count', 0)}"
)
print(
    "PROVIDER_ERROR_COUNT="
    f"{len(quality.get('provider_errors') or [])}"
)
print(f"NAV_HISTORY_COUNT={len(history_rows)}")
print(f"UPDATED_AT={valuation.get('updated_at')}")
PY
