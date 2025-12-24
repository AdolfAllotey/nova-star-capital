# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

# IMPORTANT :
# - Ne PAS mettre de prefix ici. Le prefix "/api" est ajouté dans server.py via app.include_router(..., prefix="/api")
router = APIRouter(tags=["backtests"])

# Répertoire racine des rapports (aligné sur v2.strategy.backtest)
THIS_FILE = Path(__file__).resolve()
V2_DIR = THIS_FILE.parents[1]  # .../src/v2
REPORTS_DIR = V2_DIR / "data" / "reports" / "backtests"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _list_run_dirs() -> List[Path]:
    """Retourne la liste des sous-répertoires (un run par dossier)."""
    if not REPORTS_DIR.exists():
        return []
    return sorted([p for p in REPORTS_DIR.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def _run_info(p: Path) -> Dict[str, Any]:
    """Infos synthétiques sur un run."""
    try:
        st = p.stat()
        files_count = len([f for f in p.iterdir() if f.is_file()])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run inexistant")
    return {
        "id": p.name,
        "path": str(p),
        "mtime": int(st.st_mtime),
        "files_count": files_count,
    }


def _safe_join(base: Path, *parts: str) -> Path:
    """Empêche la traversal (..)."""
    target = (base / Path(*parts)).resolve()
    base_resolved = base.resolve()
    if not str(target).startswith(str(base_resolved)):
        raise HTTPException(status_code=400, detail="Chemin invalide")
    return target


def _read_metrics_json(run_dir: Path) -> Optional[Dict[str, Any]]:
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        try:
            return json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _read_summary_csv(run_dir: Path, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Lit summary.csv si présent (cas des _batch_...).
    Le CSV peut contenir des colonnes : symbol, tf, ret, sharpe, sortino, mdd, trades, ...
    """
    out: List[Dict[str, Any]] = []
    csv_path = run_dir / "summary.csv"
    if not csv_path.exists():
        return out
    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                out.append(row)
                if limit and i + 1 >= limit:
                    break
    except Exception:
        return []
    return out


@router.get("/backtests/runs", summary="Lister les runs de backtest")
def list_runs() -> List[Dict[str, Any]]:
    """
    Liste tous les répertoires dans src/v2/data/reports/backtests (triés par mtime décroissant).
    """
    runs = _list_run_dirs()
    return [_run_info(p) for p in runs]


@router.get("/backtests/runs/{run_id}/files", summary="Lister les fichiers d’un run")
def list_files(run_id: str) -> List[str]:
    """
    Retourne la liste des fichiers d’un run donné (noms simples).
    """
    run_dir = _safe_join(REPORTS_DIR, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run introuvable")
    files = [f.name for f in run_dir.iterdir() if f.is_file()]
    files.sort()
    return files


@router.get("/backtests/runs/{run_id}/download", summary="Télécharger un fichier d’un run")
def download_file(run_id: str, file: str = Query(..., description="Nom du fichier à télécharger")):
    """
    Télécharge un fichier spécifique (ex: equity.png, metrics.json, summary.csv).
    """
    run_dir = _safe_join(REPORTS_DIR, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run introuvable")

    target = _safe_join(run_dir, file)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    # Laisse FastAPI/deviner le media-type via FileResponse
    return FileResponse(str(target), filename=target.name)


@router.get("/backtests/runs/{run_id}/summary", summary="Résumé JSON d’un run")
def run_summary(run_id: str, limit: int = Query(50, ge=1, le=1000)) -> Dict[str, Any]:
    """
    Renvoie un résumé JSON :
      - si run = _batch_* : lecture de summary.csv
      - sinon : lecture de metrics.json (si présent)
    """
    run_dir = _safe_join(REPORTS_DIR, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run introuvable")

    result: Dict[str, Any] = {"run": _run_info(run_dir)}

    if run_id.startswith("_batch_"):
        rows = _read_summary_csv(run_dir, limit=limit)
        result["type"] = "batch"
        result["summary"] = rows
        result["count"] = len(rows)
    else:
        metrics = _read_metrics_json(run_dir)
        result["type"] = "single"
        result["metrics"] = metrics or {}
        # expose aussi la liste des fichiers utiles
        files = [f.name for f in run_dir.glob("*") if f.is_file()]
        result["files"] = sorted(files)

    return result
