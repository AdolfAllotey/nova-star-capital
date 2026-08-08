from __future__ import annotations

import json

from src.v2.capital.capital_state_engine import build_capital_state
from src.v2.capital.capital_governor import run as run_governor
from src.v2.capital.rebalance_engine import run as run_rebalance
from src.v2.capital.funding_engine import run as run_funding
from src.v2.capital.survival_engine import run as run_survival
from src.v2.capital.capital_metrics import run as run_metrics
from src.v2.capital.portfolio_state_engine import build_portfolio_state
from src.v2.capital.capital_bucket_mapper import run as run_bucket_mapper
from src.v2.capital.enterprise_value_engine import run as run_enterprise_value
from src.v2.capital.collateral_state_engine import run as run_collateral_state
from src.v2.capital.treasury_state_engine import run as run_treasury_state
from src.v2.capital.family_office_bundle_engine import run as run_family_office_bundle


def main():
    out = {
        "capital_state": build_capital_state(),
        "capital_governor": run_governor(),
        "portfolio_state": build_portfolio_state(),
        "portfolio_state_normalized": run_bucket_mapper(),
        "survival": run_survival(),
        "rebalance_plan": run_rebalance(),
        "funding_plan": run_funding(),
        "capital_metrics": run_metrics(),
        "enterprise_value": run_enterprise_value(),
        "collateral_state": run_collateral_state(),
        "treasury_state": run_treasury_state(),
        "family_office_bundle": run_family_office_bundle()
    }
    print(json.dumps({
        "status": "ok",
        "engine": "capital_brain_runner_v1",
        "summary": {
            "nav_eur": out["capital_state"].get("total_nav_eur"),
            "mode": out["capital_governor"].get("mode"),
            "survival_mode": out["survival"].get("mode"),
            "portfolio_state_nav": out["portfolio_state"].get("nav_eur"),
            "rebalance_status": out["rebalance_plan"].get("status"),
            "funding_status": out["funding_plan"].get("status"),
            "enterprise_net_value": out["enterprise_value"]["enterprise_value"].get("net_value_eur"),
            "collateral_ltv": out["collateral_state"].get("ltv_current"),
            "collateral_status": out["collateral_state"].get("ltv_status"),
            "treasury_health": out["treasury_state"]["health"].get("treasury_health"),
            "family_office_bundle_status": out["family_office_bundle"].get("status")
        }
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
