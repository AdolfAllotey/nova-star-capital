from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import os

router = APIRouter()

DEFAULT_DATA_DIR = "/opt/nsc/data/preprod"
DATA_DIR = Path(os.getenv("NSC_DATA_DIR", DEFAULT_DATA_DIR))
PORTFOLIO_DIR = DATA_DIR / "portfolio"


def _read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading {path.name}: {e}")


@router.get("/portfolio-target", summary="Portfolio target (aggregator)")
@router.get("/api/portfolio-target", summary="Portfolio target (aggregator)")
def get_portfolio_target():
    return _read_json(PORTFOLIO_DIR / "portfolio_target.json")


@router.get(
    "/api/portfolio-state",
    summary="Portfolio state (canonical API alias)",
    operation_id="get_portfolio_state_api_hyphen",
)
@router.get(
    "/portfolio-state",
    summary="Portfolio state (aggregator)",
    operation_id="get_portfolio_state_root_hyphen",
)
def get_portfolio_state():
    return _read_json(PORTFOLIO_DIR / "state" / "portfolio_state.json")


@router.get("/rebalance-plan", summary="Rebalance plan (aggregator)")
@router.get("/api/rebalance-plan", summary="Rebalance plan (aggregator)")
def get_rebalance_plan():
    return _read_json(PORTFOLIO_DIR / "rebalance" / "rebalance_plan.json")


@router.get("/funding-plan", summary="Funding plan (aggregator)")
@router.get("/api/funding-plan", summary="Funding plan (aggregator)")
def get_funding_plan():
    return _read_json(PORTFOLIO_DIR / "rebalance" / "funding_plan.json")


@router.get("/aggregator-audit", summary="Aggregator audit")
@router.get("/api/aggregator-audit", summary="Aggregator audit")
def get_aggregator_audit():
    return _read_json(PORTFOLIO_DIR / "audit" / "aggregator_audit.json")

@router.get("/portfolio/rebalance-plan")
def get_portfolio_rebalance_plan_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/rebalance/rebalance_plan.json"))

@router.get("/portfolio/funding-plan")
def get_portfolio_funding_plan_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/rebalance/funding_plan.json"))

@router.get("/portfolio/master-coherence-audit")
def get_portfolio_master_coherence_audit_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/master_coherence_audit.json"))

@router.get(
    "/api/portfolio/orchestration-status",
    operation_id="get_portfolio_orchestration_status_api",
)
@router.get(
    "/portfolio/orchestration-status",
    operation_id="get_portfolio_orchestration_status_root",
)
def get_portfolio_orchestration_status_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/orchestration_status.json"))

@router.get(
    "/api/portfolio/orchestration-consistency",
    operation_id="get_portfolio_orchestration_consistency_api",
)
@router.get(
    "/portfolio/orchestration-consistency",
    operation_id="get_portfolio_orchestration_consistency_root",
)
def get_portfolio_orchestration_consistency_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/orchestration_consistency.json"))

@router.get("/portfolio/global-orchestration-audit")
def get_portfolio_global_orchestration_audit_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_orchestration_audit.json"))

@router.get("/portfolio/supervision-gate")
def get_portfolio_supervision_gate_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/supervision_gate.json"))

@router.get("/portfolio/institutional-supervision-summary")
def get_portfolio_institutional_supervision_summary_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/institutional_supervision_summary.json"))

@router.get("/portfolio/global-preprod-cycle-report")
def get_portfolio_global_preprod_cycle_report_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_cycle_report.json"))

@router.get("/portfolio/global-preprod-stress-tests")
def get_portfolio_global_preprod_stress_tests_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_stress_test_report.json"))

@router.get("/portfolio/global-preprod-history-summary")
def get_portfolio_global_preprod_history_summary_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_history_summary.json"))

@router.get("/portfolio/global-preprod-trend-monitor")
def get_portfolio_global_preprod_trend_monitor_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_trend_monitor.json"))

@router.get("/portfolio/global-preprod-anomaly-detector")
def get_portfolio_global_preprod_anomaly_detector_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_anomaly_detector.json"))

@router.get("/portfolio/global-preprod-long-run-readiness")
def get_portfolio_global_preprod_long_run_readiness_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_long_run_readiness.json"))

@router.get("/portfolio/global-preprod-48h-shadow-supervisor")
def get_portfolio_global_preprod_48h_shadow_supervisor_alias():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_48h_shadow_supervisor.json"))

@router.get("/api/allocation-policy", summary="Allocation policy layer")
@router.get("/allocation-policy", summary="Allocation policy layer")
def get_allocation_policy():
    path = DATA_DIR / "portfolio" / "policy" / "allocation_policy.json"
    if not path.exists():
        return {
            "status": "missing",
            "path": str(path),
            "policy_role": "master_policy_layer",
            "source_of_truth": False,
        }
    return _read_json(path)


@router.get("/portfolio/global-preprod-long-run-daily-check")
@router.get("/api/portfolio/global-preprod-long-run-daily-check")
def get_portfolio_global_preprod_long_run_daily_check():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_long_run_daily_check.json"))

@router.get("/portfolio/global-preprod-long-run-daily-report")
@router.get("/api/portfolio/global-preprod-long-run-daily-report")
def get_portfolio_global_preprod_long_run_daily_report():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_long_run_daily_report.json"))

@router.get("/portfolio/global-preprod-production-readiness")
@router.get("/api/portfolio/global-preprod-production-readiness")
def get_portfolio_global_preprod_production_readiness():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_production_readiness.json"))

@router.get("/portfolio/global-preprod-weekly-review")
@router.get("/api/portfolio/global-preprod-weekly-review")
def get_portfolio_global_preprod_weekly_review():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_weekly_review.json"))

@router.get("/portfolio/global-preprod-committee-review")
@router.get("/api/portfolio/global-preprod-committee-review")
def get_portfolio_global_preprod_committee_review():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_committee_review.json"))

@router.get("/portfolio/global-dynamic-metrics-audit")
@router.get("/api/portfolio/global-dynamic-metrics-audit")
def get_portfolio_global_dynamic_metrics_audit():
    return _read_json(Path("/opt/nsc/data/preprod/portfolio/audit/global_dynamic_metrics_audit.json"))
