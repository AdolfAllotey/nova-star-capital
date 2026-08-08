from fastapi import APIRouter
from src.v2.utils.file_utils import load_json_file

router = APIRouter()

# DISABLED @router.get("/api/explainability")
def get_explainability():
    return load_json_file("/opt/nsc/app/data/explainability/explainability_report.json", default={})
