# -*- coding: utf-8 -*-
"""
Batch runner : lit un univers YAML et lance les backtests pour chaque (symbol, tf).
Produit des dossiers dans src/v2/data/reports/backtests/ comme le backtest simple.

Usage manuel :
  PYTHONPATH=src NSC_API_BASE=https://api.novastarcapital.fr NSC_API_TOKEN=... \\
  python -m v2.strategy.run_batch --config /root/Bot_crypto_ultra/src/v2/strategy/universe.yaml
"""
from __future__ import annotations
import argparse, os, sys, time, subprocess
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[2]   # /root/Bot_crypto_ultra/src -> parents[2] = repo
BACKTEST_MOD = "v2.strategy.backtest"

def run_backtest(symbol: str, tf: str, days: int,
                 fees: float, slippage: float,
                 sma_fast: int, sma_slow: int,
                 base_url: str|None, token: str|None) -> int:
    env = os.environ.copy()
    if base_url:
        env["NSC_API_BASE"] = base_url
    if token:
        env["NSC_API_TOKEN"] = token

    cmd = [
        sys.executable, "-m", BACKTEST_MOD,
        "--symbols", symbol,
        "--tf", tf,
        "--days", str(days),
        "--fees", str(fees),
        "--slippage", str(slippage),
        "--sma-fast", str(sma_fast),
        "--sma-slow", str(sma_slow),
    ]
    print(f"[RUN] {' '.join(cmd)}")
    return subprocess.call(cmd, env=env, cwd=str(REPO.parent))

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Chemin du universe.yaml")
    p.add_argument("--no-prune", action="store_true", help="(placeholder) ne pas supprimer les anciens runs")
    args = p.parse_args()

    cfg_path = Path(args.config)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    base_url = os.environ.get("NSC_API_BASE", "http://127.0.0.1:8000")
    token    = os.environ.get("NSC_API_TOKEN")

    defaults   = cfg.get("defaults", {})
    def_days   = int(defaults.get("days", 30))
    def_fees   = float(defaults.get("fees", 0.0004))
    def_slip   = float(defaults.get("slippage", 0.0002))
    def_f      = int(defaults.get("sma_fast", 10))
    def_s      = int(defaults.get("sma_slow", 20))

    tasks = cfg.get("tasks", [])
    errors = 0
    for t in tasks:
        symbol = t["symbol"]
        tf     = t["tf"]
        days   = int(t.get("days", def_days))
        fees   = float(t.get("fees", def_fees))
        slip   = float(t.get("slippage", def_slip))
        fwin   = int(t.get("sma_fast", def_f))
        slow   = int(t.get("sma_slow", def_s))
        rc = run_backtest(symbol, tf, days, fees, slip, fwin, slow, base_url, token)
        if rc != 0:
            errors += 1
        time.sleep(0.2)

    if errors:
        print(f"[DONE] {len(tasks)} tâches, {errors} échec(s).")
        sys.exit(1)
    print(f"[DONE] {len(tasks)} tâches, 0 échec.")
    sys.exit(0)

if __name__ == "__main__":
    main()
