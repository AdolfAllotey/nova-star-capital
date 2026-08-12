import json
import os
from datetime import datetime
from pathlib import Path

from src.v2.portfolio.load_portfolio_inputs import load_portfolio_inputs


DEFAULT_DATA_DIR = "/opt/nsc/data/preprod"
DATA_DIR = Path(os.getenv("NSC_DATA_DIR", DEFAULT_DATA_DIR))
PORTFOLIO_DIR = DATA_DIR / "portfolio"

INPUT_DIR = "/opt/nsc/data/preprod/portfolio/inputs"
TARGET_PATH = PORTFOLIO_DIR / "portfolio_target.json"
OUTPUT_PATH = PORTFOLIO_DIR / "state" / "portfolio_state.json"
LT_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio_valuation.json")
CAPITAL_STATE_PATH = DATA_DIR / "portfolio" / "capital_state.json"


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def save_json(data, path: Path):
    data["timestamp"] = datetime.utcnow().isoformat()
    ensure_parent(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def get_real_brick_state(brick: str, deployable_capital_eur: float):
    state_paths = {
        "equities_defensive": DATA_DIR / "defensive" / "defensive_state.json",
        "bonds": DATA_DIR / "bonds" / "bond_state.json",
        "precious_metals": DATA_DIR / "metals" / "metals_state.json",
    }

    if brick in state_paths:
        state = load_json(state_paths[brick], default={}) or {}
        exposure = float(state.get("current_exposure_eur", 0.0) or 0.0)
        if exposure > 0 and deployable_capital_eur > 0:
            return {
                "current_exposure_eur": round(exposure, 2),
                "current_weight_estimate": round(exposure / deployable_capital_eur, 6),
                "state_origin": "brick_state",
                "positions_count": len(state.get("positions") or []),
                "state_source": str(state_paths[brick]),
            }

    if brick == "equities_offensive":
        path = DATA_DIR / "equities_offensive" / "state" / "exposure_snapshot.json"
        state = load_json(path, default={}) or {}

        # RC2 runtime-state contract:
        # a valid zero-position snapshot is a real runtime state and must
        # never fall back to a signal-derived target allocation.
        if (
            isinstance(state, dict)
            and "total_notional_usd" in state
            and "open_positions" in state
            and deployable_capital_eur > 0
        ):
            exposure = float(
                state.get("total_notional_usd", 0.0) or 0.0
            )
            open_count = int(
                state.get(
                    "open_positions",
                    len(state.get("positions") or []),
                )
                or 0
            )

            return {
                "current_exposure_eur": round(exposure, 2),
                "current_weight_estimate": round(
                    exposure / deployable_capital_eur,
                    6,
                ),
                "state_origin": "brick_state_simulated",
                "positions_count": open_count,
                "state_source": str(path),
            }

    if brick == "crypto":
        path = DATA_DIR / "trading" / "open_positions.json"
        positions = load_json(path, default=[]) or []
        exposure = 0.0
        open_count = 0

        if isinstance(positions, list):
            for pos in positions:
                if not isinstance(pos, dict):
                    continue

                remaining = float(pos.get("remaining_size", pos.get("size", 0.0)) or 0.0)
                is_closed = pos.get("closed") is True or remaining <= 0

                if is_closed:
                    continue

                notional = float(pos.get("notional_eur", 0.0) or 0.0)
                exposure += notional
                open_count += 1

        # If open_positions.json exists and is readable, it is the runtime source of truth.
        # Even with zero active positions, do NOT fallback to signal-derived target weight.
        if deployable_capital_eur > 0:
            return {
                "current_exposure_eur": round(exposure, 2),
                "current_weight_estimate": round(exposure / deployable_capital_eur, 6),
                "state_origin": "open_positions_simulated_open_only",
                "positions_count": open_count,
                "state_source": str(path),
            }

    if brick == "options_us":
        dashboard_path = (
            DATA_DIR / "options_v3" / "options_v3_dashboard.json"
        )
        positions_path = (
            DATA_DIR / "options_v3" / "options_v3_positions.json"
        )
        pockets_path = (
            DATA_DIR / "portfolio" / "pockets.json"
        )

        dashboard = load_json(dashboard_path, default={}) or {}
        positions = load_json(positions_path, default=[]) or []
        pockets_doc = load_json(pockets_path, default={}) or {}

        if not isinstance(dashboard, dict):
            dashboard = {}

        if not isinstance(positions, list):
            positions = []

        pockets = (
            pockets_doc.get("pockets", {})
            if isinstance(pockets_doc, dict)
            else {}
        )
        options_pocket = (
            pockets.get("options_us", {})
            if isinstance(pockets, dict)
            else {}
        )

        pocket_budget_eur = float(
            options_pocket.get("budget_eur", 0.0) or 0.0
        )

        dashboard_portfolio = (
            dashboard.get("portfolio", {})
            if isinstance(dashboard.get("portfolio"), dict)
            else {}
        )

        positions_summary = (
            dashboard.get("positions", {})
            if isinstance(dashboard.get("positions"), dict)
            else {}
        )

        open_count = int(
            positions_summary.get("open", len(positions)) or 0
        )

        internal_used_risk_eur = float(
            dashboard_portfolio.get("used_risk_eur", 0.0)
            or 0.0
        )
        internal_used_risk_pct = float(
            dashboard_portfolio.get("used_risk_pct", 0.0)
            or 0.0
        )
        internal_max_total_risk_eur = float(
            dashboard_portfolio.get(
                "max_total_risk_eur",
                0.0,
            )
            or 0.0
        )
        internal_max_trade_risk_eur = float(
            dashboard_portfolio.get(
                "max_trade_risk_eur",
                0.0,
            )
            or 0.0
        )

        current_exposure_eur = (
            internal_used_risk_eur
            if open_count > 0
            else 0.0
        )

        current_weight = (
            current_exposure_eur / deployable_capital_eur
            if deployable_capital_eur > 0
            else 0.0
        )

        return {
            "current_exposure_eur": round(
                current_exposure_eur,
                2,
            ),
            "current_weight_estimate": round(
                current_weight,
                6,
            ),
            "state_origin": (
                "options_us_open_positions_runtime"
            ),
            "positions_count": open_count,
            "state_source": str(dashboard_path),
            "pocket_source": str(pockets_path),
            "internal_used_risk_eur": round(
                internal_used_risk_eur,
                2,
            ),
            "internal_used_risk_pct": round(
                internal_used_risk_pct,
                6,
            ),
            "internal_max_total_risk_eur": round(
                internal_max_total_risk_eur,
                2,
            ),
            "internal_max_trade_risk_eur": round(
                internal_max_trade_risk_eur,
                2,
            ),
            "internal_available_risk_eur": round(
                max(
                    0.0,
                    internal_max_total_risk_eur
                    - internal_used_risk_eur,
                ),
                2,
            ),
        }

    if brick == "options_v2_shadow":
        v2_dashboard_path = Path(
            "/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json"
        )

        v2_dashboard = load_json(v2_dashboard_path, default={}) or {}
        v2_kpis = (
            v2_dashboard.get("kpis", {})
            if isinstance(v2_dashboard, dict)
            else {}
        )
        v2_open_count = int(v2_kpis.get("positions_open", 0) or 0)

        # Shadow positions are observed but never counted as deployable exposure.
        return {
            "current_exposure_eur": 0.0,
            "current_weight_estimate": 0.0,
            "state_origin": "options_v2_shadow_dashboard",
            "positions_count": v2_open_count,
            "state_source": str(v2_dashboard_path),
        }

    if brick == "options_v3_shadow":
        v3_dashboard_path = (
            DATA_DIR / "options_v3" / "options_v3_dashboard.json"
        )
        v3_positions_path = (
            DATA_DIR / "options_v3" / "options_v3_positions.json"
        )

        v3_dashboard = load_json(v3_dashboard_path, default={}) or {}
        v3_positions = load_json(v3_positions_path, default=[]) or []

        v3_positions_summary = (
            v3_dashboard.get("positions", {})
            if isinstance(v3_dashboard, dict)
            else {}
        )

        if not isinstance(v3_positions_summary, dict):
            v3_positions_summary = {}

        if not isinstance(v3_positions, list):
            v3_positions = []

        v3_open_count = int(
            v3_positions_summary.get("open", len(v3_positions)) or 0
        )

        # V3 remains a strictly observational Shadow overlay during RC2.
        # Its simulated risk must not become portfolio capital exposure.
        return {
            "current_exposure_eur": 0.0,
            "current_weight_estimate": 0.0,
            "state_origin": "options_v3_shadow_dashboard",
            "positions_count": v3_open_count,
            "state_source": str(v3_dashboard_path),
        }

    return None


def run_portfolio_state_builder():
    payloads = load_portfolio_inputs(INPUT_DIR)
    enabled_payloads = [p for p in payloads if p.get("enabled", False)]

    target_data = load_json(TARGET_PATH, default={}) or {}
    final_brick_weights = target_data.get("final_brick_weights", {}) or {}

    excluded_inputs = {
        row.get("brick"): row.get("reason")
        for row in target_data.get("inputs_excluded", [])
        if isinstance(row, dict) and row.get("brick")
    }

    lt_data = load_json(LT_PATH, default=None)
    capital_state = load_json(CAPITAL_STATE_PATH, default={}) or {}
    total_capital_eur = float(capital_state.get("total_capital_eur", 0.0) or 0.0)
    deployable_capital_eur = float(capital_state.get("deployable_capital_eur", 0.0) or 0.0)

    bricks = {}
    funding_pools = {}

    for item in enabled_payloads:
        brick = item.get("brick", "unknown")
        funding_pool = item.get("funding_pool", "unknown")

        raw_signal_weight = float(item.get("target_weight", 0.0) or 0.0)

        is_governed_target = brick in final_brick_weights
        exclusion_reason = excluded_inputs.get(brick)

        final_target_weight = float(
            final_brick_weights.get(brick, 0.0) or 0.0
        )

        real_state = get_real_brick_state(brick, deployable_capital_eur)

        is_shadow = (
            item.get("portfolio_role") == "shadow_overlay"
            or item.get("execution_mode") == "shadow_only"
            or item.get("signal_type") == "shadow_observation"
        )

        if is_shadow:
            brick_status = "shadow_active"
        elif exclusion_reason:
            brick_status = "policy_excluded_observation"
        elif is_governed_target:
            brick_status = "active_simulated"
        else:
            brick_status = "ungoverned_observation"

        bricks[brick] = {
            "status": brick_status,
            "target_weight_snapshot": round(final_target_weight, 6),
            "raw_signal_weight": round(raw_signal_weight, 6),
            "current_weight_estimate": real_state.get("current_weight_estimate") if real_state else round(raw_signal_weight, 6),
            "target_amount_eur": round(final_target_weight * deployable_capital_eur, 2) if deployable_capital_eur > 0 else None,
            "governed_target": is_governed_target,
            "policy_exclusion_reason": exclusion_reason,
            "current_exposure_eur": real_state.get("current_exposure_eur") if real_state else None,
            "state_origin": real_state.get("state_origin") if real_state else "signal_derived",
            "regime": item.get("regime", "unknown"),
            "confidence": float(item.get("confidence", 0.0) or 0.0),
            "portfolio_role": item.get("portfolio_role", "unknown"),
            "funding_pool": funding_pool,
            "allocation": item.get("allocation", {}),
            "risk_flags": item.get("risk_flags", {}),
            "inertia_profile": item.get("inertia_profile", {})
        }

        if real_state:
            bricks[brick]["positions_count"] = real_state.get(
                "positions_count"
            )
            bricks[brick]["state_source"] = real_state.get(
                "state_source"
            )

            for field in (
                "pocket_source",
                "internal_used_risk_eur",
                "internal_used_risk_pct",
                "internal_max_total_risk_eur",
                "internal_max_trade_risk_eur",
                "internal_available_risk_eur",
            ):
                if field in real_state:
                    bricks[brick][field] = real_state[field]

        if funding_pool not in funding_pools:
            funding_pools[funding_pool] = {
                "brick_count": 0,
                "governed_brick_count": 0,
                "observation_count": 0,
                "target_weight_sum": 0.0,
                "bricks": [],
                "governed_bricks": [],
                "observations": [],
            }

        funding_pools[funding_pool]["brick_count"] += 1
        funding_pools[funding_pool]["bricks"].append(brick)

        if is_governed_target:
            funding_pools[funding_pool]["governed_brick_count"] += 1
            funding_pools[funding_pool]["target_weight_sum"] += final_target_weight
            funding_pools[funding_pool]["governed_bricks"].append(brick)
        else:
            funding_pools[funding_pool]["observation_count"] += 1
            funding_pools[funding_pool]["observations"].append({
                "brick": brick,
                "status": brick_status,
                "reason": exclusion_reason or "not_in_final_target",
            })

    if isinstance(lt_data, dict):
        lt_totals = lt_data.get("totals", {}) if isinstance(lt_data.get("totals"), dict) else {}
        lt_value = float(
            lt_data.get("total_value_eur")
            or lt_data.get("market_value_eur")
            or lt_totals.get("market_value_eur")
            or 0.0
        )

    if isinstance(lt_data, dict) and lt_value > 0:

        bricks["long_term"] = {
            "status": "active",
            "target_weight_snapshot": 0.0,
            "current_weight_estimate": 0.0,
            "current_exposure_eur": round(lt_value, 6),
            "state_origin": "lt_passive_snapshot",
            "regime": "long_term_hold",
            "confidence": 1.0,
            "portfolio_role": "patrimonial_core",
            "funding_pool": "ibkr_pool",
            "allocation": lt_data.get("positions", {}),
            "risk_flags": {
                "type": "long_term_passive",
                "total_value_eur": lt_value
            },
            "inertia_profile": {
                "rebalance_frequency": "none"
            }
        }

        if "ibkr_pool" not in funding_pools:
            funding_pools["ibkr_pool"] = {
                "brick_count": 0,
                "governed_brick_count": 0,
                "observation_count": 0,
                "target_weight_sum": 0.0,
                "bricks": [],
                "governed_bricks": [],
                "observations": [],
            }

        funding_pools["ibkr_pool"]["brick_count"] += 1
        funding_pools["ibkr_pool"]["observation_count"] += 1
        funding_pools["ibkr_pool"]["bricks"].append("long_term")
        funding_pools["ibkr_pool"]["observations"].append({
            "brick": "long_term",
            "status": "passive_patrimonial_observation",
            "reason": "outside_active_allocation_target",
        })

    for pool in funding_pools.values():
        pool["target_weight_sum"] = round(pool["target_weight_sum"], 6)
        if deployable_capital_eur > 0:
            pool["target_amount_eur"] = round(pool["target_weight_sum"] * deployable_capital_eur, 2)

    capital_context = {
        "total_capital_eur": round(total_capital_eur, 2),
        "deployable_capital_eur": round(deployable_capital_eur, 2),
        "capital_state_path": str(CAPITAL_STATE_PATH)
    }

    capital_engaged_eur = round(
        sum(float((b or {}).get("current_exposure_eur") or 0.0) for b in bricks.values()),
        2
    )
    cash_available_eur = round(max(0.0, deployable_capital_eur - capital_engaged_eur), 2)
    live_exposure_ratio = round(
        capital_engaged_eur / deployable_capital_eur,
        6
    ) if deployable_capital_eur > 0 else 0.0
    total_value_eur = round(
        deployable_capital_eur +
        sum(float((b or {}).get("unrealized_pnl_eur") or 0.0) for b in bricks.values()),
        2
    )

    portfolio_state = {
        "status": "ok",
        "engine": "portfolio_state_builder_v1_4",
        "total_value_eur": total_value_eur,
        "capital_observed_eur": round(deployable_capital_eur, 2),
        "capital_engaged_eur": capital_engaged_eur,
        "cash_available_eur": cash_available_eur,
        "live_exposure_ratio": live_exposure_ratio,
        "data_dir": str(DATA_DIR),
        "inputs_loaded": len(payloads),
        "inputs_enabled": len(enabled_payloads),
        "target_source_engine": target_data.get("engine", "unknown"),
        "portfolio_regime": target_data.get("portfolio_regime", "unknown"),
        "capital_context": capital_context,
        "bricks": bricks,
        "funding_pools": funding_pools,
        "notes": [
            "V1.2 writes runtime artifacts into NSC_DATA_DIR/portfolio.",
            "target_weight_snapshot aligns with portfolio_target.final_brick_weights.",
            "current_weight_estimate uses brick state when available; otherwise falls back to signal-derived estimates.",
            "Long Term is injected as a passive patrimonial pocket when lt_portfolio.json is available.",
            "options_us current exposure represents funded pocket capital, while internal risk usage remains separately reported."
        ]
    }

    save_json(portfolio_state, OUTPUT_PATH)
    return portfolio_state


if __name__ == "__main__":
    result = run_portfolio_state_builder()
    print(json.dumps(result, indent=2))
