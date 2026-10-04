#!/usr/bin/env bash
set -euo pipefail
cd /opt/nsc/app

export NSC_ENV=PREPROD
export NSC_EQU_ACTION_POLICY=SIMULATED_EXECUTION

CANONICAL_LOCK="/run/lock/nsc-equities-offensive-canonical.lock"

exec 8>"$CANONICAL_LOCK"

echo "CANONICAL_LOCK=WAIT_SHARED"

flock -s 8

echo "CANONICAL_LOCK=ACQUIRED_SHARED"

echo "CANONICAL_READER_GUARD=START"

/opt/nsc/.venv/bin/python \
  src/v2/equities_offensive/market/canonical_reader_guard.py

echo "CANONICAL_READER_GUARD=PASS"

echo "CANONICAL_V2_RUNTIME_GATE=START"

/opt/nsc/.venv/bin/python - <<'PY_GATE'
import json
import os
import re
from pathlib import Path

root = (
    Path(os.environ["NSC_DATA_DIR"]).resolve()
    / "equities_offensive"
)

paths = {
    "prices": root / "market/prices.json",
    "snapshot": (
        root / "universe/price_snapshot.json"
    ),
    "core": (
        root / "universe/universe_filtered.json"
    ),
    "tactical": (
        root / "universe/tactical_watchlist.json"
    ),
}

docs = {}

for name, path in paths.items():
    docs[name] = json.loads(
        path.read_text(encoding="utf-8")
    )

prices = docs["prices"]
snapshot = docs["snapshot"]
core = docs["core"]
tactical = docs["tactical"]

errors = []

expected_engines = {
    "prices": (
        "offensive_canonical_market_feed_v2"
    ),
    "snapshot": (
        "offensive_canonical_snapshot_v2"
    ),
    "core": (
        "offensive_dual_universe_builder_v2"
    ),
    "tactical": (
        "offensive_dual_universe_builder_v2"
    ),
}

for name, expected in expected_engines.items():
    if docs[name].get("engine") != expected:
        errors.append(
            f"{name}_engine_not_v2"
        )

if prices.get("canonical") is not True:
    errors.append("prices_not_canonical")

if snapshot.get("canonical") is not True:
    errors.append("snapshot_not_canonical")

if core.get("universe") != "nasdaq_offensive_core":
    errors.append("core_universe_invalid")

if (
    tactical.get("universe")
    != "nasdaq_offensive_tactical"
):
    errors.append("tactical_universe_invalid")

expected_universe_authority = {
    "core": {
        "status": "active_simulated",
        "universe_role": "core",
    },
    "tactical": {
        "status": "watch_only",
        "universe_role": (
            "tactical_high_volatility"
        ),
    },
}

for name, authority in (
    expected_universe_authority.items()
):
    doc = docs[name]

    if (
        doc.get("status")
        != authority["status"]
    ):
        errors.append(
            f"{name}_status_invalid"
        )

    if (
        doc.get("universe_role")
        != authority["universe_role"]
    ):
        errors.append(
            f"{name}_role_invalid"
        )

    policy = doc.get(
        "execution_policy"
    )

    if not isinstance(
        policy,
        dict,
    ):
        errors.append(
            f"{name}_execution_policy_missing"
        )
        policy = {}

    if (
        policy.get("shadow_only")
        is not False
    ):
        errors.append(
            f"{name}_shadow_only_not_false"
        )

    if (
        policy.get(
            "direct_execution_allowed"
        )
        is not False
    ):
        errors.append(
            f"{name}_direct_execution_not_false"
        )

tactical_policy = tactical.get(
    "execution_policy"
)

if not isinstance(
    tactical_policy,
    dict,
):
    tactical_policy = {}

for control in (
    "requires_tactical_risk_engine",
    "reduced_sizing_required",
    "sector_concentration_control_required",
    "enhanced_exit_protection_required",
):
    if (
        tactical_policy.get(control)
        is not True
    ):
        errors.append(
            "tactical_control_invalid:"
            + control
        )

expected_pending_limits = {
    "max_tactical_positions": None,
    "max_tactical_weight": None,
    "position_size_factor": None,
}

if (
    tactical.get("risk_limits_pending")
    != expected_pending_limits
):
    errors.append(
        "tactical_risk_limits_contract_invalid"
    )

generation_re = re.compile(
    r"^[0-9a-f]{64}$"
)

for name in (
    "prices",
    "snapshot",
    "core",
    "tactical",
):
    generation = docs[name].get(
        "generation_id"
    )

    if not isinstance(generation, str):
        errors.append(
            f"{name}_generation_id_missing"
        )
    elif generation_re.fullmatch(
        generation
    ) is None:
        errors.append(
            f"{name}_generation_id_invalid"
        )

if (
    isinstance(
        prices.get("generation_id"),
        str,
    )
    and isinstance(
        snapshot.get("generation_id"),
        str,
    )
    and prices.get("generation_id")
    != snapshot.get("generation_id")
):
    errors.append(
        "market_generation_id_mismatch"
    )

if (
    isinstance(
        core.get("generation_id"),
        str,
    )
    and isinstance(
        tactical.get("generation_id"),
        str,
    )
    and core.get("generation_id")
    != tactical.get("generation_id")
):
    errors.append(
        "universe_generation_id_mismatch"
    )

sessions = {}

for name in (
    "prices",
    "snapshot",
    "core",
    "tactical",
):
    session = docs[name].get(
        "market_session"
    )

    if (
        not isinstance(session, str)
        or not session
    ):
        errors.append(
            f"{name}_market_session_missing"
        )
    else:
        sessions[name] = session

if len(set(sessions.values())) > 1:
    errors.append(
        "cutover_market_session_mismatch"
    )

if errors:
    print(
        "CANONICAL_V2_RUNTIME_GATE=BLOCKED",
        ",".join(errors),
    )
    raise SystemExit(42)

print("CANONICAL_V2_RUNTIME_GATE=PASS")
print(
    "MARKET_GENERATION_ID=",
    prices.get("generation_id"),
)
print(
    "UNIVERSE_GENERATION_ID=",
    core.get("generation_id"),
)
print(
    "MARKET_SESSION=",
    prices.get("market_session"),
)
PY_GATE

echo "CANONICAL_V2_RUNTIME_GATE=PASS"

echo "== NSC EQUITIES OFFENSIVE PIPELINE =="
/opt/nsc/.venv/bin/python src/v2/equities_offensive/run_equities_pipeline.py

echo "✅ DONE: equities_offensive pipeline OK"
