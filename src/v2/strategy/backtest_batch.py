# -*- coding: utf-8 -*-
"""
Batch runner pour backtests v2 :
- Lit une liste de symboles/TF
- Explore une grille de paramètres (SMA fast/slow, fees, slippage)
- Appelle v2.strategy.backtest en mémoire et agrège les métriques
- Sauvegarde un récap global trié par performance

Env:
  NSC_API_TOKEN (requis)
  NSC_API_BASE  (defaut: http://127.0.0.1:8000)

Exemples:
  PYTHONPATH=src python -m v2.strategy.backtest_batch \
    --symbols BTCUSDT,ETHUSDT --tf 15m,1h --days 30 \
    --grid "sma_fast=8,10; sma_slow=18,20,30; fees=0.0004; slippage=0.0002"

  # Symbols via fichier (un symbole par ligne)
  PYTHONPATH=src python -m v2.strategy.backtest_batch \
    --symbols-file src/v2/data/universe/majors.txt --tf 1h --days 30
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from v2.strategy.backtest import (
    fetch_ohlcv,
    sma_crossover_signals,
    backtest_core,
    calc_metrics,
    REPORTS_DIR,
)

DEF_GRID = {
    "sma_fast": [10],
    "sma_slow": [20],
    "fees": [0.0004],
    "slippage": [0.0002],
}

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch backtests (agrégé)")
    p.add_argument("--symbols", default="", help="Liste de symboles séparés par des virgules")
    p.add_argument("--symbols-file", default="", help="Fichier avec un symbole/ligne")
    p.add_argument("--tf", default="1h", help="Liste de TF (ex: 15m,1h)")
    p.add_argument("--days", type=int, default=30, help="Fenêtre en jours")
    p.add_argument("--limit", type=int, default=None, help="Force un limit (sinon auto)")
    p.add_argument(
        "--grid",
        default="",
        help='Grille param (ex: "sma_fast=8,10; sma_slow=18,20,30; fees=0.0004; slippage=0.0002")',
    )
    p.add_argument("--outdir", default=str(REPORTS_DIR), help="Dossier des sorties individuelles")
    p.add_argument("--summary", default="summary.csv", help="Nom du CSV agrégé")
    return p.parse_args()

def load_symbols(args: argparse.Namespace) -> List[str]:
    items: List[str] = []
    if args.symbols:
        items += [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        with open(args.symbols_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    items.append(s.upper())
    if not items:
        items = ["BTCUSDT"]
    return sorted(set(items))

def load_tfs(tf_str: str) -> List[str]:
    return [t.strip() for t in tf_str.split(",") if t.strip()]

def parse_grid(grid_str: str) -> Dict[str, List[float]]:
    if not grid_str.strip():
        return DEF_GRID
    grid: Dict[str, List[float]] = {}
    for part in grid_str.split(";"):
        if not part.strip():
            continue
        k, v = part.split("=")
        k = k.strip()
        vals = [x.strip() for x in v.split(",")]
        # cast float/int auto
        casted = []
        for x in vals:
            try:
                if "." in x:
                    casted.append(float(x))
                else:
                    casted.append(int(x))
            except ValueError:
                casted.append(float(x))  # dernier recours
        grid[k] = casted
    # Minimum requis pour la stratégie
    grid.setdefault("sma_fast", DEF_GRID["sma_fast"])
    grid.setdefault("sma_slow", DEF_GRID["sma_slow"])
    grid.setdefault("fees", DEF_GRID["fees"])
    grid.setdefault("slippage", DEF_GRID["slippage"])
    return grid

def grid_iter(grid: Dict[str, List[float]]) -> Iterable[Dict[str, float]]:
    keys = list(grid.keys())
    for combo in itertools.product(*[grid[k] for k in keys]):
        yield dict(zip(keys, combo))

def run_one(symbol: str, tf: str, days: int, limit: int | None, base_url: str, token: str,
            params: Dict[str, float]) -> Dict[str, object]:
    df = fetch_ohlcv(symbol, tf, days, limit, base_url, token)
    fast = int(params["sma_fast"])
    slow = int(params["sma_slow"])
    fees = float(params["fees"])
    slippage = float(params["slippage"])

    sig = sma_crossover_signals(df, fast, slow)
    recap, equity = backtest_core(df, sig, fees, slippage)
    m = calc_metrics(recap, equity, tf)

    row = {
        "symbol": symbol,
        "tf": tf,
        **{k: params[k] for k in ["sma_fast", "sma_slow", "fees", "slippage"]},
        **m,
    }
    return row

def main() -> None:
    args = parse_args()
    base_url = os.getenv("NSC_API_BASE", "http://127.0.0.1:8000")
    token = os.getenv("NSC_API_TOKEN", "")

    symbols = load_symbols(args)
    tfs = load_tfs(args.tf)
    grid = parse_grid(args.grid)

    rows: List[Dict[str, object]] = []
    for sym in symbols:
        for tf in tfs:
            for params in grid_iter(grid):
                try:
                    rows.append(run_one(sym, tf, args.days, args.limit, base_url, token, params))
                except Exception as e:
                    rows.append({
                        "symbol": sym, "tf": tf, **params,
                        "error": str(e)
                    })

    if not rows:
        print("Aucun résultat.")
        return

    df = pd.DataFrame(rows)
    # Tri par meilleur ret_total puis Sharpe, puis drawdown le plus faible
    if "ret_total" in df and "sharpe" in df and "max_drawdown" in df:
        df = df.sort_values(by=["ret_total", "sharpe", "max_drawdown"], ascending=[False, False, True])

    # Dossier run global (pour tracer l’instant)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(args.outdir) / f"_batch_{ts}"
    out_root.mkdir(parents=True, exist_ok=True)

    out_csv = out_root / args.summary
    df.to_csv(out_csv, index=False)

    with open(out_root / "meta.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "symbols": symbols,
                "tfs": tfs,
                "grid": grid,
                "days": args.days,
                "limit": args.limit,
                "api_base": base_url,
            },
            f,
            indent=2,
        )

    print(f"Résumé agrégé → {out_csv}")
    # Top 10 à l’écran
    print("\nTop 10 (aperçu):")
    with pd.option_context("display.max_columns", None, "display.width", 140):
        print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
