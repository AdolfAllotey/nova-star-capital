#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Écrit /root/src/v2/data/runtime/metrics.json de façon atomique.
À appeler par le bot après chaque cycle.

Schéma attendu:
{
  "total_exchange_balance_eur": float,
  "realized_profit_eur": float,
  "bot_monthly_pct": float | null,
  "benchmark_monthly_pct": float | null,
  "ts": "ISO-8601 UTC"
}
"""
from __future__ import annotations
import argparse, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parents[1]  # /root/src/v2
METRICS_PATH = BASE / "data" / "runtime" / "metrics.json"

def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent)) as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)

def write_metrics(
    total_exchange_balance_eur: float,
    realized_profit_eur: float,
    bot_monthly_pct: Optional[float] = None,
    benchmark_monthly_pct: Optional[float] = None,
) -> Path:
    # Validations légères
    if total_exchange_balance_eur < 0:
        raise ValueError("total_exchange_balance_eur doit être >= 0")
    # Le profit peut être négatif (perte), on le laisse passer tel quel.
    payload = {
        "total_exchange_balance_eur": float(total_exchange_balance_eur),
        "realized_profit_eur": float(realized_profit_eur),
        "bot_monthly_pct": None if bot_monthly_pct is None else float(bot_monthly_pct),
        "benchmark_monthly_pct": None if benchmark_monthly_pct is None else float(benchmark_monthly_pct),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _atomic_write(METRICS_PATH, payload)
    return METRICS_PATH

def main():
    p = argparse.ArgumentParser(description="Écriture atomique de metrics.json pour Nova Star Capital V2")
    p.add_argument("--balance", type=float, required=True, help="capital total sur exchange (EUR)")
    p.add_argument("--profit", type=float, required=True, help="profit net du cycle (EUR, négatif accepté)")
    p.add_argument("--bot-pct", type=float, default=None, help="perf mensuelle du bot en % (ex: 12)")
    p.add_argument("--bench-pct", type=float, default=None, help="perf mensuelle du benchmark en % (ex: 5)")
    args = p.parse_args()

    path = write_metrics(args.balance, args.profit, args.bot_pct, args.bench_pct)
    print(f"[write_metrics] updated: {path}")

if __name__ == "__main__":
    main()
