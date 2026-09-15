#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/nsc/app"
PYTHON="/opt/nsc/.venv/bin/python3"

PROVIDER_DIR="$APP_DIR/src/v2/equities_offensive/market/providers"
DATA_DIR="/opt/nsc/data/preprod/equities_offensive/market/providers"

LOCK_FILE="/run/lock/nsc-equities-provider-refresh.lock"
BEFORE_FILE="$(mktemp)"
AFTER_FILE="$(mktemp)"

cleanup() {
  rm -f "$BEFORE_FILE" "$AFTER_FILE"
}
trap cleanup EXIT

cd "$APP_DIR"

exec 9>"$LOCK_FILE"

if ! flock -n 9; then
  echo "STATUS=SKIPPED_ALREADY_RUNNING"
  exit 0
fi

echo "CONTROL=RC1_02B_EQUITIES_PROVIDER_REFRESH"
echo "STARTED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

snapshot_execution() {
  "$PYTHON" - "$1" <<'PY'
from pathlib import Path
import json
import sys

output = Path(sys.argv[1])

roots = [
    Path("/opt/nsc/data/preprod/equities_offensive/execution"),
    Path("/opt/nsc/data/preprod/equities_offensive/broker"),
    Path("/opt/nsc/data/preprod/equities_offensive/positions"),
]

result = {}

for root in roots:
    if not root.exists():
        continue

    for path in root.rglob("*.json"):
        if path.is_file():
            result[str(path)] = {
                "mtime_ns": path.stat().st_mtime_ns,
                "size": path.stat().st_size,
            }

output.write_text(
    json.dumps(result, sort_keys=True),
    encoding="utf-8",
)
PY
}

snapshot_execution "$BEFORE_FILE"

echo "STEP=PROVIDER_LAYER"

"$PYTHON" \
  "$PROVIDER_DIR/run_provider_layer_v1.py" \
  --providers yfinance massive \
  --log-level WARNING

echo "STEP=CROSS_SOURCE_VALIDATION"

set +e

"$PYTHON" \
  "$PROVIDER_DIR/run_provider_validation_v1.py"

VALIDATION_RC=$?

set -e

snapshot_execution "$AFTER_FILE"

echo "STEP=CONTROL"

"$PYTHON" - \
  "$DATA_DIR" \
  "$BEFORE_FILE" \
  "$AFTER_FILE" \
  "$VALIDATION_RC" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

data_dir = Path(sys.argv[1])
before_path = Path(sys.argv[2])
after_path = Path(sys.argv[3])
validation_rc = int(sys.argv[4])

failures = []
observations = []

def read_json(name: str) -> dict:
    path = data_dir / name

    if not path.exists():
        failures.append(f"{name}:missing")
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(
            f"{name}:invalid_json:{type(exc).__name__}"
        )
        return {}

    if not isinstance(payload, dict):
        failures.append(f"{name}:invalid_root")
        return {}

    return payload

def symbol_count(payload: dict) -> int:
    symbols = payload.get("symbols", [])

    if isinstance(symbols, list):
        return len(symbols)

    if isinstance(symbols, dict):
        return len(symbols)

    return 0

def age_minutes(payload: dict) -> float | None:
    raw = payload.get("generated_at")

    if not raw:
        return None

    try:
        timestamp = datetime.fromisoformat(
            str(raw).replace("Z", "+00:00")
        )
    except Exception:
        return None

    now = datetime.now(timezone.utc)

    return (now - timestamp).total_seconds() / 60

yfinance = read_json("market_data_yfinance_v1.json")
massive = read_json("market_data_massive_v1.json")
layer = read_json("provider_layer_run_v1.json")
validation = read_json("provider_validation_run_v1.json")

yf_status = str(yfinance.get("status") or "unknown")
yf_count = symbol_count(yfinance)
yf_age = age_minutes(yfinance)

massive_status = str(massive.get("status") or "unknown")
massive_count = symbol_count(massive)

layer_status = str(layer.get("status") or "unknown")
canonical_modified = layer.get(
    "canonical_files_modified"
)
promotion_executed = layer.get(
    "promotion_executed"
)

validation_status = str(
    validation.get("status") or "unknown"
)

gate_decision = str(
    validation.get("quality_gate_decision")
    or "NOT_RUN"
)

gate_status = (
    validation_status
    if gate_decision != "NOT_RUN"
    else "not_run"
)

if yf_status != "healthy":
    failures.append(f"yfinance_status:{yf_status}")

if yf_count != 15:
    failures.append(f"yfinance_coverage:{yf_count}/15")

if yf_age is None or yf_age > 15:
    failures.append(f"yfinance_freshness:{yf_age}")

if massive_status not in {
    "healthy",
    "degraded",
    "not_configured",
}:
    failures.append(
        f"massive_status:{massive_status}"
    )

if massive_status == "not_configured":
    observations.append(
        "massive:waived_not_configured"
    )

if layer_status != "completed":
    failures.append(
        f"provider_layer_status:{layer_status}"
    )

if canonical_modified is not False:
    failures.append(
        "canonical_files_modified_not_false"
    )

if promotion_executed is not False:
    failures.append(
        "promotion_executed_not_false"
    )

before = json.loads(
    before_path.read_text(encoding="utf-8")
)
after = json.loads(
    after_path.read_text(encoding="utf-8")
)

execution_changes = sorted(
    path
    for path in set(before) | set(after)
    if before.get(path) != after.get(path)
)

if execution_changes:
    failures.append(
        "execution_artefacts_modified"
    )

if validation_rc == 0:
    if gate_decision != "PASS":
        failures.append(
            f"validation_rc_0_gate:{gate_decision}"
        )

elif validation_rc == 1:
    if gate_decision == "WARNING":
        observations.append(
            "quality_gate:warning"
        )
    else:
        failures.append(
            f"validation_rc_1_gate:{gate_decision}"
        )

elif validation_rc == 2:
    if gate_decision == "FAIL":
        observations.append(
            "quality_gate:fail_promotion_blocked"
        )
    else:
        failures.append(
            f"validation_rc_2_gate:{gate_decision}"
        )

elif validation_rc == 10:
    if validation_status == "blocked_at_validation":
        observations.append(
            "cross_source_validation:"
            "blocked_promotion_not_run"
        )
    else:
        failures.append(
            f"validation_rc_10_status:{validation_status}"
        )

else:
    failures.append(
        f"unexpected_validation_rc:{validation_rc}"
    )

print(f"YFINANCE_STATUS={yf_status}")
print(f"YFINANCE_COUNT={yf_count}")
print(
    "YFINANCE_AGE_MINUTES="
    + (
        f"{yf_age:.2f}"
        if yf_age is not None
        else "unknown"
    )
)

print(f"MASSIVE_STATUS={massive_status}")
print(f"MASSIVE_COUNT={massive_count}")
print(f"PROVIDER_LAYER_STATUS={layer_status}")
print(f"QUALITY_GATE_STATUS={gate_status}")
print(f"QUALITY_GATE_DECISION={gate_decision}")
print(f"VALIDATION_RETURN_CODE={validation_rc}")

print(
    "CANONICAL_FILES_MODIFIED="
    f"{canonical_modified}"
)

print(
    "PROMOTION_EXECUTED="
    f"{promotion_executed}"
)

print(
    "EXECUTION_ARTEFACT_CHANGES="
    f"{execution_changes}"
)

print(
    "EXECUTION_ISOLATION="
    + ("PASS" if not execution_changes else "FAIL")
)

print(f"OBSERVATIONS={observations}")
print(f"FAILURES={failures}")

if failures:
    print("FINAL_STATUS=FAIL")
    raise SystemExit(1)

print("FINAL_STATUS=PASS_WITH_OBSERVATION")
PY

echo "COMPLETED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
