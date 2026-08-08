from pathlib import Path
from datetime import datetime, timezone
import json

REGIME_PATH = Path("/opt/nsc/data/preprod/analysis/market_regime_detector.json")
OUT_PATH = Path("/opt/nsc/data/preprod/analysis/effective_nsc_intensity.json")

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def main():
    d = json.loads(REGIME_PATH.read_text(encoding="utf-8"))

    confidence = float(d.get("confidence", d.get("score", 0)) or 0)
    regime = str(d.get("regime", "unknown")).lower()
    components = d.get("components") or {}

    breadth = float(components.get("breadth", 0) or 0)
    macro = float(components.get("macro", 0) or 0)

    intensity = confidence

    if breadth <= 0:
        intensity *= 0.90

    if macro < 0:
        intensity *= 0.90

    if regime in ("risk_off", "bear"):
        intensity *= 0.50

    if regime in ("unknown", "neutral"):
        intensity *= 0.70

    intensity = clamp(intensity)

    if intensity >= 0.75:
        mode = "aggressive"
        size_factor = 1.00
        max_positions_factor = 1.00
    elif intensity >= 0.55:
        mode = "moderate"
        size_factor = 0.70
        max_positions_factor = 0.75
    elif intensity >= 0.35:
        mode = "defensive"
        size_factor = 0.45
        max_positions_factor = 0.50
    else:
        mode = "protective"
        size_factor = 0.25
        max_positions_factor = 0.30

    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": "effective_nsc_intensity_v1",
        "market_regime": regime,
        "market_confidence": confidence,
        "effective_intensity": round(intensity, 4),
        "effective_intensity_pct": round(intensity * 100, 2),
        "mode": mode,
        "recommended_size_factor": size_factor,
        "recommended_max_positions_factor": max_positions_factor,
        "drivers": {
            "breadth": breadth,
            "macro": macro,
            "breadth_penalty": breadth <= 0,
            "macro_penalty": macro < 0
        }
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
