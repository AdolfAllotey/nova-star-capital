#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
from pathlib import Path

# --- chemins de base
ROOT = Path("/opt/nsc")
CFG_PATH = ROOT / "src" / "v2" / "config" / "settings.json"
REPORTS_DIR = ROOT / "src" / "v2" / "data" / "reports"
LOGS_DIR = ROOT / "src" / "v2" / "logs"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} {msg}"
    print(line)
    with open(LOGS_DIR / "lt_dca_scheduler.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def run_once():
    cfg = load_json(CFG_PATH, {})
    dca = cfg.get("lt_dca", {})
    enabled = bool(dca.get("enabled", False))
    if not enabled:
        log("[lt_dca] disabled; exit")
        status = {
            "enabled": False,
            "frequency": dca.get("frequency", "weekly"),
            "next_run_utc": None,
            "last_run": {"ts": None, "orders": []}
        }
        save_json(REPORTS_DIR / "lt_dca_status.json", status)
        return 0

    stable = cfg.get("stablecoin", {}).get("primary", "USDC")
    targets = dca.get("per_asset_targets", {"BTC": 1.0})
    # ⚠️ Ici on ne place pas d'ordre réel : on simule un succès minimal pour valider l’intégration
    orders = []
    total_budget_usdc = 0.0  # à remplacer par lecture d’un solde réel plus tard
    # Demo: exécute une ligne factice si aucun budget (pour tester le service)
    for asset, w in targets.items():
        budget = round(10.0 * float(w), 2)  # 10 USDC fictifs pour smoke-test
        orders.append({"asset": asset, "amount_usdc": budget, "price": "market", "txid": "SIMULATED"})
        total_budget_usdc += budget

    status = {
        "enabled": True,
        "frequency": dca.get("frequency", "weekly"),
        "next_run_utc": None,  # géré par le timer systemd
        "last_run": {
            "ts": datetime.now(timezone.utc).isoformat(),
            "orders": orders,
            "stable_used": stable,
            "total_budget_usdc": round(total_budget_usdc, 2)
        }
    }
    save_json(REPORTS_DIR / "lt_dca_status.json", status)
    log(f"[lt_dca] wrote {len(orders)} simulated orders → {REPORTS_DIR/'lt_dca_status.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(run_once())
