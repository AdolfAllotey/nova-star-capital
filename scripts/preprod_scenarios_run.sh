#!/usr/bin/env bash
set -euo pipefail

export TZ=UTC

SC_DIR="${1:-scripts/preprod_scenarios}"
OUT_DIR="data/telemetry/preprod_scenarios"
mkdir -p "$OUT_DIR"

ts="$(date -u +%Y%m%d_%H%M%S)"
out_json="$OUT_DIR/preprod_scenarios_${ts}.json"

# NSC_PATCH: overall_ok_from_scenarios BEGIN
# Force overall_ok to be AND of all scenario_ok values (source-of-truth)
if [ -f "$out_json" ]; then
  _all_ok="$(jq -r '[.scenarios[].scenario_ok] | all' "$out_json" 2>/dev/null || echo "false")"
  tmp="${out_json}.tmp"
  jq --argjson v "$_all_ok" '.overall_ok = ($v == true)' "$out_json" > "$tmp" && mv "$tmp" "$out_json"
fi
# NSC_PATCH: overall_ok_from_scenarios END

out_md="$OUT_DIR/preprod_scenarios_${ts}.md"

echo "== PREPROD SCENARIOS RUN =="
echo "scenarios_dir=$SC_DIR"
echo "out_json=$out_json"
echo "out_md=$out_md"

# snapshot immutability sentinel
before_pos="$(sha256sum data/trading/open_positions.json 2>/dev/null | awk '{print $1}' || true)"

# gather scenario files
mapfile -t files < <(ls -1 "$SC_DIR"/*.json 2>/dev/null | sort || true)
if [ "${#files[@]}" -eq 0 ]; then
  echo "ERROR: no scenarios found in $SC_DIR"
  exit 1
fi

results="[]"
overall_ok=true

for f in "${files[@]}"; do
  sid="$(jq -r '.id // empty' "$f")"
  # NSC_PATCH: stress_timeout_flag_v1
  STRESS_WRAP_TIMEOUT="0"
  if [ "${sid:-}" = "30_stress_25" ]; then
    STRESS_WRAP_TIMEOUT="1"
  fi

  # NSC_PATCH: custom_scenarios_overrides_v1 BEGIN
  # Some scenarios need temporary JSON overrides; always restore (defense-in-depth).
  _restore_files=()

  _backup_and_write_json() {
    # $1 = target path, $2 = json content
    local target="$1"
    local content="$2"
    local bak="${target}.bak_scen_$$"
    if [ -f "$target" ]; then
      cp -a "$target" "$bak"
      _restore_files+=("$target::$bak")
    else
      _restore_files+=("$target::__CREATED__")
    fi
    mkdir -p "$(dirname "$target")"
    printf "%s\n" "$content" > "$target"
  }

  _restore_all() {
    local item target bak
    for item in "${_restore_files[@]}"; do
      target="${item%%::*}"
      bak="${item##*::}"
      if [ "$bak" = "__CREATED__" ]; then
        rm -f "$target" 2>/dev/null || true
      else
        mv -f "$bak" "$target" 2>/dev/null || true
      fi
    done
    _restore_files=()
  }

  trap '_restore_all' RETURN

  # Scenario-specific overrides
  if [ "${id:-}" = "40_killswitch_precedence" ]; then
    _backup_and_write_json "data/trading/kill_switch.json" '{"hard_block": true, "reason": "scenario_force_killswitch"}'
  fi

  if [ "${id:-}" = "50_correlation_gate_payload" ]; then
    _backup_and_write_json "data/analysis/correlation_gate_state.json" '{"active": false, "reason": "scenario_payload_sanity"}'
  fi
  # NSC_PATCH: custom_scenarios_overrides_v1 END



  desc="$(jq -r '.desc // ""' "$f")"
  echo
  echo "---- scenario: $sid ----"


  echo "$desc"

  # reset env to a known baseline for each scenario
  unset PREPROD_SIMULATE_ORDERS || true
  export NSC_ENV=PREPROD

# max seconds for each preprod_check during stress scenarios
PREPROD_CHECK_TIMEOUT_S="${PREPROD_CHECK_TIMEOUT_S:-120}"

  # apply env overrides
  while IFS=$'\t' read -r k v; do
    if [ -n "$k" ] && [ "$k" != "null" ]; then
      if [ "$v" = "null" ]; then
        unset "$k" || true
      else
        export "$k=$v"
      fi
    fi
  done < <(jq -r '.env // {} | to_entries[] | "\(.key)\t\(.value)"' "$f")

  # run baseline check
  # NSC_PATCH: wrapped_preprod_check_v1
  if [ "${STRESS_WRAP_TIMEOUT:-0}" = "1" ]; then
    echo "-- stress run ${i:-?}/${runs:-?} (timeout=${PREPROD_CHECK_TIMEOUT_S}s)"
    if ! timeout "${PREPROD_CHECK_TIMEOUT_S}" ./scripts/preprod_check.sh >/dev/null; then
      echo "❌ preprod_check timed out/failed (run=${i:-?}/${runs:-?}, timeout=${PREPROD_CHECK_TIMEOUT_S}s)"
      stress_ok="false"
      break
    fi
  else
    ./scripts/preprod_check.sh >/dev/null
  fi
  ok="$(jq -r '.ok' data/telemetry/preprod_check.json)"
  assertions="$(jq -c '.assertions' data/telemetry/preprod_check.json)"
  details="$(jq -c '.details' data/telemetry/preprod_check.json)"

  # optional stress
  stress_runs="$(jq -r '.stress.runs // 0' "$f")"
  stress_ok="null"
  if [ "$stress_runs" != "0" ]; then
    if ./scripts/preprod_stress_smoke.sh "$stress_runs" >/dev/null; then
      stress_ok="true"
    else
      stress_ok="false"
    fi
  fi

  # scenario expectations (basic)
  expect_ok="$(jq -r '.expect.preprod_check_ok // empty' "$f")"
  scen_ok=true
  if [ -n "$expect_ok" ]; then
    if [ "$expect_ok" = "true" ] && [ "$ok" != "true" ]; then scen_ok=false; fi
    if [ "$expect_ok" = "false" ] && [ "$ok" = "true" ]; then scen_ok=false; fi
  fi

  # price expectation
  expect_price="$(jq -r '.expect.price_fetch_ok // empty' "$f")"
  if [ -n "$expect_price" ]; then
    px_ok="$(jq -r '.assertions.market_price_fetch_ok // empty' data/telemetry/preprod_check.json)"
    if [ "$expect_price" = "true" ] && [ "$px_ok" != "true" ]; then scen_ok=false; fi
  fi

  # stress expectation
  expect_stress="$(jq -r '.expect.stress_ok // empty' "$f")"
  if [ -n "$expect_stress" ]; then
    if [ "$expect_stress" = "true" ] && [ "$stress_ok" != "true" ]; then scen_ok=false; fi
  fi

  # record
  
  # NSC_PATCH: compute_scen_ok_v1 BEGIN
  # scenario_ok = preprod_check_ok AND (stress_ok is true OR null)
  scen_ok=false
  if [ "$ok" = "true" ]; then
    if [ "$stress_ok" = "true" ] || [ "$stress_ok" = "null" ]; then
      scen_ok=true
    fi
  fi
  # NSC_PATCH: compute_scen_ok_v1 END

results="$(jq -c \
    --arg id "$sid" \
    --arg desc "$desc" \
    --arg file "$f" \
    --arg ok "$ok" \
    --argjson assertions "$assertions" \
    --argjson details "$details" \
    --arg stress_ok "$stress_ok" \
    --arg scen_ok "$scen_ok" \
    '. + [{
      "id": $id,
      "desc": $desc,
      "file": $file,
      "preprod_check_ok": ($ok == "true"),
      "scenario_ok": ($scen_ok == "true"),  # NSC_PATCH: scenario_ok_from_scen_ok_v1
      "stress_ok": (if $stress_ok == "null" then null else ($stress_ok == "true") end),
      "assertions": $assertions,
      "details": $details
    }]' <<<"$results")"

  if [ "$scen_ok" != true ]; then
    overall_ok=false
  fi
done

after_pos="$(sha256sum data/trading/open_positions.json 2>/dev/null | awk '{print $1}' || true)"
pos_immutable=true
if [ "$before_pos" != "$after_pos" ]; then
  pos_immutable=false
  overall_ok=false
fi

# write scorecard
jq -n \
  --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson overall_ok "$( [ "$overall_ok" = true ] && echo true || echo false )" \
  --arg before_pos "$before_pos" \
  --arg after_pos "$after_pos" \
  --argjson pos_immutable "$( [ "$pos_immutable" = true ] && echo true || echo false )" \
  --argjson results "$results" \
  '{
    generated_at: $generated_at,
    overall_ok: $overall_ok,
    open_positions_hash_before: $before_pos,
    open_positions_hash_after: $after_pos,
    open_positions_immutable: $pos_immutable,
    scenarios: $results
  }' > "$out_json"

# Markdown summary
{
  echo "# NSC PREPROD SCENARIOS"
  echo
  echo "- generated_at: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
  echo "- overall_ok: \`$overall_ok\`"
  echo "- open_positions_immutable: \`$pos_immutable\`"
  echo
  echo "## Scenarios"
  jq -r '.scenarios[] | "- \(.id): scenario_ok=\(.scenario_ok) preprod_check_ok=\(.preprod_check_ok) stress_ok=\(.stress_ok)"' "$out_json"
} > "$out_md"

echo "✅ wrote $out_json"
echo "✅ wrote $out_md"

  # NSC_PATCH: scenarios_kpis_auto_v1 BEGIN
  python scripts/preprod_scenarios_kpis.py >/dev/null || true
  # NSC_PATCH: scenarios_kpis_auto_v1 END

if [ "$overall_ok" != true ]; then
  echo "❌ scenarios failed"
  exit 1
fi
