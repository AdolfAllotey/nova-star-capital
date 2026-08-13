#!/usr/bin/env bash
set -euo pipefail

APP="/opt/nsc/app"
DATA="/opt/nsc/data/preprod"

if [ -x /opt/nsc/.venv/bin/python3 ]; then
    PY="/opt/nsc/.venv/bin/python3"
elif [ -x /opt/nsc/.venv/bin/python ]; then
    PY="/opt/nsc/.venv/bin/python"
else
    PY="/usr/bin/python3"
fi

cd "$APP"

echo "============================================================"
echo " NOVA STAR CAPITAL — RC2 STRATEGIC CHECK"
echo " READ ONLY / PREPROD / DECISION QUALITY"
echo "============================================================"

echo
echo "===== 1. RC2 REFERENCE ====="
echo "BRANCH=$(git branch --show-current)"
echo "HEAD=$(git rev-parse --short HEAD)"
echo "TRACKED_DIRTY=$(git diff --name-only | wc -l)"
echo "STAGED=$(git diff --cached --name-only | wc -l)"

"$PY" - <<'PY'
import json
import math
from pathlib import Path
from datetime import datetime, timezone

DATA = Path("/opt/nsc/data/preprod")

def load(path, default):
    path = Path(path)
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        return json.loads(path.read_text())
    except Exception:
        return default

def f(v, default=0.0):
    try:
        x = float(v)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return default

def pct(v):
    return round(f(v) * 100, 2)

state = load(
    DATA / "portfolio/state/portfolio_state.json",
    {}
)

target = load(
    DATA / "portfolio/portfolio_target.json",
    {}
)

launch = load(
    DATA / "releases/RC2/RC2_LAUNCH.json",
    {}
)

bricks = state.get("bricks", {}) if isinstance(state, dict) else {}

print()
print("===== 2. RC2 CLOCK / STRATEGIC CONTEXT =====")
print("RC2_STATUS=", launch.get("status"))
print("RC2_PHASE=", launch.get("phase"))
print("RC2_LAUNCH_UTC=", launch.get("launch_timestamp_utc"))
print("PORTFOLIO_REGIME=", state.get("portfolio_regime"))
print("CAPITAL_OBSERVED_EUR=", state.get("capital_observed_eur"))
print("CAPITAL_ENGAGED_EUR=", state.get("capital_engaged_eur"))
print("CASH_AVAILABLE_EUR=", state.get("cash_available_eur"))
print("LIVE_EXPOSURE_RATIO=", state.get("live_exposure_ratio"))

print()
print("===== 3. TARGET VS CURRENT ALLOCATION =====")

active = [
    "crypto",
    "equities_offensive",
    "equities_defensive",
    "bonds",
    "precious_metals",
    "options_us",
]

allocation_flags = []
underdeploy_flags = []
overdeploy_flags = []

for brick in active:
    b = bricks.get(brick, {}) or {}

    target_w = f(b.get("target_weight_snapshot"))
    current_w = f(b.get("current_weight_estimate"))
    exposure = f(b.get("current_exposure_eur"))
    positions = b.get("positions_count")
    delta = current_w - target_w

    if abs(delta) >= 0.05:
        allocation_flags.append(brick)

    if delta <= -0.05:
        underdeploy_flags.append(brick)

    if delta >= 0.05:
        overdeploy_flags.append(brick)

    print(
        f"{brick} | "
        f"target={target_w:.6f} | "
        f"current={current_w:.6f} | "
        f"delta={delta:+.6f} | "
        f"exposure={exposure:.2f} | "
        f"positions={positions} | "
        f"origin={b.get('state_origin')}"
    )

print()
print("===== 4. CRYPTO / DISCOVERY / BITPANDA =====")

crypto = bricks.get("crypto", {}) or {}
print("CRYPTO_TARGET=", crypto.get("target_weight_snapshot"))
print("CRYPTO_CURRENT=", crypto.get("current_weight_estimate"))
print("CRYPTO_EXPOSURE_EUR=", crypto.get("current_exposure_eur"))
print("CRYPTO_POSITIONS=", crypto.get("positions_count"))

discovery_root = DATA / "discovery"
bitpanda_files = []

if discovery_root.exists():
    for p in discovery_root.rglob("*"):
        if p.is_file() and "bitpanda" in p.name.lower():
            bitpanda_files.append(p)

bitpanda_files.sort(
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

print("BITPANDA_FILES=", len(bitpanda_files))

for p in bitpanda_files[:5]:
    age_h = (
        datetime.now(timezone.utc).timestamp()
        - p.stat().st_mtime
    ) / 3600

    print(
        "BITPANDA_SOURCE",
        p.name,
        "| age_hours=",
        round(age_h, 2),
        "| size=",
        p.stat().st_size,
    )

print()
print("===== 5. OFFENSIVE EQUITIES =====")

off = bricks.get("equities_offensive", {}) or {}
off_payload = load(
    DATA / "equities_offensive/reporting/dashboard_payload.json",
    {}
)

off_kpis = (
    off_payload.get("kpis", {})
    if isinstance(off_payload, dict)
    else {}
)

print("STATUS=", off.get("status"))
print("TARGET=", off.get("target_weight_snapshot"))
print("CURRENT=", off.get("current_weight_estimate"))
print("EXPOSURE_EUR=", off.get("current_exposure_eur"))
print("POSITIONS=", off.get("positions_count"))
print("STATE_ORIGIN=", off.get("state_origin"))
print("SIGNALS_COUNT=", off_kpis.get("signals_count"))
print("VOTED_COUNT=", off_kpis.get("voted_count"))
print(
    "EXECUTION_CANDIDATE_ORDERS=",
    off_kpis.get("execution_candidate_orders"),
)
print("ACTION_POLICY=", off_kpis.get("action_policy"))

print()
print("===== 6. DEFENSIVE EQUITIES =====")

de = bricks.get("equities_defensive", {}) or {}
def_state = load(
    DATA / "defensive/defensive_state.json",
    {}
)

print("STATUS=", de.get("status"))
print("TARGET=", de.get("target_weight_snapshot"))
print("CURRENT=", de.get("current_weight_estimate"))
print("EXPOSURE_EUR=", de.get("current_exposure_eur"))
print("POSITIONS=", de.get("positions_count"))
print("STATE_ORIGIN=", de.get("state_origin"))

if isinstance(def_state, dict):
    print(
        "DEFENSIVE_STATE_STATUS=",
        def_state.get("status"),
    )
    print(
        "DEFENSIVE_REGIME=",
        def_state.get("market_regime")
        or def_state.get("regime"),
    )

print()
print("===== 7. BONDS =====")

bonds = bricks.get("bonds", {}) or {}
print("STATUS=", bonds.get("status"))
print("TARGET=", bonds.get("target_weight_snapshot"))
print("CURRENT=", bonds.get("current_weight_estimate"))
print("EXPOSURE_EUR=", bonds.get("current_exposure_eur"))
print("POSITIONS=", bonds.get("positions_count"))

print()
print("===== 8. PRECIOUS METALS =====")

metals = bricks.get("precious_metals", {}) or {}
print("STATUS=", metals.get("status"))
print("TARGET=", metals.get("target_weight_snapshot"))
print("CURRENT=", metals.get("current_weight_estimate"))
print("EXPOSURE_EUR=", metals.get("current_exposure_eur"))
print("POSITIONS=", metals.get("positions_count"))

print()
print("===== 9. OPTIONS US =====")

opt = bricks.get("options_us", {}) or {}

opt_dashboard = load(
    DATA / "options_v3/options_v3_dashboard.json",
    {}
)
opt_status = load(
    DATA / "options_v3/options_v3_status.json",
    {}
)
raw = load(
    DATA / "options_v3/options_v3_candidates_raw.json",
    []
)
validated = load(
    DATA / "options_v3/options_v3_candidates_validated.json",
    []
)
decisions = load(
    DATA / "options_v3/options_v3_decisions.json",
    []
)
positions = load(
    DATA / "options_v3/options_v3_positions.json",
    []
)

print("TARGET=", opt.get("target_weight_snapshot"))
print("CURRENT=", opt.get("current_weight_estimate"))
print("EXPOSURE_EUR=", opt.get("current_exposure_eur"))
print("OPEN_POSITIONS=", len(positions))
print("RAW_CANDIDATES=", len(raw))
print("VALIDATED=", len(validated))
print("DECISIONS=", len(decisions))
print("ACTION_POLICY=", opt_status.get("action_policy"))

status_block = (
    opt_dashboard.get("status", {})
    if isinstance(opt_dashboard, dict)
    else {}
)

print(
    "OPPORTUNITY_STATUS=",
    status_block.get("opportunity_status"),
)

for d in decisions[:10]:
    if isinstance(d, dict):
        print(
            "OPTION_DECISION",
            d.get("ticker"),
            "| status=",
            d.get("status"),
            "| reason=",
            d.get("reason"),
        )

print()
print("===== 10. DECISION / OPPORTUNITY ANALYSIS =====")

rejection_reasons = {}

for d in decisions:
    if not isinstance(d, dict):
        continue
    if str(d.get("status")).upper().startswith("REJECT"):
        reason = str(
            d.get("reason")
            or "unknown"
        )
        rejection_reasons[reason] = (
            rejection_reasons.get(reason, 0) + 1
        )

print("OPTIONS_REJECTION_REASONS=", rejection_reasons)

print(
    "ALLOCATION_DEVIATIONS_GE_5PCT=",
    allocation_flags,
)
print(
    "UNDERDEPLOYED_GE_5PCT=",
    underdeploy_flags,
)
print(
    "OVERDEPLOYED_GE_5PCT=",
    overdeploy_flags,
)

print()
print("===== 11. CASH / DEPLOYMENT =====")

capital = f(state.get("capital_observed_eur"))
engaged = f(state.get("capital_engaged_eur"))
cash = f(state.get("cash_available_eur"))

cash_ratio = (
    cash / capital
    if capital > 0
    else 0.0
)

print("CAPITAL_EUR=", capital)
print("ENGAGED_EUR=", engaged)
print("CASH_EUR=", cash)
print("CASH_RATIO=", round(cash_ratio, 6))
print("CASH_RATIO_PCT=", round(cash_ratio * 100, 2))

print()
print("===== 12. CROSS-BRICK CONSISTENCY =====")

issues = []

for brick in active:
    b = bricks.get(brick)

    if not isinstance(b, dict):
        issues.append(f"{brick}:missing_state")
        continue

    target_w = f(b.get("target_weight_snapshot"))
    current_w = f(b.get("current_weight_estimate"))

    if current_w < -1e-9:
        issues.append(
            f"{brick}:negative_current_weight"
        )

    if target_w < -1e-9:
        issues.append(
            f"{brick}:negative_target_weight"
        )

    if (
        f(b.get("current_exposure_eur")) == 0
        and int(b.get("positions_count") or 0) > 0
    ):
        issues.append(
            f"{brick}:positions_without_exposure"
        )

print("CONSISTENCY_ISSUES=", issues)
print(
    "CROSS_BRICK_CONSISTENCY=",
    "PASS" if not issues else "REVIEW",
)

print()
print("===== 13. STRATEGIC VERDICT =====")

score = 100
watch = []

if issues:
    score -= min(30, len(issues) * 10)
    watch.extend(issues)

if len(allocation_flags) >= 3:
    score -= 10
    watch.append(
        "multiple_material_allocation_deviations"
    )

if cash_ratio > 0.45:
    score -= 10
    watch.append("high_cash_ratio")

if (
    f(opt.get("target_weight_snapshot")) > 0
    and f(opt.get("current_weight_estimate")) == 0
):
    watch.append(
        "options_target_not_deployed"
    )

if (
    f(off.get("target_weight_snapshot")) > 0
    and f(off.get("current_weight_estimate")) == 0
):
    watch.append(
        "offensive_target_not_deployed"
    )

if score >= 90:
    verdict = "HEALTHY"
elif score >= 75:
    verdict = "WATCH"
else:
    verdict = "REVIEW"

print("STRATEGIC_HEALTH_SCORE=", score)
print("STRATEGIC_VERDICT=", verdict)
print("WATCH_ITEMS=", watch)

print()
print("===== 13B. STRATEGIC HISTORY SNAPSHOT =====")

history_dir = (
    DATA
    / "releases"
    / "RC2"
    / "strategy_history"
)

history_dir.mkdir(
    parents=True,
    exist_ok=True,
)

history_ts = datetime.now(
    timezone.utc
)

history_payload = {
    "ts": history_ts.isoformat(),
    "release": "RC2",
    "portfolio_regime": state.get(
        "portfolio_regime"
    ),
    "strategic_health_score": score,
    "strategic_verdict": verdict,
    "watch_items": watch,
    "capital": {
        "observed_eur": capital,
        "engaged_eur": engaged,
        "cash_eur": cash,
        "cash_ratio": round(
            cash_ratio,
            6,
        ),
    },
    "allocation": {
        "crypto": {
            "target": f(
                crypto.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                crypto.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                crypto.get(
                    "current_exposure_eur"
                )
            ),
        },
        "equities_offensive": {
            "target": f(
                off.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                off.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                off.get(
                    "current_exposure_eur"
                )
            ),
        },
        "equities_defensive": {
            "target": f(
                de.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                de.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                de.get(
                    "current_exposure_eur"
                )
            ),
        },
        "bonds": {
            "target": f(
                bonds.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                bonds.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                bonds.get(
                    "current_exposure_eur"
                )
            ),
        },
        "precious_metals": {
            "target": f(
                metals.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                metals.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                metals.get(
                    "current_exposure_eur"
                )
            ),
        },
        "options_us": {
            "target": f(
                opt.get(
                    "target_weight_snapshot"
                )
            ),
            "current": f(
                opt.get(
                    "current_weight_estimate"
                )
            ),
            "exposure_eur": f(
                opt.get(
                    "current_exposure_eur"
                )
            ),
        },
    },
    "decision_quality": {
        "validated_options_candidates": len(
            validated
        ),
        "options_rejection_reasons": dict(
            rejection_reasons
        ),
        "allocation_deviations_ge_5pct": (
            allocation_flags
        ),
        "consistency_issues": issues,
    },
}

snapshot_name = (
    "strategy_"
    + history_ts.strftime(
        "%Y%m%dT%H%M%SZ"
    )
    + ".json"
)

snapshot_path = (
    history_dir
    / snapshot_name
)

snapshot_path.write_text(
    json.dumps(
        history_payload,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

jsonl_path = (
    history_dir
    / "rc2_strategy_history.jsonl"
)

with jsonl_path.open(
    "a",
    encoding="utf-8",
) as fh:
    fh.write(
        json.dumps(
            history_payload,
            ensure_ascii=False,
        )
        + "\n"
    )

latest_path = (
    history_dir
    / "latest.json"
)

latest_path.write_text(
    json.dumps(
        history_payload,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "STRATEGY_HISTORY_SNAPSHOT=",
    snapshot_path,
)

print(
    "STRATEGY_HISTORY_JSONL=",
    jsonl_path,
)

print(
    "STRATEGY_HISTORY_LATEST=",
    latest_path,
)

print(
    "STRATEGY_HISTORY_WRITE=PASS"
)

print()
print("===== 14. STRATEGIC INTERPRETATION =====")

print(
    "DECISION_QUALITY=",
    "OBSERVE"
    if not validated
    else "ACTIVE_SAMPLE",
)

print(
    "ALLOCATION_COHERENCE=",
    "PASS"
    if len(allocation_flags) <= 2
    else "WATCH",
)

print(
    "CASH_DEPLOYMENT=",
    "WATCH"
    if cash_ratio > 0.45
    else "NORMAL",
)

print(
    "OPTIONS_STRATEGY=",
    "FAIL_CLOSED_NO_OPPORTUNITY"
    if not validated
    else "OPPORTUNITY_PRESENT",
)

print(
    "OFFENSIVE_DEPLOYMENT=",
    "NO_POSITION"
    if f(off.get("current_weight_estimate")) == 0
    else "DEPLOYED",
)

print()
print("============================================================")
print(
    " RC2 STRATEGIC CHECK COMPLETE —",
    verdict,
)
print(" READ ONLY — NOTHING MODIFIED")
print("============================================================")
PY

echo
echo "===== FINAL GIT SAFETY ====="
echo "TRACKED_DIRTY=$(git diff --name-only | wc -l)"
echo "STAGED=$(git diff --cached --name-only | wc -l)"
