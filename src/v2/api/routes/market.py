# /opt/nsc/app/src/v2/api/routes/market.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
import os, json, datetime as dt

router = APIRouter(prefix="/market", tags=["market"])

def _data_root() -> str:
    # respecte NSC_DATA_ROOT si présent, sinon chemin par défaut
    return os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")

def _top_movers_path() -> str:
    # tu peux adapter ce sous-dossier si tu préfères /reports/
    return os.path.join(_data_root(), "market", "top_movers.json")

@router.get("/top-movers")
def get_top_movers() -> Dict[str, Any]:
    """
    Renvoie les 'top movers' préparés par le batch (ou un autre service).
    Structure attendue dans top_movers.json :
    {
      "updated_at": "2025-11-03T20:55:12Z",
      "items": [
        {"symbol":"BTC","price":...,"change_24h":...,"volume_24h":...},
        ...
      ]
    }
    """
    path = _top_movers_path()
    if not os.path.exists(path):
        # on retourne un 200 vide + message (plus pratique côté UI)
        return {"updated_at": None, "items": [], "message": f"Fichier introuvable: {path}"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lecture KO: {e}")

    # garde-fous minimum
    items: List[Dict[str, Any]] = payload.get("items", [])
    updated_at = payload.get("updated_at")
    if updated_at is None:
        # si absent, on l’infère du mtime du fichier
        ts = dt.datetime.utcfromtimestamp(os.path.getmtime(path)).replace(microsecond=0).isoformat() + "Z"
        updated_at = ts

    return {"updated_at": updated_at, "items": items}
