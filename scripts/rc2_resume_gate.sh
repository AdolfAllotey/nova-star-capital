#!/usr/bin/env bash
set -euo pipefail

APP="/opt/nsc/app"

cd "$APP"

FAILURES=0

pass() {
    echo "PASS | $*"
}

fail() {
    echo "FAIL | $*"
    FAILURES=$((FAILURES + 1))
}

echo "============================================================"
echo " NOVA STAR CAPITAL — RC2 OPERATIONAL RESUME GATE"
echo " READ ONLY / FAIL CLOSED"
echo "============================================================"

echo
echo "===== 1. REPOSITORY ====="

BRANCH="$(git branch --show-current)"
HEAD="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/preprod 2>/dev/null || true)"
DIRTY="$(git diff --name-only | wc -l)"
STAGED="$(git diff --cached --name-only | wc -l)"

echo "BRANCH=$BRANCH"
echo "HEAD=$HEAD"
echo "REMOTE=$REMOTE"
echo "DIRTY=$DIRTY"
echo "STAGED=$STAGED"

if [[ "$BRANCH" == "preprod" ]]; then
    pass "BRANCH=preprod"
else
    fail "BRANCH=$BRANCH"
fi

if [[ -n "$REMOTE" && "$HEAD" == "$REMOTE" ]]; then
    pass "HEAD_MATCHES_ORIGIN_PREPROD"
else
    fail "HEAD_REMOTE_MISMATCH"
fi

if [[ "$DIRTY" -eq 0 && "$STAGED" -eq 0 ]]; then
    pass "REPOSITORY_CLEAN"
else
    fail "REPOSITORY_NOT_CLEAN"
fi


echo
echo "===== 2. FAILED NSC UNITS ====="

FAILED_NSC="$(
    systemctl --failed \
        --no-legend \
        --plain \
        2>/dev/null \
        | awk '$1 ~ /^nsc-/ {print}'
)"

if [[ -z "$FAILED_NSC" ]]; then
    echo "FAILED_NSC_COUNT=0"
    pass "SERVICE_FAILURE_SCAN"
else
    echo "$FAILED_NSC"

    FAILED_COUNT="$(
        printf '%s\n' "$FAILED_NSC" \
            | sed '/^[[:space:]]*$/d' \
            | wc -l
    )"

    echo "FAILED_NSC_COUNT=$FAILED_COUNT"
    fail "SERVICE_FAILURE_SCAN"
fi


echo
echo "===== 3. CRITICAL TIMERS ====="

TIMERS=(
    nsc-kernel.timer
    nsc-global-preprod-cycle.timer
    nsc-options-v3-shadow.timer
    nsc-global-preprod-long-run-daily-check.timer
    nsc-preprod-health-report.timer
    nsc-defensive-preprod.timer
    nsc-precious-metals-preprod.timer
)

for unit in "${TIMERS[@]}"; do
    LOAD="$(
        systemctl show "$unit" \
            -p LoadState \
            --value \
            2>/dev/null \
            || true
    )"

    ACTIVE="$(
        systemctl show "$unit" \
            -p ActiveState \
            --value \
            2>/dev/null \
            || true
    )"

    SUB="$(
        systemctl show "$unit" \
            -p SubState \
            --value \
            2>/dev/null \
            || true
    )"

    ENABLED="$(
        systemctl show "$unit" \
            -p UnitFileState \
            --value \
            2>/dev/null \
            || true
    )"

    echo \
        "$unit | load=$LOAD | active=$ACTIVE | sub=$SUB | enabled=$ENABLED"

    if [[ "$LOAD" == "loaded" \
        && "$ACTIVE" == "active" \
        && "$SUB" == "waiting" \
        && "$ENABLED" == "enabled" ]]
    then
        pass "$unit"
    else
        fail "$unit"
    fi
done


echo
echo "===== 4. CRITICAL SERVICE LAST RESULTS ====="

SERVICES=(
    nsc-kernel.service
    nsc-preprod-pipeline.service
    nsc-defensive-preprod.service
    nsc-precious-metals-preprod.service
    nsc-options-v3-shadow.service
)

for unit in "${SERVICES[@]}"; do
    LOAD="$(
        systemctl show "$unit" \
            -p LoadState \
            --value \
            2>/dev/null \
            || true
    )"

    RESULT="$(
        systemctl show "$unit" \
            -p Result \
            --value \
            2>/dev/null \
            || true
    )"

    STATUS="$(
        systemctl show "$unit" \
            -p ExecMainStatus \
            --value \
            2>/dev/null \
            || true
    )"

    ACTIVE="$(
        systemctl show "$unit" \
            -p ActiveState \
            --value \
            2>/dev/null \
            || true
    )"

    SUB="$(
        systemctl show "$unit" \
            -p SubState \
            --value \
            2>/dev/null \
            || true
    )"

    echo \
        "$unit | load=$LOAD | result=$RESULT | status=$STATUS | active=$ACTIVE | sub=$SUB"

    if [[ "$LOAD" == "loaded" \
        && "$RESULT" == "success" \
        && "$STATUS" == "0" ]]
    then
        pass "$unit"
    else
        fail "$unit"
    fi
done


echo
echo "===== 5. GLOBAL PIPELINE INTERPRETER ====="

EXECSTART="$(
    systemctl show \
        nsc-preprod-pipeline.service \
        -p ExecStart \
        --value \
        2>/dev/null \
        || true
)"

echo "EFFECTIVE_EXECSTART=$EXECSTART"

if [[ "$EXECSTART" == *"/opt/nsc/.venv/bin/python"* \
    && "$EXECSTART" == *"/opt/nsc/app/src/v2/run_pipeline_wrapped.py"* ]]
then
    pass "GLOBAL_PIPELINE_INTERPRETER"
else
    fail "GLOBAL_PIPELINE_INTERPRETER"
fi


echo
echo "===== 6. FINAL VERDICT ====="

echo "FAILURES=$FAILURES"

if [[ "$FAILURES" -eq 0 ]]; then
    echo "RC2_OPERATIONAL_RESUME_GATE=PASS"
    echo "============================================================"
    exit 0
fi

echo "RC2_OPERATIONAL_RESUME_GATE=FAIL"
echo "============================================================"
exit 1
