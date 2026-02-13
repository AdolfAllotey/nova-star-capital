#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

@dataclass
class UniverseFilters:
    min_dollar_vol_20d: float = 500_000_000.0
    min_rs_6m: float = 55.0
    min_ret_60d: float = -0.02
    max_atr_pct_14: float = 0.06  # avoid ultra wild names

def filter_universe(
    symbols: List[str],
    metrics: Dict[str, Any],
    f: UniverseFilters
) -> Tuple[List[str], Dict[str, Any]]:
    kept = []
    dropped: Dict[str, Any] = {}

    for sym in symbols:
        m = metrics.get(sym) or {}
        dv = float(m.get("avg_dollar_vol_20d") or 0.0)
        rs = float(m.get("rs_6m") or 0.0)
        ret = float(m.get("ret_60d") or 0.0)
        atr = float(m.get("atr_pct_14") or 0.0)

        reasons = []
        if dv < f.min_dollar_vol_20d:
            reasons.append(f"low_dollar_vol<{f.min_dollar_vol_20d}")
        if rs < f.min_rs_6m:
            reasons.append(f"rs_6m<{f.min_rs_6m}")
        if ret < f.min_ret_60d:
            reasons.append(f"ret_60d<{f.min_ret_60d}")
        if atr > f.max_atr_pct_14:
            reasons.append(f"atr_pct_14>{f.max_atr_pct_14}")

        if reasons:
            dropped[sym] = {"reasons": reasons, "metrics": m}
        else:
            kept.append(sym)

    return kept, dropped

def build_universe(
    shortlist_path: str = "data/equities_offensive/universe/shortlist_nasdaq.json",
    metrics_path: str = "data/equities_offensive/universe/metrics_snapshot.json",
    out_path: str = "data/equities_offensive/universe/universe_filtered.json"
) -> Dict[str, Any]:
    shortlist = load_json(Path(shortlist_path), default={}) or {}
    metrics_doc = load_json(Path(metrics_path), default={}) or {}

    symbols = shortlist.get("symbols") or []
    metrics = metrics_doc.get("metrics") or {}

    filt = UniverseFilters()
    kept, dropped = filter_universe(list(symbols), dict(metrics), filt)

    out = {
        "ts": utc_now_iso(),
        "universe": shortlist.get("universe", "nasdaq_core"),
        "filters": {
            "min_dollar_vol_20d": filt.min_dollar_vol_20d,
            "min_rs_6m": filt.min_rs_6m,
            "min_ret_60d": filt.min_ret_60d,
            "max_atr_pct_14": filt.max_atr_pct_14
        },
        "count_in": len(symbols),
        "count_out": len(kept),
        "symbols": kept,
        "dropped": dropped
    }
    save_json(Path(out_path), out)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NSC Nasdaq Universe Loader (shortlist + metrics -> filtered)")
    ap.add_argument("--shortlist", default="data/equities_offensive/universe/shortlist_nasdaq.json")
    ap.add_argument("--metrics", default="data/equities_offensive/universe/metrics_snapshot.json")
    ap.add_argument("--out", default="data/equities_offensive/universe/universe_filtered.json")
    args = ap.parse_args()

    out = build_universe(args.shortlist, args.metrics, args.out)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
