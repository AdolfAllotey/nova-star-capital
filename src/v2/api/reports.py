# src/v2/api/reports.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from .security import require_bearer

router = APIRouter(
    prefix="/api/backtests",
    tags=["backtests"],
    dependencies=[Depends(require_bearer)],
)

# Dossier des backtests (même base que le script backtest.py)
REPORTS_DIR = Path(__file__).resolve().parents[1] / "data" / "reports" / "backtests"

def _safe_run_dir(run_id: str) -> Path:
    base = REPORTS_DIR.resolve()
    target = (base / run_id).resolve()
    if not target.is_dir() or base not in target.parents:
        raise HTTPException(status_code=404, detail="Run not found")
    return target

@router.get("/runs")
def list_runs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    runs: List[dict] = []
    for p in sorted(REPORTS_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_dir():
            try:
                files_count = sum(1 for _ in p.rglob("*") if _.is_file())
            except Exception:
                files_count = 0
            runs.append({
                "id": p.name,
                "path": str(p),
                "mtime": int(p.stat().st_mtime),
                "files_count": files_count,
            })
    return runs

@router.get("/runs/{run_id}/files")
def list_run_files(run_id: str):
    d = _safe_run_dir(run_id)
    out = []
    for f in sorted(d.rglob("*")):
        if f.is_file():
            rel = f.relative_to(d).as_posix()
            out.append(rel)
    return out

@router.get("/runs/{run_id}/summary")
def get_run_summary(run_id: str):
    d = _safe_run_dir(run_id)
    metrics = d / "metrics.json"
    summary_csv = d / "summary.csv"  # présent pour les batchs
    if metrics.exists():
        try:
            return json.loads(metrics.read_text())
        except Exception:
            raise HTTPException(500, detail="metrics.json illisible")
    if summary_csv.exists():
        # Pour rester JSON-friendly on retourne un aperçu + info de téléchargement
        lines = summary_csv.read_text().splitlines()
        head = lines[:20]
        return {
            "note": "summary.csv trouvé (batch). Utilisez /download?file=summary.csv pour le fichier complet.",
            "preview": head,
            "total_lines": len(lines),
        }
    raise HTTPException(404, detail="Aucun summary disponible (ni metrics.json ni summary.csv)")

@router.get("/runs/{run_id}/download")
def download_artifact(run_id: str, file: str = Query(..., description="Chemin relatif dans le run")):
    d = _safe_run_dir(run_id)
    target = (d / file).resolve()
    if d not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(target)
