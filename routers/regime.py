from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

@router.get("/regime")
def get_regime():
    """
    Renvoie le régime de marché actuel (bull/bear/range)
    basé sur le fichier /var/lib/nsc/regime.json généré par le détecteur.
    """
    p = Path("/var/lib/nsc/regime.json")
    if not p.exists():
        raise HTTPException(status_code=404, detail="regime.json not found")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture regime.json: {e}")
