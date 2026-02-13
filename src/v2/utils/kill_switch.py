import json
import os
from pathlib import Path

def _env_true(v: str | None) -> bool:
    if not v:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}

def is_kill_switch_active(governance_path: str = "data/governance/governance_engine_pro.json") -> bool:
    # 1) Override immédiat via variable d’environnement
    if _env_true(os.getenv("NSC_KILL_SWITCH")):
        return True

    # 2) Fichier de gouvernance (optionnel)
    try:
        p = Path(governance_path)
        if not p.exists():
            return False
        d = json.loads(p.read_text(encoding="utf-8"))
        return bool(d.get("kill_switch", {}).get("active", False))
    except Exception:
        return False
