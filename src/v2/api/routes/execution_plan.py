from fastapi import APIRouter
from pathlib import Path
import json

from src.v2.execution.execution_adapter import build_execution_plan

router = APIRouter()

DATA_DIR = Path("/opt/nsc/data/preprod")

def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except:
        return {}

@router.get("/api/execution-plan")
def get_execution_plan():
    funding_plan = load_json(DATA_DIR / "analysis" / "funding_plan.json")
    governance = load_json(DATA_DIR / "analysis" / "governance_engine_pro.json")

    plan = build_execution_plan(funding_plan, governance)

    return plan
