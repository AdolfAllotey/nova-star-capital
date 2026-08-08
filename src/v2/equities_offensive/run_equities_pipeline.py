from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class Step:
    name: str
    cmd: list[str]


def run_step(step: Step) -> None:
    print(f"\n=== [equities_pipeline] {step.name} ===")
    print("cmd:", " ".join(step.cmd))
    subprocess.run(step.cmd, check=True)


def main() -> int:
    os.environ.setdefault("NSC_ENV", "PREPROD")
    os.environ.setdefault("NSC_EQU_ACTION_POLICY", "SIMULATED_EXECUTION")

    steps = [
        Step("sync_ops", [sys.executable, "src/v2/equities_offensive/ops/sync_ops.py"]),
        Step("sync_governance", [sys.executable, "src/v2/equities_offensive/governance/sync_governance.py"]),
        Step("sync_market_regime", [sys.executable, "src/v2/equities_offensive/market/sync_market_regime.py"]),
        
        
        Step("signal_engine", [sys.executable, "src/v2/equities_offensive/engines/signal_engine_v1.py"]),
        Step("voting_engine", [sys.executable, "src/v2/equities_offensive/voting/voting_engine_v1.py"]),
        Step("risk_engine", [sys.executable, "src/v2/equities_offensive/risk/risk_engine_v1.py"]),
        Step("exit_signal_engine", [sys.executable, "src/v2/equities_offensive/risk/exit_signal_engine.py"]),
        Step("execution_plan_builder", [sys.executable, "src/v2/equities_offensive/execution/execution_plan_builder.py"]),
        Step("simulated_broker", [sys.executable, "src/v2/equities_offensive/broker/simulated_broker.py"]),
        Step("position_tracker", [sys.executable, "src/v2/equities_offensive/execution/position_tracker.py"]),
        Step("post_trade_reconciliation", [sys.executable, "src/v2/equities_offensive/execution/post_trade_reconciliation.py"]),
        Step("ui_bundle_builder", [sys.executable, "src/v2/equities_offensive/ui/ui_bundle_builder.py"]),
        Step("report_builder_v1", [sys.executable, "src/v2/equities_offensive/reporting/report_builder_v1.py"]),
        Step("preprod_check", [sys.executable, "src/v2/equities_offensive/tests/preprod_check.py"]),
    ]

    print(f"[equities_pipeline] ts={utc_now_iso()} env={os.environ.get('NSC_ENV')}")
    for st in steps:
        run_step(st)

    print("\n[equities_pipeline] ✅ all steps OK")
    return 0


if __name__ == "__main__":
    rc = main()
    subprocess.run(
        [sys.executable, "src/v2/portfolio/offensive_equity_curve_updater.py"],
        check=False,
    )
    raise SystemExit(rc)
