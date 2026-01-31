import os, json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/app/data"))
BASELINE = DATA_DIR / "telemetry" / "preprod_baseline.json"
KPI = DATA_DIR / "telemetry" / "preprod_runs" / "preprod_kpis.json"

def _safe_load(p: Path, default=None):
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def main():
    BASELINE.parent.mkdir(parents=True, exist_ok=True)

    baseline = _safe_load(BASELINE, default={}) or {}
    if isinstance(baseline, dict) and baseline.get("equity_start_ytd") is not None:
        print(f"✅ baseline already exists: {BASELINE}")
        return

    kpi = _safe_load(KPI, default={}) or {}
    # On essaye de trouver une equity "current" (si dispo)
    equity_current = None
    for key in ("equity_current", "equity", "portfolio_value_eur", "nav_eur"):
        v = kpi.get(key) if isinstance(kpi, dict) else None
        if isinstance(v, (int, float)) and v > 0:
            equity_current = float(v)
            break

    # Fail-safe: si pas d'equity, on met 0 et on ajustera après
    if equity_current is None:
        equity_current = 0.0

    baseline = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "equity_start_ytd": equity_current,
        "note": "PREPROD YTD baseline. Do not edit unless you want to reset YTD."
    }
    BASELINE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ wrote baseline: {BASELINE}")

if __name__ == "__main__":
    main()
