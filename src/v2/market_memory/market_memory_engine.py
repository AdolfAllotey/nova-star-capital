from pathlib import Path
from datetime import datetime, timezone
import json

BASE = Path("/opt/nsc/data/preprod")
OUT = BASE / "market_memory"
OUT.mkdir(parents=True, exist_ok=True)

MOVERS = BASE / "market/top_movers_combined.json"
META = BASE / "discovery/meta_rankings.json"
DISCOVERY = BASE / "discovery/discovery_summary.json"
MEMORY = OUT / "market_memory.json"

def read_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def now():
    return datetime.now(timezone.utc).isoformat()

def norm_symbol(x):
    return str(x or "").upper().strip()

def update_memory():
    ts = now()
    memory = read_json(MEMORY, {"generated_at": ts, "assets": {}})
    assets = memory.get("assets", {})

    movers = read_json(MOVERS, {}).get("items", [])
    meta_items = read_json(META, {}).get("items", [])
    discovery_items = read_json(DISCOVERY, {}).get("top_candidates", [])

    by_symbol = {}

    for item in movers:
        s = norm_symbol(item.get("symbol"))
        if s:
            by_symbol.setdefault(s, {}).update({
                "symbol": s,
                "name": item.get("name"),
                "source": item.get("source"),
                "pair": item.get("pair"),
                "tradable": item.get("tradable"),
                "chg_24h": item.get("chg_24h"),
                "price": item.get("price"),
            })

    for item in discovery_items:
        s = norm_symbol(item.get("symbol"))
        if s:
            by_symbol.setdefault(s, {}).update({
                "symbol": s,
                "discovery_score": item.get("score"),
                "discovery_chg_24h": item.get("chg_24h"),
                "discovery_sources": item.get("sources"),
            })

    for item in meta_items:
        s = norm_symbol(item.get("symbol"))
        if s:
            by_symbol.setdefault(s, {}).update({
                "symbol": s,
                "meta_rank": item.get("meta_rank"),
                "persistence_score": item.get("persistence_score"),
                "momentum_score": item.get("momentum_score"),
                "social_score": item.get("social_score"),
                "source_score": item.get("source_score"),
                "hours_present": item.get("hours_present"),
                "observations": item.get("observations"),
                "verdict": item.get("verdict"),
                "recommended": item.get("recommended"),
                "risk_flags": item.get("risk_flags", []),
                "explainability": item.get("explainability", {}),
            })

    for symbol, snapshot in by_symbol.items():
        existing = assets.get(symbol, {})
        observations = existing.get("observations_history", [])
        observations.append({"ts": ts, **snapshot})
        observations = observations[-200:]

        chgs = [float(o.get("chg_24h")) for o in observations if o.get("chg_24h") is not None]
        metas = [float(o.get("meta_rank")) for o in observations if o.get("meta_rank") is not None]

        assets[symbol] = {
            "symbol": symbol,
            "first_seen": existing.get("first_seen") or ts,
            "last_seen": ts,
            "observations_count": len(observations),
            "max_gain_24h": max(chgs) if chgs else None,
            "max_loss_24h": min(chgs) if chgs else None,
            "current_chg_24h": snapshot.get("chg_24h") or snapshot.get("discovery_chg_24h"),
            "max_meta_rank": max(metas) if metas else None,
            "current_meta_rank": snapshot.get("meta_rank"),
            "current_verdict": snapshot.get("verdict"),
            "tradable": snapshot.get("tradable"),
            "pair": snapshot.get("pair"),
            "sources": snapshot.get("discovery_sources") or ([snapshot.get("source")] if snapshot.get("source") else []),
            "hours_present": snapshot.get("hours_present"),
            "persistence_score": snapshot.get("persistence_score"),
            "momentum_score": snapshot.get("momentum_score"),
            "explainability": snapshot.get("explainability", {}),
            "observations_history": observations,
        }

    ranked = sorted(
        assets.values(),
        key=lambda x: (
            float(x.get("current_meta_rank") or 0),
            float(x.get("persistence_score") or 0),
            x.get("observations_count") or 0,
        ),
        reverse=True,
    )

    payload = {
        "generated_at": ts,
        "engine": "market_memory_engine_v1",
        "assets_count": len(assets),
        "assets": assets,
        "top_assets": ranked[:30],
    }

    MEMORY.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload

if __name__ == "__main__":
    payload = update_memory()
    print("Market Memory generated:", MEMORY)
    print("Assets:", payload["assets_count"])
